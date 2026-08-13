"""
Ledger de ingresos B2B (estilo Steam / Epic).

Modelo de negocio:
- La comisión se calcula sobre el precio del juego (pre-impuesto).
- Impuestos (IVA/VAT) se recaudan aparte y NO se reparten con el publisher.
- publisher_share_pct en la cuenta partner (default 70) → publisher_net.
- platform_take_rate = 100 - publisher_share → platform_fee.
- Cada venta genera un asiento idempotente; cada reembolso genera un asiento inverso.
- El saldo del partner = SUM(publisher_net_amount) de asientos available.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from checkout.revenue_share import split_revenue as _split_engine
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

# Cache en memoria para mitigar lag Kafka→Pinot en lecturas inmediatas post-venta.
_LEDGER_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_BY_PARTNER: dict[str, set[str]] = {}


def _money(value: float | Decimal | str) -> float:
    return float(
        Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def sale_ledger_id(order_id: str, product_id: str) -> str:
    """Clave determinista: re-fulfill no duplica la venta."""
    raw = f"sale_{order_id}_{product_id}"
    return raw[:64]


def refund_ledger_id(purchase_id: str) -> str:
    raw = f"refund_{purchase_id}"
    return raw[:64]


def split_revenue(gross: float, publisher_share_pct: float) -> tuple[float, float, float, float]:
    """
    Returns: (gross, platform_fee, publisher_net, platform_take_rate_pct)
    Delegado a checkout.revenue_share (flat | steam_tiers).
    """
    r = _split_engine(gross, publisher_share_pct)
    return r.gross, r.platform_fee, r.publisher_net, r.platform_take_rate_pct


async def _ledger_entry_exists(entry_id: str) -> dict[str, Any] | None:
    cached = _LEDGER_CACHE.get(entry_id)
    if cached and not cached.get("deleted"):
        return cached
    rows = await pinot_query(
        f"SELECT ledger_entry_id FROM fact_partner_ledger "
        f"WHERE ledger_entry_id = '{esc(entry_id)}' AND deleted = false LIMIT 1"
    )
    if rows:
        return {"ledger_entry_id": entry_id, "status": "already_exists"}
    return None


@dataclass
class PartnerAttribution:
    partner_id: str
    game_name: str
    publisher_share_pct: float


async def resolve_partner_for_product(product_id: str) -> PartnerAttribution | None:
    """Quién es dueño del product_id (solo claims aprobados por admin)."""
    from social.partner_game_claims import get_approved_claim

    cached = get_approved_claim(product_id)
    if cached:
        partner_id = str(cached["partner_id"])
        game_name = str(cached.get("game_name") or product_id)
    else:
        rows = await pinot_query(
            f"SELECT partner_id, game_name FROM fact_partner_games "
            f"WHERE product_id = '{esc(product_id)}' AND deleted = false "
            f"AND submission_status = 'approved' "
            f"ORDER BY created_at DESC LIMIT 1"
        )
        if not rows:
            return None
        partner_id, game_name = str(rows[0][0]), str(rows[0][1] or product_id)

    acct = await pinot_query(
        f"SELECT revenue_share_pct, status FROM fact_partner_accounts "
        f"WHERE partner_id = '{esc(partner_id)}' AND deleted = false LIMIT 1"
    )
    if not acct:
        return None
    status = str(acct[0][1] or "").lower()
    if status and status not in ("active", "approved", ""):
        return None
    share = float(acct[0][0] if acct[0][0] is not None else 70.0)
    return PartnerAttribution(
        partner_id=partner_id,
        game_name=game_name,
        publisher_share_pct=share,
    )


def _cache_put(entry: dict[str, Any]) -> None:
    eid = entry["ledger_entry_id"]
    _LEDGER_CACHE[eid] = entry
    pid = entry["partner_id"]
    _CACHE_BY_PARTNER.setdefault(pid, set()).add(eid)


async def record_sale_ledger(
    *,
    order_id: str,
    buyer_user_id: str,
    product_id: str,
    game_name: str,
    unit_price: float,
    quantity: int,
    currency: str = "USD",
) -> dict[str, Any] | None:
    """
    Asiento de venta. Si el juego no tiene publisher atribuido, no genera ledger
    (catálogo first-party / sin partner) — 100% plataforma implícito.
    """
    attr = await resolve_partner_for_product(product_id)
    if not attr:
        return None

    qty = max(1, int(quantity or 1))
    gross_line = _money(float(unit_price or 0) * qty)
    if gross_line <= 0:
        return None

    entry_id = sale_ledger_id(order_id, product_id)
    existing = await _ledger_entry_exists(entry_id)
    if existing and existing.get("gross_amount") is not None:
        return existing
    if existing and existing.get("status") == "already_exists":
        return existing

    # Lifetime AGR del producto (para steam_tiers); en flat se ignora.
    lifetime_before = 0.0
    try:
        from checkout.revenue_share import MODE as _RS_MODE

        if _RS_MODE == "steam_tiers":
            prev = await pinot_query(
                f"SELECT SUM(gross_amount) FROM fact_partner_ledger "
                f"WHERE product_id = '{esc(product_id)}' AND deleted = false "
                f"AND entry_type IN ('sale','refund','chargeback')"
            )
            if prev and prev[0][0] is not None:
                lifetime_before = float(prev[0][0])
    except Exception:
        lifetime_before = 0.0

    split = _split_engine(
        gross_line,
        attr.publisher_share_pct,
        lifetime_agr_before=lifetime_before,
    )
    g, fee, net, take = split.gross, split.platform_fee, split.publisher_net, split.platform_take_rate_pct
    now_ms = int(time.time() * 1000)
    entry = {
        "ledger_entry_id": entry_id,
        "partner_id": attr.partner_id,
        "order_id": order_id,
        "product_id": product_id,
        "game_name": game_name or attr.game_name,
        "buyer_user_id": buyer_user_id,
        "entry_type": "sale",
        "currency": (currency or "USD").upper(),
        "status": "available",
        "related_entry_id": "",
        "quantity": qty,
        "gross_amount": g,
        "platform_fee_amount": fee,
        "publisher_net_amount": net,
        "publisher_share_pct": float(attr.publisher_share_pct),
        "platform_take_rate_pct": take,
        "created_at": now_ms,
        "deleted": False,
    }
    _cache_put(entry)
    await kafka_send("fact_partner_ledger", entry_id, entry)

    try:
        from checkout.direct_fee import maybe_recoup_publication_fee

        await maybe_recoup_publication_fee(
            partner_id=attr.partner_id,
            product_id=product_id,
            game_name=game_name or attr.game_name,
        )
    except Exception as exc:
        print(f"[direct_fee] recoup skip: {exc}")

    return entry


async def record_refund_ledger(
    *,
    purchase_id: str,
    order_id: str,
    buyer_user_id: str,
    product_id: str,
    game_name: str,
    amount: float,
    currency: str = "USD",
) -> dict[str, Any] | None:
    """
    Asiento inverso. Usa el mismo split que la venta original si existe;
    si no, re-resuelve partner y aplica el % actual.
    """
    sale_id = sale_ledger_id(order_id, product_id)
    original = _LEDGER_CACHE.get(sale_id)
    if not original:
        rows = await pinot_query(
            f"SELECT ledger_entry_id, partner_id, game_name, currency, quantity, "
            f"gross_amount, platform_fee_amount, publisher_net_amount, "
            f"publisher_share_pct, platform_take_rate_pct "
            f"FROM fact_partner_ledger "
            f"WHERE ledger_entry_id = '{esc(sale_id)}' AND deleted = false LIMIT 1"
        )
        if rows:
            r = rows[0]
            original = {
                "ledger_entry_id": r[0],
                "partner_id": r[1],
                "game_name": r[2],
                "currency": r[3],
                "quantity": int(r[4] or 1),
                "gross_amount": float(r[5] or 0),
                "platform_fee_amount": float(r[6] or 0),
                "publisher_net_amount": float(r[7] or 0),
                "publisher_share_pct": float(r[8] or 70),
                "platform_take_rate_pct": float(r[9] or 30),
            }

    if original:
        partner_id = original["partner_id"]
        g = -abs(_money(original["gross_amount"]))
        fee = -abs(_money(original["platform_fee_amount"]))
        net = -abs(_money(original["publisher_net_amount"]))
        share = float(original["publisher_share_pct"])
        take = float(original["platform_take_rate_pct"])
        qty = -abs(int(original.get("quantity") or 1))
        cur = original.get("currency") or currency or "USD"
        gname = original.get("game_name") or game_name
        related = sale_id
    else:
        attr = await resolve_partner_for_product(product_id)
        if not attr:
            return None
        g0, fee0, net0, take = split_revenue(abs(float(amount or 0)), attr.publisher_share_pct)
        partner_id = attr.partner_id
        g, fee, net = -g0, -fee0, -net0
        share = attr.publisher_share_pct
        qty = -1
        cur = currency or "USD"
        gname = game_name or attr.game_name
        related = ""

    entry_id = refund_ledger_id(purchase_id)
    existing = await _ledger_entry_exists(entry_id)
    if existing and existing.get("entry_type") == "refund":
        return existing
    if existing and existing.get("status") == "already_exists":
        return existing

    now_ms = int(time.time() * 1000)
    entry = {
        "ledger_entry_id": entry_id,
        "partner_id": partner_id,
        "order_id": order_id,
        "product_id": product_id,
        "game_name": gname,
        "buyer_user_id": buyer_user_id,
        "entry_type": "refund",
        "currency": str(cur).upper(),
        "status": "available",
        "related_entry_id": related,
        "quantity": qty,
        "gross_amount": g,
        "platform_fee_amount": fee,
        "publisher_net_amount": net,
        "publisher_share_pct": share,
        "platform_take_rate_pct": take,
        "created_at": now_ms,
        "deleted": False,
    }
    _cache_put(entry)
    await kafka_send("fact_partner_ledger", entry_id, entry)
    return entry


def _row_to_entry(r: list) -> dict[str, Any]:
    return {
        "ledger_entry_id": r[0],
        "partner_id": r[1],
        "order_id": r[2],
        "product_id": r[3],
        "game_name": r[4],
        "buyer_user_id": r[5],
        "entry_type": r[6],
        "currency": r[7],
        "status": r[8],
        "related_entry_id": r[9] or "",
        "quantity": int(r[10] or 0),
        "gross_amount": float(r[11] or 0),
        "platform_fee_amount": float(r[12] or 0),
        "publisher_net_amount": float(r[13] or 0),
        "publisher_share_pct": float(r[14] or 0),
        "platform_take_rate_pct": float(r[15] or 0),
        "created_at": int(r[16] or 0),
    }


async def list_partner_ledger(partner_id: str, limit: int = 100) -> list[dict[str, Any]]:
    rows = await pinot_query(
        f"SELECT ledger_entry_id, partner_id, order_id, product_id, game_name, "
        f"buyer_user_id, entry_type, currency, status, related_entry_id, "
        f"quantity, gross_amount, platform_fee_amount, publisher_net_amount, "
        f"publisher_share_pct, platform_take_rate_pct, created_at "
        f"FROM fact_partner_ledger "
        f"WHERE partner_id = '{esc(partner_id)}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT {int(limit)}"
    )
    by_id: dict[str, dict[str, Any]] = {}
    for r in rows or []:
        e = _row_to_entry(r)
        by_id[e["ledger_entry_id"]] = e
    for eid in _CACHE_BY_PARTNER.get(partner_id, set()):
        cached = _LEDGER_CACHE.get(eid)
        if cached and not cached.get("deleted"):
            by_id[eid] = cached
    entries = list(by_id.values())
    entries.sort(key=lambda x: int(x.get("created_at") or 0), reverse=True)
    return entries[:limit]


def summarize_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    gross = _money(sum(float(e.get("gross_amount") or 0) for e in entries))
    fee = _money(sum(float(e.get("platform_fee_amount") or 0) for e in entries))
    net = _money(sum(float(e.get("publisher_net_amount") or 0) for e in entries))
    units = sum(int(e.get("quantity") or 0) for e in entries if e.get("entry_type") == "sale")
    refunds = sum(1 for e in entries if e.get("entry_type") == "refund")
    by_product: dict[str, dict[str, Any]] = {}
    for e in entries:
        pid = e.get("product_id") or ""
        bucket = by_product.setdefault(
            pid,
            {
                "product_id": pid,
                "game_name": e.get("game_name") or pid,
                "units_sold": 0,
                "gross_revenue": 0.0,
                "platform_fee": 0.0,
                "publisher_net": 0.0,
            },
        )
        bucket["gross_revenue"] = _money(bucket["gross_revenue"] + float(e.get("gross_amount") or 0))
        bucket["platform_fee"] = _money(bucket["platform_fee"] + float(e.get("platform_fee_amount") or 0))
        bucket["publisher_net"] = _money(bucket["publisher_net"] + float(e.get("publisher_net_amount") or 0))
        if e.get("entry_type") == "sale":
            bucket["units_sold"] += int(e.get("quantity") or 0)
        elif e.get("entry_type") == "refund":
            bucket["units_sold"] += int(e.get("quantity") or 0)  # already negative
    return {
        "gross_revenue": gross,
        "platform_fee": fee,
        "publisher_net": net,
        "balance_available": net,
        "units_sold": max(0, units),
        "refund_count": refunds,
        "by_product": list(by_product.values()),
        "entries": entries,
    }


async def partner_earnings_summary(partner_id: str) -> dict[str, Any]:
    """Earnings + hold + payouts (Steam-like available vs pending)."""
    from checkout.partner_payouts import partner_balance

    return await partner_balance(partner_id)


async def platform_gmv_summary(limit: int = 500) -> dict[str, Any]:
    """Vista admin: GMV bruto, take rate cobrado, neto publisher."""
    rows = await pinot_query(
        f"SELECT ledger_entry_id, partner_id, order_id, product_id, game_name, "
        f"buyer_user_id, entry_type, currency, status, related_entry_id, "
        f"quantity, gross_amount, platform_fee_amount, publisher_net_amount, "
        f"publisher_share_pct, platform_take_rate_pct, created_at "
        f"FROM fact_partner_ledger WHERE deleted = false "
        f"ORDER BY created_at DESC LIMIT {int(limit)}"
    )
    by_id: dict[str, dict[str, Any]] = {}
    for r in rows or []:
        e = _row_to_entry(r)
        by_id[e["ledger_entry_id"]] = e
    for cached in _LEDGER_CACHE.values():
        if cached and not cached.get("deleted"):
            by_id[cached["ledger_entry_id"]] = cached
    entries = list(by_id.values())
    summary = summarize_entries(entries)
    partners: dict[str, dict[str, Any]] = {}
    for e in entries:
        pid = e["partner_id"]
        p = partners.setdefault(
            pid,
            {
                "partner_id": pid,
                "gross_revenue": 0.0,
                "platform_fee": 0.0,
                "publisher_net": 0.0,
                "sales": 0,
                "units_sold": 0,
                "refund_count": 0,
            },
        )
        p["gross_revenue"] = _money(p["gross_revenue"] + float(e.get("gross_amount") or 0))
        p["platform_fee"] = _money(p["platform_fee"] + float(e.get("platform_fee_amount") or 0))
        p["publisher_net"] = _money(p["publisher_net"] + float(e.get("publisher_net_amount") or 0))
        if e.get("entry_type") == "sale":
            p["sales"] += 1
            p["units_sold"] += int(e.get("quantity") or 0)
        elif e.get("entry_type") == "refund":
            p["refund_count"] += 1
    return {
        "gmv": summary["gross_revenue"],
        "platform_revenue": summary["platform_fee"],
        "publisher_payouts_owed": summary["publisher_net"],
        "units_sold": summary["units_sold"],
        "refund_count": summary["refund_count"],
        "partners": sorted(partners.values(), key=lambda x: x["gross_revenue"], reverse=True),
        "recent_entries": entries[:50],
    }


async def admin_business_dashboard(limit: int = 500) -> dict[str, Any]:
    """
    Dashboard B2B admin: GMV + lista completa de partners con estado y comisión.
    Incluye cuentas sin ventas (GMV 0).
    """
    gmv = await platform_gmv_summary(limit=limit)
    ledger_by_id = {p["partner_id"]: p for p in gmv["partners"]}

    account_rows = await pinot_query(
        "SELECT partner_id, company_name, contact_email, revenue_share_pct, status, created_at "
        "FROM fact_partner_accounts WHERE deleted = false LIMIT 200"
    )
    game_rows = await pinot_query(
        "SELECT partner_id, product_id FROM fact_partner_games "
        "WHERE deleted = false LIMIT 500"
    )
    games_by_partner: dict[str, int] = {}
    for gr in game_rows or []:
        pid = str(gr[0])
        games_by_partner[pid] = games_by_partner.get(pid, 0) + 1

    partners_full: list[dict[str, Any]] = []
    for row in account_rows or []:
        pid, company, email, share_pct, status, created_at = row
        pid = str(pid)
        share = float(share_pct if share_pct is not None else 70.0)
        ledger = ledger_by_id.get(pid, {})
        partners_full.append({
            "partner_id": pid,
            "company_name": company or "—",
            "contact_email": email or "—",
            "status": str(status or "active").lower(),
            "publisher_share_pct": share,
            "platform_take_rate_pct": _money(100.0 - share),
            "games_count": games_by_partner.get(pid, 0),
            "gross_revenue": float(ledger.get("gross_revenue") or 0),
            "platform_fee": float(ledger.get("platform_fee") or 0),
            "publisher_net": float(ledger.get("publisher_net") or 0),
            "sales": int(ledger.get("sales") or 0),
            "units_sold": int(ledger.get("units_sold") or 0),
            "refund_count": int(ledger.get("refund_count") or 0),
            "created_at": int(created_at or 0),
        })

    partners_full.sort(key=lambda x: x["gross_revenue"], reverse=True)
    active_count = sum(1 for p in partners_full if p["status"] in ("active", "approved", ""))
    return {
        "gmv": gmv["gmv"],
        "platform_revenue": gmv["platform_revenue"],
        "publisher_payouts_owed": gmv["publisher_payouts_owed"],
        "units_sold": gmv["units_sold"],
        "refund_count": gmv["refund_count"],
        "partners_count": len(partners_full),
        "partners_active": active_count,
        "partners": partners_full,
        "recent_entries": gmv["recent_entries"],
        "note": (
            "GMV = precio juego pre-impuesto (ventas netas). "
            "Ingreso GameMetrics = take rate (platform_fee). "
            "Adeudado publishers = neto acumulado en ledger."
        ),
    }

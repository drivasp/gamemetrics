"""
Payouts a publishers — modelo tipo Steamworks.

Steam:
- Paga ~30 días después del mes de venta
- Mínimo ~$100 (configurable)
- Reembolsos restan del neto

GameMetrics (profesional / academic):
- Hold = ventana de reembolso (default 14 días) → pending vs available
- Mínimo PAYOUT_MIN_USD (default $10 en dev; documentar $100 en prod)
- Admin marca pagado (manual + referencia) o Transfer vía Stripe Connect
"""
from __future__ import annotations

import os
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from checkout.partner_ledger import list_partner_ledger, record_sale_ledger  # noqa: F401
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

HOLD_MS = int(os.getenv("PAYOUT_HOLD_MS", "0"))  # prod Steam-like: 1209600000 (14d)
PAYOUT_MIN_USD = float(os.getenv("PAYOUT_MIN_USD", "1"))
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4000").rstrip("/")

_PAYOUT_CACHE: dict[str, dict[str, Any]] = {}
_PAYOUTS_BY_PARTNER: dict[str, set[str]] = {}
_CONNECT_CACHE: dict[str, dict[str, Any]] = {}


def _money(v: float | Decimal | str) -> float:
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def effective_entry_bucket(entry: dict[str, Any], now_ms: int | None = None) -> str:
    """pending | available — alineado a ventana de reembolso Steam-like."""
    now = now_ms or int(time.time() * 1000)
    et = entry.get("entry_type") or ""
    if et == "payout":
        return "paid_out"
    if et in ("refund", "chargeback", "direct_fee", "direct_fee_recoup"):
        return "available"  # ajustan saldo disponible de inmediato
    created = int(entry.get("created_at") or 0)
    if et == "sale" and (now - created) < HOLD_MS:
        return "pending"
    return "available"


async def list_partner_payouts(partner_id: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = await pinot_query(
        f"SELECT payout_id, partner_id, currency, method, status, reference, "
        f"created_by, stripe_transfer_id, notes, amount, created_at, paid_at "
        f"FROM fact_partner_payouts WHERE partner_id = '{esc(partner_id)}' "
        f"AND deleted = false ORDER BY created_at DESC LIMIT {int(limit)}"
    )
    by_id: dict[str, dict[str, Any]] = {}
    for r in rows or []:
        p = {
            "payout_id": r[0],
            "partner_id": r[1],
            "currency": r[2] or "USD",
            "method": r[3],
            "status": r[4],
            "reference": r[5] or "",
            "created_by": r[6] or "",
            "stripe_transfer_id": r[7] or "",
            "notes": r[8] or "",
            "amount": float(r[9] or 0),
            "created_at": int(r[10] or 0),
            "paid_at": int(r[11] or 0),
        }
        by_id[p["payout_id"]] = p
    for pid in _PAYOUTS_BY_PARTNER.get(partner_id, set()):
        if pid in _PAYOUT_CACHE:
            by_id[pid] = _PAYOUT_CACHE[pid]
    items = list(by_id.values())
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items[:limit]


def summarize_with_hold(
    entries: list[dict[str, Any]],
    payouts: list[dict[str, Any]],
) -> dict[str, Any]:
    now = int(time.time() * 1000)
    pending = 0.0
    available_gross_net = 0.0
    gross = 0.0
    fee = 0.0
    units = 0
    refunds = 0
    for e in entries:
        if e.get("entry_type") == "payout":
            continue
        net = float(e.get("publisher_net_amount") or 0)
        gross = _money(gross + float(e.get("gross_amount") or 0))
        fee = _money(fee + float(e.get("platform_fee_amount") or 0))
        bucket = effective_entry_bucket(e, now)
        if e.get("entry_type") == "sale":
            units += int(e.get("quantity") or 0)
        if e.get("entry_type") == "refund":
            refunds += 1
        if bucket == "pending":
            pending = _money(pending + net)
        else:
            available_gross_net = _money(available_gross_net + net)

    paid = _money(
        sum(float(p["amount"]) for p in payouts if str(p.get("status")) == "paid")
    )
    balance_available = _money(max(0.0, available_gross_net - paid))
    return {
        "gross_revenue": gross,
        "platform_fee": fee,
        "publisher_net": _money(available_gross_net + pending),
        "balance_pending": pending,
        "balance_available": balance_available,
        "balance_paid_out": paid,
        "payout_min_usd": PAYOUT_MIN_USD,
        "hold_days": max(0, HOLD_MS // (24 * 60 * 60 * 1000)),
        "can_request_payout": balance_available >= PAYOUT_MIN_USD,
        "units_sold": max(0, units),
        "refund_count": refunds,
        "payouts": payouts,
        "entries": entries,
    }


async def partner_balance(partner_id: str) -> dict[str, Any]:
    entries = await list_partner_ledger(partner_id, limit=300)
    payouts = await list_partner_payouts(partner_id, limit=100)
    summary = summarize_with_hold(entries, payouts)
    # by_product from available+pending sales (reuse simple loop)
    by_product: dict[str, dict[str, Any]] = {}
    for e in entries:
        if e.get("entry_type") == "payout":
            continue
        pid = e.get("product_id") or ""
        b = by_product.setdefault(
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
        b["gross_revenue"] = _money(b["gross_revenue"] + float(e.get("gross_amount") or 0))
        b["platform_fee"] = _money(b["platform_fee"] + float(e.get("platform_fee_amount") or 0))
        b["publisher_net"] = _money(b["publisher_net"] + float(e.get("publisher_net_amount") or 0))
        if e.get("entry_type") == "sale":
            b["units_sold"] += int(e.get("quantity") or 0)
        elif e.get("entry_type") == "refund":
            b["units_sold"] += int(e.get("quantity") or 0)
    summary["by_product"] = list(by_product.values())
    return summary


async def get_connect_account(partner_id: str) -> dict[str, Any] | None:
    if partner_id in _CONNECT_CACHE:
        return _CONNECT_CACHE[partner_id]
    rows = await pinot_query(
        f"SELECT partner_id, stripe_account_id, onboarding_status, payouts_enabled, updated_at "
        f"FROM fact_partner_payout_accounts WHERE partner_id = '{esc(partner_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        return None
    r = rows[0]
    acct = {
        "partner_id": r[0],
        "stripe_account_id": r[1] or "",
        "onboarding_status": r[2] or "none",
        "payouts_enabled": bool(r[3]),
        "updated_at": int(r[4] or 0),
    }
    _CONNECT_CACHE[partner_id] = acct
    return acct


async def upsert_connect_account(
    partner_id: str,
    stripe_account_id: str,
    onboarding_status: str,
    payouts_enabled: bool,
) -> dict[str, Any]:
    now = int(time.time() * 1000)
    row = {
        "partner_id": partner_id,
        "stripe_account_id": stripe_account_id,
        "onboarding_status": onboarding_status,
        "payouts_enabled": payouts_enabled,
        "updated_at": now,
        "deleted": False,
    }
    _CONNECT_CACHE[partner_id] = row
    await kafka_send("fact_partner_payout_accounts", partner_id, row)
    return row


async def create_connect_onboarding_link(
    partner_id: str,
    email: str,
    company_name: str,
) -> dict[str, Any]:
    if not STRIPE_SECRET:
        raise RuntimeError(
            "Stripe no configurado. Usa payout manual o define STRIPE_SECRET_KEY."
        )
    import stripe

    stripe.api_key = STRIPE_SECRET
    existing = await get_connect_account(partner_id)
    acct_id = existing["stripe_account_id"] if existing else ""
    if not acct_id:
        acct = stripe.Account.create(
            type="express",
            email=email or None,
            capabilities={"transfers": {"requested": True}},
            business_profile={"name": company_name or "GameMetrics Publisher"},
            metadata={"partner_id": partner_id},
        )
        acct_id = acct.id
        await upsert_connect_account(partner_id, acct_id, "pending", False)

    link = stripe.AccountLink.create(
        account=acct_id,
        refresh_url=f"{FRONTEND_URL}/my-partner?connect=refresh",
        return_url=f"{FRONTEND_URL}/my-partner?connect=done",
        type="account_onboarding",
    )
    await upsert_connect_account(partner_id, acct_id, "pending", False)
    return {"stripe_account_id": acct_id, "url": link.url, "onboarding_status": "pending"}


async def refresh_connect_status(partner_id: str) -> dict[str, Any] | None:
    acct = await get_connect_account(partner_id)
    if not acct or not acct.get("stripe_account_id") or not STRIPE_SECRET:
        return acct
    import stripe

    stripe.api_key = STRIPE_SECRET
    remote = stripe.Account.retrieve(acct["stripe_account_id"])
    enabled = bool(remote.payouts_enabled and remote.details_submitted)
    status = "complete" if enabled else "pending"
    return await upsert_connect_account(
        partner_id, acct["stripe_account_id"], status, enabled
    )


async def create_payout(
    *,
    partner_id: str,
    amount: float,
    created_by: str,
    method: str = "manual",
    reference: str = "",
    notes: str = "",
    idempotency_key: str = "",
    force_fail: bool = False,
) -> dict[str, Any]:
    from fraud.service import FraudDetectionService

    fraud = FraudDetectionService().evaluate(
        user_id=created_by,
        action="payout_attempt",
        entity_type="partner",
        entity_id=partner_id,
        amount=amount,
    )
    if fraud["action"] == "block":
        raise ValueError(f"Payout bloqueado por fraude: {fraud['reason']}")

    bal = await partner_balance(partner_id)
    amt = _money(amount)
    if amt <= 0:
        raise ValueError("El monto debe ser mayor a 0")
    if amt < PAYOUT_MIN_USD:
        raise ValueError(f"Mínimo de payout: ${PAYOUT_MIN_USD:.2f} USD (política tipo Steam)")
    if amt > bal["balance_available"] + 0.001:
        raise ValueError(
            f"Saldo disponible insuficiente (${bal['balance_available']:.2f}). "
            f"${bal['balance_pending']:.2f} aún en hold ({bal['hold_days']} días)."
        )

    # Idempotencia: misma clave o misma referencia no duplica payout pagado
    key = (idempotency_key or reference or "").strip()
    if key:
        for p in await list_partner_payouts(partner_id, limit=100):
            if key and (p.get("reference") == key or f"idem:{key}" in str(p.get("notes") or "")):
                return p

    # Sandbox: simular fallo sin debitar saldo
    if force_fail or method == "sandbox_fail":
        now = int(time.time() * 1000)
        payout_id = uuid.uuid4().hex[:15]
        row = {
            "payout_id": payout_id,
            "partner_id": partner_id,
            "currency": "USD",
            "method": method,
            "status": "failed",
            "reference": reference or f"FAIL-{payout_id}",
            "created_by": created_by,
            "stripe_transfer_id": "",
            "notes": (notes or "") + " | sandbox_fail",
            "amount": amt,
            "created_at": now,
            "paid_at": 0,
            "deleted": False,
        }
        _PAYOUT_CACHE[payout_id] = row
        _PAYOUTS_BY_PARTNER.setdefault(partner_id, set()).add(payout_id)
        await kafka_send("fact_partner_payouts", payout_id, row)
        # NO ledger debit — balance intact
        return row

    stripe_transfer_id = ""
    method = (method or "manual").lower()
    if method == "stripe_connect":
        if not STRIPE_SECRET:
            raise ValueError("Stripe Connect requiere STRIPE_SECRET_KEY")
        acct = await refresh_connect_status(partner_id)
        if not acct or not acct.get("payouts_enabled"):
            raise ValueError("El publisher no tiene Stripe Connect listo (onboarding incompleto)")
        import stripe

        stripe.api_key = STRIPE_SECRET
        transfer_kwargs = {
            "amount": int(round(amt * 100)),
            "currency": "usd",
            "destination": acct["stripe_account_id"],
            "transfer_group": f"partner_{partner_id}",
            "metadata": {"partner_id": partner_id, "idempotency_key": key or ""},
        }
        if key:
            transfer = stripe.Transfer.create(**transfer_kwargs, idempotency_key=key[:255])
        else:
            transfer = stripe.Transfer.create(**transfer_kwargs)
        stripe_transfer_id = transfer.id
        if not reference:
            reference = transfer.id

    now = int(time.time() * 1000)
    payout_id = uuid.uuid4().hex[:15]
    row = {
        "payout_id": payout_id,
        "partner_id": partner_id,
        "currency": "USD",
        "method": method,
        "status": "paid",
        "reference": reference or f"PAY-{payout_id}",
        "created_by": created_by,
        "stripe_transfer_id": stripe_transfer_id,
        "notes": (notes or "") + (f" | idem:{key}" if key and "idem:" not in (notes or "") else ""),
        "amount": amt,
        "created_at": now,
        "paid_at": now,
        "deleted": False,
    }
    _PAYOUT_CACHE[payout_id] = row
    _PAYOUTS_BY_PARTNER.setdefault(partner_id, set()).add(payout_id)
    await kafka_send("fact_partner_payouts", payout_id, row)

# Payout durable debit when paid
    ledger_id = f"payout_{payout_id}"
    await kafka_send("fact_partner_ledger", ledger_id, {
        "ledger_entry_id": ledger_id,
        "partner_id": partner_id,
        "order_id": "",
        "product_id": "",
        "game_name": "Payout",
        "buyer_user_id": created_by,
        "entry_type": "payout",
        "currency": "USD",
        "status": "paid",
        "related_entry_id": payout_id,
        "quantity": 0,
        "gross_amount": 0.0,
        "platform_fee_amount": 0.0,
        "publisher_net_amount": -amt,
        "publisher_share_pct": 0.0,
        "platform_take_rate_pct": 0.0,
        "created_at": now,
        "deleted": False,
    })
    try:
        from ledger.sqlite_store import post_entry

        post_entry(
            entry_type="payout",
            account_type="partner",
            account_id=partner_id,
            amount=-amt,
            reference=row["reference"],
            related_payment=payout_id,
            idempotency_key=f"durable_payout_{key or payout_id}",
            metadata={"method": method, "created_by": created_by},
            allow_negative_balance=True,
        )
    except Exception as exc:
        print(f"[payout] durable skip: {exc}")
    try:
        from checkout.financial_audit import audit_event

        audit_event(
            actor_id=created_by,
            action="create_payout",
            entity_type="payout",
            entity_id=payout_id,
            amount=amt,
            after=row,
        )
    except Exception:
        pass
    return row


async def list_all_payouts(limit: int = 100) -> list[dict[str, Any]]:
    rows = await pinot_query(
        f"SELECT payout_id, partner_id, currency, method, status, reference, "
        f"created_by, stripe_transfer_id, notes, amount, created_at, paid_at "
        f"FROM fact_partner_payouts WHERE deleted = false "
        f"ORDER BY created_at DESC LIMIT {int(limit)}"
    )
    items = []
    for r in rows or []:
        items.append({
            "payout_id": r[0],
            "partner_id": r[1],
            "currency": r[2] or "USD",
            "method": r[3],
            "status": r[4],
            "reference": r[5] or "",
            "created_by": r[6] or "",
            "stripe_transfer_id": r[7] or "",
            "notes": r[8] or "",
            "amount": float(r[9] or 0),
            "created_at": int(r[10] or 0),
            "paid_at": int(r[11] or 0),
        })
    for cached in _PAYOUT_CACHE.values():
        if not any(i["payout_id"] == cached["payout_id"] for i in items):
            items.append(cached)
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items[:limit]

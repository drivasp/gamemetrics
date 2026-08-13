"""Armado de payloads para los 6 reportes tácticos."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from checkout.partner_ledger import admin_business_dashboard
from checkout.partner_payouts import list_all_payouts, partner_balance
from reports.catalog import get_meta, list_catalog
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from social.partner_game_claims import cache_partner_game, list_cached_claims


def _iso(ms: int | str | None) -> str:
    try:
        n = int(ms or 0)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    if n < 1_000_000_000_000:
        n *= 1000
    return datetime.fromtimestamp(n / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _envelope(meta: dict[str, Any], *, rows: list[dict], kpis: list[dict] | None = None,
              applied_filters: dict | None = None, partners: list | None = None) -> dict[str, Any]:
    return {
        "meta": {
            "code": meta["code"],
            "type": meta["type"],
            "title": meta["title"],
            "area": meta["area"],
            "question": meta["question"],
            "description": meta["description"],
            "source": meta["source"],
            "columns": meta["columns"],
        },
        "filters": applied_filters or {},
        "kpis": kpis or [],
        "rows": rows,
        "partners": partners or [],
        "generated_at": _now_iso(),
        "row_count": len(rows),
        "disclaimer": (
            "Informe táctico GameMetrics S.A. · Uso interno. "
            "No sustituye estados financieros auditados."
        ),
    }


async def _company_name(partner_id: str) -> str:
    rows = await pinot_query(
        f"SELECT company_name FROM fact_partner_accounts "
        f"WHERE partner_id = '{esc(partner_id)}' AND deleted = false LIMIT 1"
    )
    return str(rows[0][0]) if rows else "—"


async def build_s01(status: str = "pending") -> dict[str, Any]:
    meta = get_meta("GM-S01")
    assert meta
    want = (status or "pending").lower()
    try:
        rows_raw = await pinot_query(
            "SELECT partner_game_id, partner_id, product_id, game_name, submission_status, created_at "
            "FROM fact_partner_games WHERE deleted = false "
            f"AND submission_status = '{esc(want)}' "
            "ORDER BY created_at DESC LIMIT 200"
        )
    except Exception:
        rows_raw = []
    by_id: dict[str, dict] = {}
    for r in rows_raw or []:
        item = {
            "partner_game_id": str(r[0]),
            "partner_id": str(r[1]),
            "product_id": str(r[2]),
            "game_name": r[3] or "",
            "submission_status": str(r[4] or want),
            "created_at": int(r[5] or 0),
        }
        by_id[item["partner_game_id"]] = item
        cache_partner_game({**item, "deleted": False})
    for cached in list_cached_claims(want):
        by_id[str(cached["partner_game_id"])] = cached

    rows = []
    for item in sorted(by_id.values(), key=lambda x: int(x.get("created_at") or 0), reverse=True):
        company = await _company_name(str(item.get("partner_id") or ""))
        email_rows = await pinot_query(
            f"SELECT contact_email FROM fact_partner_accounts "
            f"WHERE partner_id = '{esc(item.get('partner_id') or '')}' AND deleted = false LIMIT 1"
        )
        rows.append({
            "partner_game_id": item.get("partner_game_id"),
            "game_name": item.get("game_name") or "—",
            "company_name": company,
            "contact_email": (email_rows[0][0] if email_rows else "—"),
            "product_id": item.get("product_id") or "—",
            "submission_status": item.get("submission_status") or want,
            "created_at_iso": _iso(item.get("created_at")),
        })
    return _envelope(meta, rows=rows, applied_filters={"status": want})


async def build_s02() -> dict[str, Any]:
    meta = get_meta("GM-S02")
    assert meta
    try:
        payouts = await list_all_payouts(100)
    except Exception:
        payouts = []
    rows = []
    for p in payouts:
        rows.append({
            "payout_id": p.get("payout_id") or "—",
            "partner_id": p.get("partner_id") or "—",
            "company_name": await _company_name(str(p.get("partner_id") or "")),
            "amount": float(p.get("amount") or 0),
            "method": p.get("method") or "—",
            "status": p.get("status") or "—",
            "reference": p.get("reference") or "—",
            "paid_at_iso": _iso(p.get("paid_at") or p.get("created_at")),
        })
    return _envelope(meta, rows=rows)


async def build_s03(status: str = "open") -> dict[str, Any]:
    meta = get_meta("GM-S03")
    assert meta
    want = (status or "open").lower()
    try:
        raw = await pinot_query(
            "SELECT ticket_id, user_id, subject, body, status, priority, created_at "
            "FROM fact_support_tickets WHERE deleted = false "
            f"AND status = '{esc(want)}' "
            "ORDER BY created_at DESC LIMIT 200"
        )
    except Exception:
        raw = []
    priority_rank = {"high": 0, "normal": 1, "low": 2}
    items = []
    for r in raw or []:
        items.append({
            "ticket_id": r[0],
            "user_id": r[1],
            "subject": r[2] or "—",
            "priority": r[5] or "normal",
            "status": r[4] or want,
            "created_at": int(r[6] or 0) if str(r[6]).isdigit() else 0,
            "created_at_iso": _iso(r[6]),
        })
    items.sort(key=lambda x: (priority_rank.get(str(x["priority"]), 9), -int(x["created_at"])))
    rows = [{k: v for k, v in i.items() if k != "created_at"} for i in items]
    return _envelope(meta, rows=rows, applied_filters={"status": want})


async def build_c01() -> dict[str, Any]:
    meta = get_meta("GM-C01")
    assert meta
    try:
        dash = await admin_business_dashboard(limit=500)
    except Exception:
        dash = {}
    kpis = [
        {"key": "gmv", "label": "GMV total", "value": float(dash.get("gmv") or 0), "format": "currency"},
        {"key": "platform_revenue", "label": "Ingresos GameMetrics", "value": float(dash.get("platform_revenue") or 0), "format": "currency"},
        {"key": "publisher_payouts_owed", "label": "Adeudado publishers", "value": float(dash.get("publisher_payouts_owed") or 0), "format": "currency"},
        {"key": "units_sold", "label": "Unidades vendidas", "value": int(dash.get("units_sold") or 0), "format": "number"},
        {"key": "partners_active", "label": "Partners activos", "value": int(dash.get("partners_active") or 0), "format": "number"},
        {"key": "refund_count", "label": "Reembolsos", "value": int(dash.get("refund_count") or 0), "format": "number"},
    ]
    rows = [
        {"metric": k["label"], "value": k["value"], "unit": "USD" if k["format"] == "currency" else "count"}
        for k in kpis
    ]
    return _envelope(meta, rows=rows, kpis=kpis)


async def build_c02(partner_id: str) -> dict[str, Any]:
    meta = get_meta("GM-C02")
    assert meta
    partners_list = []
    try:
        dash = await admin_business_dashboard(limit=500)
        partners_list = [
            {"partner_id": p["partner_id"], "company_name": p.get("company_name") or p["partner_id"]}
            for p in (dash.get("partners") or [])
        ]
    except Exception:
        partners_list = []

    if not partner_id:
        return _envelope(
            meta,
            rows=[],
            kpis=[],
            applied_filters={"partner_id": ""},
            partners=partners_list,
        )

    try:
        bal = await partner_balance(partner_id)
    except Exception:
        bal = {}
    company = await _company_name(partner_id)
    kpis = [
        {"key": "company", "label": "Estudio", "value": company, "format": "text"},
        {"key": "gross", "label": "Ingreso bruto", "value": float(bal.get("gross_revenue") or 0), "format": "currency"},
        {"key": "fee", "label": "Comisión plataforma", "value": float(bal.get("platform_fee") or 0), "format": "currency"},
        {"key": "net", "label": "Neto publisher", "value": float(bal.get("publisher_net") or 0), "format": "currency"},
        {"key": "available", "label": "Saldo disponible", "value": float(bal.get("balance_available") or 0), "format": "currency"},
        {"key": "pending", "label": "Saldo en hold", "value": float(bal.get("balance_pending") or 0), "format": "currency"},
        {"key": "paid", "label": "Ya liquidado", "value": float(bal.get("balance_paid_out") or 0), "format": "currency"},
    ]
    rows = []
    for p in bal.get("by_product") or []:
        rows.append({
            "game_name": p.get("game_name") or p.get("product_id") or "—",
            "units_sold": int(p.get("units_sold") or 0),
            "gross_revenue": float(p.get("gross_revenue") or 0),
            "platform_fee": float(p.get("platform_fee") or 0),
            "publisher_net": float(p.get("publisher_net") or 0),
        })
    return _envelope(
        meta,
        rows=rows,
        kpis=kpis,
        applied_filters={"partner_id": partner_id},
        partners=partners_list,
    )


async def build_c03() -> dict[str, Any]:
    meta = get_meta("GM-C03")
    assert meta
    try:
        dash = await admin_business_dashboard(limit=500)
    except Exception:
        dash = {}
    partners = dash.get("partners") or []
    kpis = [
        {"key": "partners_count", "label": "Estudios", "value": int(dash.get("partners_count") or len(partners)), "format": "number"},
        {"key": "gmv", "label": "GMV", "value": float(dash.get("gmv") or 0), "format": "currency"},
        {"key": "units_sold", "label": "Unidades", "value": int(dash.get("units_sold") or 0), "format": "number"},
        {"key": "refund_count", "label": "Reembolsos", "value": int(dash.get("refund_count") or 0), "format": "number"},
    ]
    rows = []
    for p in partners:
        rows.append({
            "company_name": p.get("company_name") or "—",
            "partner_id": p.get("partner_id"),
            "games_count": int(p.get("games_count") or 0),
            "units_sold": int(p.get("units_sold") or 0),
            "gross_revenue": float(p.get("gross_revenue") or 0),
            "platform_fee": float(p.get("platform_fee") or 0),
            "publisher_net": float(p.get("publisher_net") or 0),
            "refund_count": int(p.get("refund_count") or 0),
            "status": p.get("status") or "—",
        })
    rows.sort(key=lambda x: float(x["gross_revenue"]), reverse=True)
    return _envelope(meta, rows=rows, kpis=kpis)


async def build_report(code: str, *, status: str | None = None, partner_id: str | None = None) -> dict[str, Any]:
    c = (code or "").upper()
    if c == "GM-S01":
        return await build_s01(status or "pending")
    if c == "GM-S02":
        return await build_s02()
    if c == "GM-S03":
        return await build_s03(status or "open")
    if c == "GM-C01":
        return await build_c01()
    if c == "GM-C02":
        return await build_c02(partner_id or "")
    if c == "GM-C03":
        return await build_c03()
    raise KeyError(c)


def to_csv(payload: dict[str, Any]) -> str:
    cols = payload.get("meta", {}).get("columns") or []
    keys = [c["key"] for c in cols]
    labels = [c["label"] for c in cols]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["GameMetrics S.A.", payload.get("meta", {}).get("code", ""), payload.get("generated_at", "")])
    writer.writerow([payload.get("meta", {}).get("title", "")])
    writer.writerow([])
    writer.writerow(labels)
    for row in payload.get("rows") or []:
        writer.writerow([row.get(k, "") for k in keys])
    return buf.getvalue()


def catalog_payload() -> dict[str, Any]:
    return {
        "items": list_catalog(),
        "generated_at": _now_iso(),
        "count": len(list_catalog()),
    }

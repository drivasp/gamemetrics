"""Armado de payloads para los reportes tácticos del Centro de Reportes."""
from __future__ import annotations

import csv
import io
import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import httpx

from checkout.partner_ledger import admin_business_dashboard
from checkout.partner_payouts import list_all_payouts, list_partner_payouts, partner_balance
from reports.catalog import get_meta, list_catalog
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.pinot_utils import to_bool, to_ms
from social.partner_game_claims import cache_partner_game, list_cached_claims

ETL_BASE = os.getenv("ETL_API_URL", "http://etl-api:5000")
REFUND_WINDOW_MS = 14 * 24 * 60 * 60 * 1000


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


def _envelope(
    meta: dict[str, Any],
    *,
    rows: list[dict],
    kpis: list[dict] | None = None,
    applied_filters: dict | None = None,
    partners: list | None = None,
) -> dict[str, Any]:
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


async def _partners_list() -> list[dict[str, str]]:
    try:
        dash = await admin_business_dashboard(limit=500)
        return [
            {"partner_id": p["partner_id"], "company_name": p.get("company_name") or p["partner_id"]}
            for p in (dash.get("partners") or [])
        ]
    except Exception:
        return []


async def _emp_collection(collection: str, limit: int = 200) -> list[dict[str, Any]]:
    try:
        raw = await pinot_query(
            f"SELECT record_id, data_json, created_at FROM emp_records "
            f"WHERE collection = '{esc(collection)}' AND deleted = false "
            f"ORDER BY created_at DESC LIMIT {int(limit)}"
        )
    except Exception:
        return []
    items = []
    for r in raw or []:
        try:
            data = json.loads(r[1] or "{}")
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data["id"] = r[0]
        data["created_at"] = r[2]
        items.append(data)
    return items


def _pick(d: dict, *keys: str, default: str = "—") -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


# ── Existing S01–S03 / C01–C03 ──────────────────────────────────────────────

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


async def build_s04() -> dict[str, Any]:
    meta = get_meta("GM-S04")
    assert meta
    items = await _emp_collection("empleados")
    rows = []
    for d in items:
        rows.append({
            "nombre": _pick(d, "nombre", "name"),
            "apellido": _pick(d, "apellido", "lastname", default=""),
            "cargo": _pick(d, "cargo"),
            "departamento": _pick(d, "departamento"),
            "email": _pick(d, "email"),
            "fecha_ingreso": _pick(d, "fecha_ingreso"),
            "salario": d.get("salario", ""),
        })
    return _envelope(meta, rows=rows)


async def build_s05() -> dict[str, Any]:
    meta = get_meta("GM-S05")
    assert meta
    items = await _emp_collection("contratos")
    rows = []
    for d in items:
        rows.append({
            "publicador": _pick(d, "publicador", "publisher", "nombre"),
            "tipo": _pick(d, "tipo"),
            "fecha_inicio": _pick(d, "fecha_inicio", "inicio"),
            "fecha_fin": _pick(d, "fecha_fin", "fin"),
            "valor": d.get("valor", d.get("monto", "")),
            "estado": _pick(d, "estado", "status"),
        })
    return _envelope(meta, rows=rows)


async def build_s06() -> dict[str, Any]:
    meta = get_meta("GM-S06")
    assert meta
    rows: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{ETL_BASE}/etl/status")
            r.raise_for_status()
            jobs = r.json()
        if isinstance(jobs, dict):
            for job, info in sorted(jobs.items()):
                if not isinstance(info, dict):
                    continue
                rows.append({
                    "job": job,
                    "status": info.get("status") or "—",
                    "mensaje": info.get("mensaje") or "",
                })
    except Exception as e:
        rows.append({"job": "etl-api", "status": "unreachable", "mensaje": str(e)[:120]})
    return _envelope(meta, rows=rows)


async def build_s07() -> dict[str, Any]:
    meta = get_meta("GM-S07")
    assert meta
    items = await _emp_collection("campanas_marketing")
    rows = []
    for d in items:
        rows.append({
            "nombre": _pick(d, "nombre", "name"),
            "juego": _pick(d, "juego", "game", "producto"),
            "presupuesto": d.get("presupuesto", d.get("budget", "")),
            "canal": _pick(d, "canal", "channel"),
            "estado": _pick(d, "estado", "status"),
            "fecha_inicio": _pick(d, "fecha_inicio", "inicio"),
            "fecha_fin": _pick(d, "fecha_fin", "fin"),
        })
    return _envelope(meta, rows=rows)


async def build_s08() -> dict[str, Any]:
    meta = get_meta("GM-S08")
    assert meta
    items = await _emp_collection("catalogo_distribucion")
    rows = []
    for d in items:
        rows.append({
            "juego": _pick(d, "juego", "nombre", "game"),
            "plataforma": _pick(d, "plataforma", "platform"),
            "precio": d.get("precio", d.get("price", "")),
            "region": _pick(d, "region", "región", "region_code"),
            "estado": _pick(d, "estado", "status"),
        })
    return _envelope(meta, rows=rows)


async def build_s09() -> dict[str, Any]:
    meta = get_meta("GM-S09")
    assert meta
    try:
        raw = await pinot_query(
            "SELECT placement_id, partner_id, product_id, game_name, status, "
            "amount_paid, duration_days, ends_at "
            "FROM fact_featured_placements WHERE deleted = false "
            "ORDER BY created_at DESC LIMIT 200"
        )
    except Exception:
        raw = []
    rows = []
    for r in raw or []:
        pid = str(r[1] or "")
        rows.append({
            "game_name": r[3] or "—",
            "partner_id": pid or "—",
            "company_name": await _company_name(pid) if pid else "—",
            "status": r[4] or "—",
            "amount_paid": float(r[5] or 0),
            "duration_days": int(r[6] or 0),
            "ends_at_iso": _iso(r[7]),
        })
    return _envelope(meta, rows=rows)


async def build_s10() -> dict[str, Any]:
    meta = get_meta("GM-S10")
    assert meta
    try:
        raw = await pinot_query(
            "SELECT user_id, game_name, amount, refunded, purchased_at "
            "FROM fact_purchases WHERE deleted = false "
            "ORDER BY purchased_at DESC LIMIT 200"
        )
    except Exception:
        raw = []
    rows = []
    for r in raw or []:
        rows.append({
            "user_id": r[0] or "—",
            "game_name": r[1] or "—",
            "amount": float(r[2] or 0),
            "refunded": "yes" if to_bool(r[3]) else "no",
            "purchased_at_iso": _iso(r[4]),
        })
    return _envelope(meta, rows=rows)


async def build_s11() -> dict[str, Any]:
    meta = get_meta("GM-S11")
    assert meta
    now = int(time.time() * 1000)
    try:
        raw = await pinot_query(
            "SELECT user_id, game_name, amount, purchased_at, refunded "
            "FROM fact_purchases WHERE deleted = false "
            "ORDER BY purchased_at DESC LIMIT 500"
        )
    except Exception:
        raw = []
    rows = []
    for r in raw or []:
        if to_bool(r[4]):
            continue
        purchased = to_ms(r[3])
        age = now - purchased
        if age < 0 or age > REFUND_WINDOW_MS:
            continue
        days_left = max(0, int((REFUND_WINDOW_MS - age) / (24 * 60 * 60 * 1000)))
        rows.append({
            "user_id": r[0] or "—",
            "game_name": r[1] or "—",
            "amount": float(r[2] or 0),
            "purchased_at_iso": _iso(purchased),
            "days_left": days_left,
        })
    return _envelope(meta, rows=rows[:200])


async def build_s12(partner_id: str) -> dict[str, Any]:
    meta = get_meta("GM-S12")
    assert meta
    partners = await _partners_list()
    if not partner_id:
        return _envelope(meta, rows=[], partners=partners, applied_filters={"partner_id": ""})
    try:
        raw = await pinot_query(
            "SELECT game_name, product_id, submission_status, created_at "
            "FROM fact_partner_games WHERE deleted = false "
            f"AND partner_id = '{esc(partner_id)}' "
            "ORDER BY created_at DESC LIMIT 200"
        )
    except Exception:
        raw = []
    rows = [
        {
            "game_name": r[0] or "—",
            "product_id": r[1] or "—",
            "submission_status": r[2] or "—",
            "created_at_iso": _iso(r[3]),
        }
        for r in (raw or [])
    ]
    return _envelope(meta, rows=rows, partners=partners, applied_filters={"partner_id": partner_id})


async def build_s13(partner_id: str) -> dict[str, Any]:
    meta = get_meta("GM-S13")
    assert meta
    partners = await _partners_list()
    if not partner_id:
        return _envelope(meta, rows=[], partners=partners, applied_filters={"partner_id": ""})
    try:
        payouts = await list_partner_payouts(partner_id, limit=100)
    except Exception:
        payouts = []
    rows = [
        {
            "payout_id": p.get("payout_id") or "—",
            "amount": float(p.get("amount") or 0),
            "method": p.get("method") or "—",
            "status": p.get("status") or "—",
            "reference": p.get("reference") or "—",
            "paid_at_iso": _iso(p.get("paid_at") or p.get("created_at")),
        }
        for p in payouts
    ]
    return _envelope(meta, rows=rows, partners=partners, applied_filters={"partner_id": partner_id})


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
    partners_list = await _partners_list()
    if not partner_id:
        return _envelope(meta, rows=[], kpis=[], applied_filters={"partner_id": ""}, partners=partners_list)
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
    return _envelope(meta, rows=rows, kpis=kpis, applied_filters={"partner_id": partner_id}, partners=partners_list)


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


def _week(n: int | None) -> int:
    try:
        w = int(n or 1)
    except (TypeError, ValueError):
        w = 1
    return max(1, min(17, w))


async def build_c04(week: int | None = 1) -> dict[str, Any]:
    meta = get_meta("GM-C04")
    assert meta
    w = _week(week)
    try:
        raw = await pinot_query(f"SELECT COUNT(*) FROM fact_videogames WHERE semana = {w}")
        total = int(raw[0][0]) if raw else 0
    except Exception:
        total = 0
    rows = [{"semana": w, "total_juegos": total}]
    kpis = [{"key": "total", "label": f"Juegos semana {w}", "value": total, "format": "number"}]
    return _envelope(meta, rows=rows, kpis=kpis, applied_filters={"week": str(w)})


async def build_c05(week: int | None = 1) -> dict[str, Any]:
    meta = get_meta("GM-C05")
    assert meta
    w = _week(week)
    try:
        raw = await pinot_query(
            f"SELECT genres FROM fact_videogames WHERE semana = {w} LIMIT 5000"
        )
    except Exception:
        raw = []
    counter: Counter[str] = Counter()
    for r in raw or []:
        genres = str(r[0] or "")
        parts = [g.strip() for g in genres.replace(",", "||").split("||") if g.strip()]
        if not parts:
            counter["(sin género)"] += 1
        else:
            for g in parts:
                counter[g] += 1
    rows = [{"genre": g, "game_count": c} for g, c in counter.most_common(50)]
    kpis = [{"key": "genres", "label": "Géneros distintos", "value": len(counter), "format": "number"}]
    return _envelope(meta, rows=rows, kpis=kpis, applied_filters={"week": str(w)})


async def build_c06(week: int | None = 1) -> dict[str, Any]:
    meta = get_meta("GM-C06")
    assert meta
    w = _week(week)
    try:
        raw = await pinot_query(
            f"SELECT platforms FROM fact_videogames WHERE semana = {w} LIMIT 5000"
        )
    except Exception:
        raw = []
    counter: Counter[str] = Counter()
    for r in raw or []:
        plats = str(r[0] or "")
        parts = [p.strip() for p in plats.replace(",", "||").split("||") if p.strip()]
        if not parts:
            counter["(sin plataforma)"] += 1
        else:
            for p in parts:
                counter[p] += 1
    rows = [{"platform": p, "game_count": c} for p, c in counter.most_common(50)]
    kpis = [{"key": "platforms", "label": "Plataformas distintas", "value": len(counter), "format": "number"}]
    return _envelope(meta, rows=rows, kpis=kpis, applied_filters={"week": str(w)})


async def build_c07(week: int | None = 1) -> dict[str, Any]:
    meta = get_meta("GM-C07")
    assert meta
    w = _week(week)
    try:
        raw = await pinot_query(
            f"SELECT name, rating, metacritic, genres FROM fact_videogames "
            f"WHERE semana = {w} AND rating > 0 "
            f"ORDER BY rating DESC LIMIT 10"
        )
    except Exception:
        raw = []
    rows = []
    for i, r in enumerate(raw or [], 1):
        rows.append({
            "rank": i,
            "name": r[0] or "—",
            "rating": float(r[1] or 0),
            "metacritic": r[2] if r[2] is not None else "—",
            "genres": r[3] or "—",
        })
    return _envelope(meta, rows=rows, applied_filters={"week": str(w)})


async def build_c08(date_from: str | None = None, date_to: str | None = None) -> dict[str, Any]:
    meta = get_meta("GM-C08")
    assert meta
    conditions = ["deleted = false"]
    if date_from:
        conditions.append(f"fecha >= '{esc(date_from)}'")
    if date_to:
        conditions.append(f"fecha <= '{esc(date_to)}'")
    where = " AND ".join(conditions)
    try:
        raw = await pinot_query(
            "SELECT fecha, gmv, platform_fee, publisher_net, orders_count, units_sold, refund_count "
            f"FROM report_kpi_ventas_diarias WHERE {where} ORDER BY fecha ASC LIMIT 400"
        )
    except Exception:
        raw = []
    rows = [
        {
            "fecha": r[0],
            "gmv": float(r[1] or 0),
            "platform_fee": float(r[2] or 0),
            "publisher_net": float(r[3] or 0),
            "orders_count": int(r[4] or 0),
            "units_sold": int(r[5] or 0),
            "refund_count": int(r[6] or 0),
        }
        for r in (raw or [])
    ]
    kpis = [
        {"key": "days", "label": "Días en rango", "value": len(rows), "format": "number"},
        {"key": "gmv_total", "label": "GMV del rango", "value": sum(r["gmv"] for r in rows), "format": "currency"},
        {"key": "orders_total", "label": "Órdenes del rango", "value": sum(r["orders_count"] for r in rows), "format": "number"},
    ]
    return _envelope(
        meta, rows=rows, kpis=kpis,
        applied_filters={"date_from": date_from or "", "date_to": date_to or ""},
    )


async def build_c09() -> dict[str, Any]:
    meta = get_meta("GM-C09")
    assert meta
    try:
        raw = await pinot_query(
            "SELECT company_name, games_count, units_sold, gross_revenue, platform_fee, "
            "publisher_net, refund_count, paid_out "
            "FROM report_kpi_partners_resumen WHERE deleted = false ORDER BY gross_revenue DESC LIMIT 200"
        )
    except Exception:
        raw = []
    rows = [
        {
            "company_name": r[0] or "—",
            "games_count": int(r[1] or 0),
            "units_sold": int(r[2] or 0),
            "gross_revenue": float(r[3] or 0),
            "platform_fee": float(r[4] or 0),
            "publisher_net": float(r[5] or 0),
            "refund_count": int(r[6] or 0),
            "paid_out": float(r[7] or 0),
        }
        for r in (raw or [])
    ]
    kpis = [
        {"key": "partners_count", "label": "Estudios", "value": len(rows), "format": "number"},
        {"key": "gross_total", "label": "Bruto total", "value": sum(r["gross_revenue"] for r in rows), "format": "currency"},
        {"key": "net_total", "label": "Neto total", "value": sum(r["publisher_net"] for r in rows), "format": "currency"},
    ]
    return _envelope(meta, rows=rows, kpis=kpis)


async def build_report(
    code: str,
    *,
    status: str | None = None,
    partner_id: str | None = None,
    week: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    c = (code or "").upper()
    builders = {
        "GM-S01": lambda: build_s01(status or "pending"),
        "GM-S02": build_s02,
        "GM-S03": lambda: build_s03(status or "open"),
        "GM-S04": build_s04,
        "GM-S05": build_s05,
        "GM-S06": build_s06,
        "GM-S07": build_s07,
        "GM-S08": build_s08,
        "GM-S09": build_s09,
        "GM-S10": build_s10,
        "GM-S11": build_s11,
        "GM-S12": lambda: build_s12(partner_id or ""),
        "GM-S13": lambda: build_s13(partner_id or ""),
        "GM-C01": build_c01,
        "GM-C02": lambda: build_c02(partner_id or ""),
        "GM-C03": build_c03,
        "GM-C04": lambda: build_c04(week),
        "GM-C05": lambda: build_c05(week),
        "GM-C06": lambda: build_c06(week),
        "GM-C07": lambda: build_c07(week),
        "GM-C08": lambda: build_c08(date_from, date_to),
        "GM-C09": build_c09,
    }
    fn = builders.get(c)
    if not fn:
        raise KeyError(c)
    return await fn()


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
    items = list_catalog()
    return {
        "items": items,
        "generated_at": _now_iso(),
        "count": len(items),
    }

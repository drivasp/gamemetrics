"""
DAG horario: materializa KPIs pre-agregados (report_kpi_partners_resumen,
report_kpi_ventas_diarias) y mide cuánto se gana en tiempo de consulta frente
al informe "tradicional" (agregación en caliente sobre filas crudas, el mismo
patrón que hoy usa backend/checkout/partner_ledger.py::platform_gmv_summary).

Tasks:
  sql_compat_check   -> intenta un JOIN real (motor multi-stage de Pinot) y
                         cae a la alternativa de dos SELECT + merge si el
                         broker lo rechaza. Documenta la ruta que funcionó.
  extract            -> filas crudas de fact_partner_ledger / _accounts / _games / _payouts
  transform          -> agregación Python -> filas por partner y por día
  load                -> upsert a report_kpi_* vía Kafka (clave = partner_id / fecha)
  benchmark_vs_tradicional -> cronometra "tradicional" vs "tabla pre-agregada"
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator

from common.kafka_client import send_and_flush
from common.pinot_client import run_sql, run_sql_compatible

REPORTS_OUTPUT_DIR = "/opt/airflow/reports_output"

default_args = {
    "owner": "gamemetrics",
    "retries": 1,
}


def _money(x: float) -> float:
    return round(float(x) + 1e-9, 2)


def _fetch_raw_ledger() -> list[list]:
    return run_sql(
        "SELECT ledger_entry_id, partner_id, entry_type, quantity, gross_amount, "
        "platform_fee_amount, publisher_net_amount, created_at "
        "FROM fact_partner_ledger WHERE deleted = false LIMIT 5000"
    )


def _fetch_raw_accounts() -> list[list]:
    return run_sql(
        "SELECT partner_id, company_name, status FROM fact_partner_accounts "
        "WHERE deleted = false LIMIT 200"
    )


def _fetch_raw_games_count() -> dict[str, int]:
    rows = run_sql(
        "SELECT partner_id, product_id FROM fact_partner_games WHERE deleted = false LIMIT 500"
    )
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[str(r[0])] += 1
    return dict(counts)


def _fetch_raw_payouts_paid() -> dict[str, float]:
    rows = run_sql(
        "SELECT partner_id, amount FROM fact_partner_payouts "
        "WHERE deleted = false AND status = 'paid' LIMIT 500"
    )
    paid: dict[str, float] = defaultdict(float)
    for r in rows:
        paid[str(r[0])] = _money(paid[str(r[0])] + float(r[1] or 0))
    return dict(paid)


# ── sql_compat_check: demuestra el fallback de compatibilidad de SQL ────────

def _sql_compat_check(**context) -> dict:
    preferred = (
        "SELECT l.partner_id, a.company_name, SUM(l.gross_amount) AS gross "
        "FROM fact_partner_ledger l JOIN fact_partner_accounts a "
        "ON l.partner_id = a.partner_id "
        "WHERE l.deleted = false AND a.deleted = false "
        "GROUP BY l.partner_id, a.company_name LIMIT 200"
    )

    def fallback() -> list[list]:
        ledger = _fetch_raw_ledger()
        accounts = {str(r[0]): r[1] for r in _fetch_raw_accounts()}
        totals: dict[str, float] = defaultdict(float)
        for r in ledger:
            totals[str(r[1])] += float(r[4] or 0)
        return [[pid, accounts.get(pid, "—"), _money(v)] for pid, v in totals.items()]

    rows, route = run_sql_compatible(preferred, fallback)
    result = {"route": route, "row_count": len(rows)}
    print(f"[sql_compat_check] Ruta usada: {route} ({len(rows)} filas) -- ver docs/TA13_AIRFLOW_ETL_KPI.md §3")
    return result


# ── extract / transform / load de los KPI ────────────────────────────────────

def _extract(**context) -> dict:
    return {
        "ledger": _fetch_raw_ledger(),
        "accounts": _fetch_raw_accounts(),
        "games_count": _fetch_raw_games_count(),
        "payouts_paid": _fetch_raw_payouts_paid(),
    }


def _transform(**context) -> dict:
    raw = context["ti"].xcom_pull(task_ids="extract")
    ledger = raw["ledger"]
    accounts = raw["accounts"]
    games_count = raw["games_count"]
    payouts_paid = raw["payouts_paid"]

    partners_agg: dict[str, dict] = {}
    for pid, company, status in [(str(r[0]), r[1] or "—", r[2] or "active") for r in accounts]:
        partners_agg[pid] = {
            "partner_id": pid,
            "company_name": company,
            "status": status,
            "games_count": games_count.get(pid, 0),
            "units_sold": 0,
            "gross_revenue": 0.0,
            "platform_fee": 0.0,
            "publisher_net": 0.0,
            "refund_count": 0,
            "paid_out": payouts_paid.get(pid, 0.0),
        }

    daily_agg: dict[str, dict] = {}
    for entry_id, pid, entry_type, qty, gross, fee, net, created_at in ledger:
        pid = str(pid)
        p = partners_agg.setdefault(pid, {
            "partner_id": pid, "company_name": "—", "status": "active", "games_count": 0,
            "units_sold": 0, "gross_revenue": 0.0, "platform_fee": 0.0, "publisher_net": 0.0,
            "refund_count": 0, "paid_out": payouts_paid.get(pid, 0.0),
        })
        if entry_type == "sale":
            p["units_sold"] += int(qty or 0)
            p["gross_revenue"] = _money(p["gross_revenue"] + float(gross or 0))
            p["platform_fee"] = _money(p["platform_fee"] + float(fee or 0))
            p["publisher_net"] = _money(p["publisher_net"] + float(net or 0))
        elif entry_type == "refund":
            p["refund_count"] += 1
            p["gross_revenue"] = _money(p["gross_revenue"] + float(gross or 0))
            p["platform_fee"] = _money(p["platform_fee"] + float(fee or 0))
            p["publisher_net"] = _money(p["publisher_net"] + float(net or 0))

        if entry_type in ("sale", "refund"):
            fecha = datetime.fromtimestamp(int(created_at) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            d = daily_agg.setdefault(fecha, {
                "fecha": fecha, "gmv": 0.0, "platform_fee": 0.0, "publisher_net": 0.0,
                "orders_count": 0, "units_sold": 0, "refund_count": 0,
            })
            d["gmv"] = _money(d["gmv"] + float(gross or 0))
            d["platform_fee"] = _money(d["platform_fee"] + float(fee or 0))
            d["publisher_net"] = _money(d["publisher_net"] + float(net or 0))
            if entry_type == "sale":
                d["orders_count"] += 1
                d["units_sold"] += int(qty or 0)
            else:
                d["refund_count"] += 1

    print(f"[transform] {len(partners_agg)} partners, {len(daily_agg)} días agregados")
    return {"partners": list(partners_agg.values()), "daily": list(daily_agg.values())}


def _load(**context) -> None:
    agg = context["ti"].xcom_pull(task_ids="transform")
    now_ms = int(time.time() * 1000)

    partner_rows = {}
    for p in agg["partners"]:
        row = dict(p)
        row["updated_at"] = now_ms
        row["deleted"] = False
        partner_rows[p["partner_id"]] = row
    n1 = send_and_flush("report_kpi_partners_resumen", partner_rows)

    daily_rows = {}
    for d in agg["daily"]:
        row = dict(d)
        day_ts = int(datetime.strptime(d["fecha"], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
        row["fecha_epoch_ms"] = day_ts
        row["deleted"] = False
        daily_rows[d["fecha"]] = row
    n2 = send_and_flush("report_kpi_ventas_diarias", daily_rows)

    print(f"[load] Upsert: {n1} partners -> report_kpi_partners_resumen, {n2} días -> report_kpi_ventas_diarias")


# ── benchmark: tradicional (agregación en caliente) vs. tabla pre-agregada ──

def _benchmark(**context) -> dict:
    t0 = time.perf_counter()
    ledger = _fetch_raw_ledger()
    accounts = {str(r[0]): r[1] for r in _fetch_raw_accounts()}
    totals: dict[str, dict] = defaultdict(lambda: {"gross": 0.0, "fee": 0.0, "net": 0.0, "units": 0})
    for _id, pid, entry_type, qty, gross, fee, net, _ts in ledger:
        pid = str(pid)
        if entry_type != "sale":
            continue
        t = totals[pid]
        t["gross"] = _money(t["gross"] + float(gross or 0))
        t["fee"] = _money(t["fee"] + float(fee or 0))
        t["net"] = _money(t["net"] + float(net or 0))
        t["units"] += int(qty or 0)
    _ = [{"partner_id": pid, "company_name": accounts.get(pid, "—"), **v} for pid, v in totals.items()]
    t_tradicional = time.perf_counter() - t0

    t0 = time.perf_counter()
    _ = run_sql(
        "SELECT partner_id, company_name, gross_revenue, platform_fee, publisher_net, units_sold "
        "FROM report_kpi_partners_resumen WHERE deleted = false LIMIT 200"
    )
    t_preagregado = time.perf_counter() - t0

    result = {
        "run_id": context["run_id"],
        "measured_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "informe_tradicional_seconds": round(t_tradicional, 4),
        "informe_kpi_preagregado_seconds": round(t_preagregado, 4),
        "speedup_x": round(t_tradicional / t_preagregado, 2) if t_preagregado > 0 else None,
        "rows_scanned_tradicional": len(ledger),
        "rows_scanned_preagregado": len(totals),
    }

    os.makedirs(REPORTS_OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(REPORTS_OUTPUT_DIR, f"benchmark_{context['run_id'].replace(':', '_').replace('+', '_')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[benchmark] tradicional={t_tradicional:.4f}s  pre-agregado={t_preagregado:.4f}s  -> {out_path}")
    return result


with DAG(
    dag_id="gamemetrics_kpi_reportes",
    description="Horario: materializa KPIs pre-agregados y mide tradicional vs. pre-agregado",
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["gamemetrics", "kpi", "benchmark"],
) as dag:
    sql_compat_check = PythonOperator(task_id="sql_compat_check", python_callable=_sql_compat_check)
    extract = PythonOperator(task_id="extract", python_callable=_extract)
    transform = PythonOperator(task_id="transform", python_callable=_transform)
    load = PythonOperator(task_id="load", python_callable=_load)
    benchmark = PythonOperator(task_id="benchmark_vs_tradicional", python_callable=_benchmark)

    sql_compat_check >> extract >> transform >> load >> benchmark

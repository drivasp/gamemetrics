"""
Informe "tradicional a punta de SQL normal" -- para correr standalone,
FUERA de Airflow, desde la máquina del desarrollador (requiere solo
`pip install httpx`, no Airflow).

Reproduce exactamente lo que hace hoy backend/checkout/partner_ledger.py
(platform_gmv_summary / admin_business_dashboard) para los informes GM-C01/C03:
un SELECT crudo sobre fact_partner_ledger + agregación en un loop de Python,
sin materializar nada. Es el "antes" contra el que se compara la tabla
report_kpi_partners_resumen que materializa dag_kpi_reportes.py cada hora.

Uso:
  cd airflow/reports_output
  python run_informe_tradicional.py
  (opcional) $env:PINOT_BROKER_URL = "http://localhost:8099"
"""
from __future__ import annotations

import os
import time
from collections import defaultdict

import httpx

PINOT_BROKER_URL = os.getenv("PINOT_BROKER_URL", "http://localhost:8099")
QUERY_URL = f"{PINOT_BROKER_URL}/query/sql"


def pinot_query(sql: str) -> list[list]:
    resp = httpx.post(QUERY_URL, json={"sql": sql}, timeout=30.0)
    resp.raise_for_status()
    body = resp.json()
    if body.get("exceptions"):
        raise RuntimeError(body["exceptions"][0].get("message", "Pinot query error"))
    return (body.get("resultTable") or {}).get("rows") or []


def money(x: float) -> float:
    return round(float(x) + 1e-9, 2)


def main() -> None:
    print("=" * 70)
    print("  Informe tradicional (SQL crudo + agregación en Python)")
    print(f"  Broker: {PINOT_BROKER_URL}")
    print("=" * 70)

    t0 = time.perf_counter()

    ledger = pinot_query(
        "SELECT partner_id, entry_type, quantity, gross_amount, "
        "platform_fee_amount, publisher_net_amount "
        "FROM fact_partner_ledger WHERE deleted = false LIMIT 5000"
    )
    accounts = pinot_query(
        "SELECT partner_id, company_name FROM fact_partner_accounts WHERE deleted = false LIMIT 200"
    )
    company_by_id = {str(r[0]): (r[1] or "—") for r in accounts}

    totals: dict[str, dict] = defaultdict(lambda: {"gross": 0.0, "fee": 0.0, "net": 0.0, "units": 0, "refunds": 0})
    for partner_id, entry_type, qty, gross, fee, net in ledger:
        pid = str(partner_id)
        t = totals[pid]
        if entry_type == "sale":
            t["gross"] = money(t["gross"] + float(gross or 0))
            t["fee"] = money(t["fee"] + float(fee or 0))
            t["net"] = money(t["net"] + float(net or 0))
            t["units"] += int(qty or 0)
        elif entry_type == "refund":
            t["refunds"] += 1

    rows = sorted(
        (
            {"partner_id": pid, "company_name": company_by_id.get(pid, "—"), **v}
            for pid, v in totals.items()
        ),
        key=lambda r: r["gross"],
        reverse=True,
    )

    elapsed = time.perf_counter() - t0

    print(f"\n{len(rows)} estudios agregados en {len(ledger)} filas de ledger crudas.\n")
    for r in rows[:10]:
        print(f"  {r['company_name']:<28} gross=${r['gross']:>10,.2f}  fee=${r['fee']:>9,.2f}  "
              f"net=${r['net']:>10,.2f}  units={r['units']:>4}  refunds={r['refunds']}")

    print(f"\nTiempo total (SQL + agregación Python): {elapsed:.4f} s")
    print("Comparar con: airflow/reports_output/benchmark_<run_id>.json"
          " (task benchmark_vs_tradicional de dag_kpi_reportes)")
    print("=" * 70)


if __name__ == "__main__":
    main()

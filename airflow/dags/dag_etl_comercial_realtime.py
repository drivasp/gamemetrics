"""
Refresco comercial recurrente (cada 6h): agrega ventas nuevas al ledger B2B.

Política deliberada: INCREMENTAL, nunca wipe. Un job que corre cada 6 horas
no puede borrar `fact_partner_ledger` en cada corrida -- borraría ventas
reales. Este DAG solo agrega entradas nuevas con `ledger_entry_id` únicos
(uuid4), nunca reutiliza ni pisa las existentes -- lo opuesto al patrón de
etl/22_wipe_business_demo_data.py (que se deja intacto, para uso administrativo
manual, no programado). Ver docs/TA13_AIRFLOW_ETL_KPI.md sección 4.

extract: lee partners activos + juegos aprobados desde Pinot (fuente real,
no una lista hardcodeada) -> transform: genera 1-4 ventas sintéticas nuevas
por juego con timestamp "ahora" -> load: publica a Kafka (mismo topic/schema
que ya consume fact_partner_ledger).
"""
from __future__ import annotations

import random
import time
import uuid
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from common.kafka_client import send_and_flush
from common.pinot_client import run_sql

UNIT_PRICE_DEFAULT = 19.99
SHARE_DEFAULT = 70.0

default_args = {
    "owner": "gamemetrics",
    "retries": 1,
}


def _money(x: float) -> float:
    return round(float(x) + 1e-9, 2)


def _split(gross: float, share_pct: float) -> tuple[float, float, float]:
    g = _money(gross)
    fee = _money(g * (100.0 - share_pct) / 100.0)
    net = _money(g - fee)
    return g, fee, net


def _extract(**context) -> list[dict]:
    partners = run_sql(
        "SELECT partner_id, revenue_share_pct FROM fact_partner_accounts "
        "WHERE deleted = false AND status = 'active' LIMIT 200"
    )
    share_by_partner = {str(r[0]): float(r[1] or SHARE_DEFAULT) for r in partners}

    games = run_sql(
        "SELECT partner_id, product_id, game_name FROM fact_partner_games "
        "WHERE deleted = false AND submission_status = 'approved' LIMIT 500"
    )
    approved = [
        {"partner_id": str(r[0]), "product_id": str(r[1]), "game_name": r[2] or str(r[1])}
        for r in games
        if str(r[0]) in share_by_partner
    ]
    print(f"[extract] {len(share_by_partner)} partners activos, {len(approved)} juegos aprobados")
    return approved


def _transform(**context) -> list[dict]:
    approved = context["ti"].xcom_pull(task_ids="extract") or []
    partners = run_sql(
        "SELECT partner_id, revenue_share_pct FROM fact_partner_accounts "
        "WHERE deleted = false AND status = 'active' LIMIT 200"
    )
    share_by_partner = {str(r[0]): float(r[1] or SHARE_DEFAULT) for r in partners}
    now_ms = int(time.time() * 1000)

    new_entries: list[dict] = []
    for game in approved:
        n_new = random.randint(1, 4)
        share = share_by_partner.get(game["partner_id"], SHARE_DEFAULT)
        for _ in range(n_new):
            qty = 1 if random.random() < 0.85 else random.randint(2, 3)
            gross, fee, net = _split(UNIT_PRICE_DEFAULT * qty, share)
            order_id = f"ord_{uuid.uuid4().hex[:10]}"
            entry_id = f"sale_{order_id}_{game['product_id']}"
            new_entries.append({
                "ledger_entry_id": entry_id,
                "partner_id": game["partner_id"],
                "order_id": order_id,
                "product_id": game["product_id"],
                "game_name": game["game_name"],
                "buyer_user_id": f"user_{uuid.uuid4().hex[:8]}",
                "entry_type": "sale",
                "currency": "USD",
                "status": "available",
                "related_entry_id": "",
                "quantity": qty,
                "gross_amount": gross,
                "platform_fee_amount": fee,
                "publisher_net_amount": net,
                "publisher_share_pct": share,
                "platform_take_rate_pct": _money(100.0 - share),
                "created_at": now_ms,
                "deleted": False,
            })
    print(f"[transform] {len(new_entries)} ventas nuevas generadas para esta corrida")
    return new_entries


def _load(**context) -> None:
    new_entries = context["ti"].xcom_pull(task_ids="transform") or []
    if not new_entries:
        print("[load] Nada que publicar (sin juegos aprobados todavía).")
        return
    rows_by_key = {e["ledger_entry_id"]: e for e in new_entries}
    n = send_and_flush("fact_partner_ledger", rows_by_key)
    print(f"[load] {n} entradas de ledger publicadas a Kafka (append incremental, sin borrar nada).")


with DAG(
    dag_id="gamemetrics_etl_comercial_realtime",
    description="Cada 6h: agrega ventas nuevas al ledger B2B (incremental, nunca wipe)",
    schedule="0 */6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["gamemetrics", "etl", "comercial"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=_extract)
    transform = PythonOperator(task_id="transform", python_callable=_transform)
    load = PythonOperator(task_id="load", python_callable=_load)

    extract >> transform >> load

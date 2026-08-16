"""
DAG manual (schedule=None): crea/repara las tablas Pinot nuevas para los
informes KPI pre-agregados (report_kpi_partners_resumen, report_kpi_ventas_diarias).

No corre en un horario porque es DDL, no ETL recurrente -- se dispara a mano
la primera vez (o si se necesita recrear el esquema) desde la UI de Airflow.
Idempotente: borra si existe y vuelve a crear, igual que los scripts
etl/05_create_empresa_tables.py / etl/13_create_phase2_tables.py.
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from common.pinot_client import setup_table_idempotent, wait_for_pinot

KPI_TABLES = [
    "report_kpi_partners_resumen",
    "report_kpi_ventas_diarias",
]

default_args = {
    "owner": "gamemetrics",
    "retries": 1,
}


def _bootstrap_tables() -> None:
    wait_for_pinot()
    failed = [name for name in KPI_TABLES if not setup_table_idempotent(name)]
    if failed:
        raise RuntimeError(f"No se pudieron crear las tablas: {failed}")
    print(f"[dag_bootstrap_ddl] OK: {len(KPI_TABLES)} tablas KPI listas")


with DAG(
    dag_id="gamemetrics_bootstrap_ddl",
    description="DDL manual: crea las tablas Pinot report_kpi_* para los informes pre-agregados",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["gamemetrics", "ddl", "manual"],
) as dag:
    bootstrap_tables = PythonOperator(
        task_id="bootstrap_kpi_tables",
        python_callable=_bootstrap_tables,
    )

"""
ETL recurrente del catálogo analítico (fact_videogames), corriendo cada día.

Reutiliza las funciones ya factorizadas en etl/04_ingest_pinot.py (no las
reescribe): prepare_dataframe() = extract+transform base, apply_variation()
= transform por semana, ingest_dataframe() = load. Se separan en 3 tasks de
Airflow (extract / transform / load) para que se vean como etapas
independientes en la UI, tal como pide el enunciado.

Idempotente: antes de cargar, mira semanas_cargadas.json (mismo estado que
ya usa el resto del proyecto) y si la próxima semana objetivo ya está
cargada, salta el DAG entero sin tocar Pinot (evita duplicar filas en un
rerun accidental).
"""
from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator

from common.etl_loader import ETL_SRC_DIR, load_etl_module

MODULE_FILE = "04_ingest_pinot.py"
TMP_DIR = os.path.join(ETL_SRC_DIR, "data", "stage", "_airflow_tmp")

default_args = {
    "owner": "gamemetrics",
    "retries": 1,
}


def _next_semana(module) -> tuple[int, set[int]]:
    semanas = module.get_semanas_cargadas()
    ultima = max(semanas) if semanas else 0
    objetivo = min(17, ultima + 1)
    return objetivo, semanas


def _extract(**context) -> dict:
    os.chdir(ETL_SRC_DIR)
    module = load_etl_module(MODULE_FILE)
    module.wait_for_pinot_controller()

    semana, semanas_cargadas = _next_semana(module)
    if semana in semanas_cargadas:
        raise AirflowSkipException(
            f"Catálogo completo: las 17 semanas ya están cargadas (semanas={sorted(semanas_cargadas)})"
        )

    if not module.tabla_existe():
        print("[extract] Tabla fact_videogames no existe en Pinot todavía -> creando (primera corrida).")
        module.reset_table()

    df_base = module.prepare_dataframe()
    os.makedirs(TMP_DIR, exist_ok=True)
    path = os.path.join(TMP_DIR, "extract_base.parquet")
    df_base.to_parquet(path)
    print(f"[extract] {len(df_base)} filas base -> {path} (semana objetivo: {semana})")
    return {"path": path, "semana": semana}


def _transform(**context) -> dict:
    import pandas as pd

    os.chdir(ETL_SRC_DIR)
    module = load_etl_module(MODULE_FILE)
    xcom = context["ti"].xcom_pull(task_ids="extract")
    df_base = pd.read_parquet(xcom["path"])
    semana = xcom["semana"]

    df = module.apply_variation(df_base, semana)
    df["semana"] = semana
    df = df[module.COLUMNAS]

    path = os.path.join(TMP_DIR, f"transform_semana_{semana}.parquet")
    df.to_parquet(path)
    print(f"[transform] Semana {semana}: variación aplicada, {len(df)} filas -> {path}")
    return {"path": path, "semana": semana}


def _load(**context) -> None:
    import pandas as pd

    os.chdir(ETL_SRC_DIR)
    module = load_etl_module(MODULE_FILE)
    xcom = context["ti"].xcom_pull(task_ids="transform")
    df = pd.read_parquet(xcom["path"])
    semana = xcom["semana"]

    lotes_ok = module.ingest_dataframe(df, semana)
    if lotes_ok <= 0:
        raise RuntimeError(f"No se pudo ingestar la semana {semana} a Pinot")

    semanas_cargadas = module.get_semanas_cargadas()
    semanas_cargadas.add(semana)
    module.save_semanas_cargadas(semanas_cargadas)
    print(f"[load] Semana {semana} cargada. Semanas en estado: {sorted(semanas_cargadas)}")


with DAG(
    dag_id="gamemetrics_etl_catalogo_videogames",
    description="ETL diario: siguiente semana del catálogo analítico -> fact_videogames",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["gamemetrics", "etl", "catalogo"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=_extract)
    transform = PythonOperator(task_id="transform", python_callable=_transform)
    load = PythonOperator(task_id="load", python_callable=_load)

    extract >> transform >> load

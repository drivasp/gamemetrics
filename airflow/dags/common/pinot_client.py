"""
Cliente PinotSQL para los DAGs de Airflow + helpers de DDL de tablas.

Apache Pinot no habla SQL estándar: expone su propio dialecto (PinotSQL) vía
POST {broker}/query/sql. Este módulo centraliza dos cosas:

1. Ejecución de queries con manejo explícito de errores del broker (Pinot
   devuelve HTTP 200 con un array "exceptions" en el body cuando la consulta
   es sintácticamente inválida para su motor — no lanza 4xx/5xx como un RDBMS).
2. `run_sql_compatible()`: si una consulta "preferida" (p.ej. un JOIN, que en
   Pinot 1.0 solo corre en el motor multi-stage) falla por incompatibilidad,
   cae automáticamente a una alternativa compatible con el motor single-stage.
   Esto es el mecanismo que resuelve "en caso de incompatibilidad de SQL,
   buscar una versión compatible" pedido en el enunciado.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable

import httpx
import requests

PINOT_CONTROLLER_URL = os.getenv("PINOT_CONTROLLER_URL", "http://pinot-controller:9000")
PINOT_BROKER_URL = os.getenv("PINOT_BROKER_URL", "http://pinot-broker:8099")
PINOT_QUERY_URL = f"{PINOT_BROKER_URL}/query/sql"
TIMEOUT = 15.0


class PinotQueryError(RuntimeError):
    """El broker de Pinot respondió con `exceptions` para esta consulta."""


class PinotIncompatibleSqlError(PinotQueryError):
    """La consulta preferida no es compatible con el motor SQL disponible."""


def wait_for_pinot(attempts: int = 20, delay_s: float = 5.0) -> None:
    for attempt in range(attempts):
        try:
            r = requests.get(f"{PINOT_CONTROLLER_URL}/health", timeout=5)
            if r.status_code == 200:
                return
        except Exception:
            pass
        print(f"[pinot_client] Esperando Pinot Controller... {attempt + 1}/{attempts}")
        time.sleep(delay_s)
    raise RuntimeError("Pinot Controller no respondió a tiempo")


def run_sql(sql: str, *, use_multistage_engine: bool = False) -> list[list[Any]]:
    """Ejecuta una consulta PinotSQL cruda. Lanza PinotQueryError si el broker
    reporta excepciones (incluye incompatibilidades de sintaxis/motor)."""
    payload: dict[str, Any] = {"sql": sql}
    if use_multistage_engine:
        payload["queryOptions"] = "useMultistageEngine=true"
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(PINOT_QUERY_URL, json=payload)
        resp.raise_for_status()
        body = resp.json()
    if body.get("exceptions"):
        msg = body["exceptions"][0].get("message", "Pinot query error")
        raise PinotQueryError(msg)
    return (body.get("resultTable") or {}).get("rows") or []


def run_sql_compatible(
    preferred_sql: str,
    fallback: Callable[[], list[list[Any]]],
    *,
    use_multistage_engine: bool = True,
) -> tuple[list[list[Any]], str]:
    """Intenta `preferred_sql` (motor multi-stage, permite JOIN). Si el broker
    la rechaza por incompatibilidad, ejecuta `fallback()` -- típicamente dos
    SELECT de tabla única + merge en Python, el patrón single-stage-safe que
    ya usa el resto del backend de GameMetrics.

    Devuelve (rows, "preferred"|"fallback") para que el DAG pueda loguear /
    documentar cuál ruta terminó funcionando contra el Pinot real del stack.
    """
    try:
        rows = run_sql(preferred_sql, use_multistage_engine=use_multistage_engine)
        return rows, "preferred"
    except PinotQueryError as exc:
        print(f"[pinot_client] Consulta preferida incompatible ({exc}); usando fallback compatible.")
        return fallback(), "fallback"


# ── DDL helpers (mismo patrón que etl/07_create_dimensions.py, etl/13_create_phase2_tables.py) ──

SCHEMAS_DIR = os.getenv("PINOT_SCHEMAS_DIR", "/opt/airflow/pinot_schemas")


def _load_json(filename: str) -> dict:
    import json

    with open(os.path.join(SCHEMAS_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def delete_table(name: str) -> None:
    r = requests.delete(f"{PINOT_CONTROLLER_URL}/tables/{name}?type=realtime", timeout=30)
    print(f"[pinot_client] DELETE table {name}: {r.status_code}")


def delete_schema(name: str) -> None:
    r = requests.delete(f"{PINOT_CONTROLLER_URL}/schemas/{name}", timeout=30)
    print(f"[pinot_client] DELETE schema {name}: {r.status_code}")


def create_schema(schema: dict) -> bool:
    r = requests.post(
        f"{PINOT_CONTROLLER_URL}/schemas",
        json=schema,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    ok = r.status_code in (200, 201)
    print(f"[pinot_client] POST schema {schema['schemaName']}: {r.status_code}" + ("" if ok else f" — {r.text[:200]}"))
    return ok


def create_table(table: dict) -> bool:
    r = requests.post(
        f"{PINOT_CONTROLLER_URL}/tables",
        json=table,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    ok = r.status_code in (200, 201)
    print(f"[pinot_client] POST table {table['tableName']}: {r.status_code}" + ("" if ok else f" — {r.text[:300]}"))
    return ok


def setup_table_idempotent(name: str) -> bool:
    """Borra (si existe) y recrea schema+table para `name`. Seguro de re-correr
    (drop-if-exists), igual que los scripts numerados de etl/."""
    print(f"[pinot_client] --- {name} ---")
    delete_table(name)
    time.sleep(1)
    delete_schema(name)
    time.sleep(1)
    if not create_schema(_load_json(f"schema_{name}.json")):
        return False
    time.sleep(1)
    return create_table(_load_json(f"table_{name}.json"))

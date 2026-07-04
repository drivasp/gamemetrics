"""
GameMetrics S.A. - Carga acumulativa de fact_videogames a Apache Pinot.
Cada semana se carga de forma independiente y acumulativa.
Los datos de cada semana se varían con una semilla fija para simular
datos reales diferentes cada semana.
"""
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://localhost:9000")
PARQUET_PATH     = "data/stage/videogames.parquet"
TABLE_NAME       = "fact_videogames"
BATCH_SIZE       = 100_000
SEMANA_TARGET    = int(os.getenv("SEMANA_TARGET", "1"))
FORCE_RESET      = os.getenv("FORCE_RESET", "0") == "1"
STATE_FILE       = os.path.join("data", "stage", "semanas_cargadas.json")

COLUMNAS = [
    "id", "slug", "name", "released", "updated", "tba",
    "esrb_rating", "platforms", "developers", "genres", "publishers",
    "metacritic", "rating", "achievements", "ratings_count",
    "suggestions_count", "released_ts", "semana"
]


# ── Estado persistente de semanas cargadas ────────────────────────────────────

def get_semanas_cargadas() -> set:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def save_semanas_cargadas(semanas: set):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(semanas), f)


# ── Pinot: tabla ──────────────────────────────────────────────────────────────

def tabla_existe() -> bool:
    try:
        r = requests.get(f"{PINOT_CONTROLLER}/tables", timeout=10)
        if r.status_code != 200:
            return False
        return TABLE_NAME in r.json().get("tables", [])
    except Exception:
        return False


def reset_table():
    base        = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base, "pinot_schemas", "schema_fact_videogames.json")
    table_path  = os.path.join(base, "pinot_schemas", "table_fact_videogames.json")

    requests.delete(f"{PINOT_CONTROLLER}/tables/{TABLE_NAME}?type=offline", timeout=15)
    time.sleep(2)
    requests.delete(f"{PINOT_CONTROLLER}/schemas/{TABLE_NAME}", timeout=15)
    time.sleep(2)
    print("[Pinot] Tabla y schema eliminados")

    with open(schema_path) as f:
        r = requests.post(f"{PINOT_CONTROLLER}/schemas", json=json.load(f), timeout=15)
        print(f"[Pinot] Schema: {r.status_code}")
    time.sleep(2)
    with open(table_path) as f:
        r = requests.post(f"{PINOT_CONTROLLER}/tables", json=json.load(f), timeout=15)
        print(f"[Pinot] Tabla: {r.status_code} {r.text[:200]}")
    # Esperar a que Pinot registre la tabla antes de ingestar
    for i in range(10):
        time.sleep(3)
        if tabla_existe():
            print("[Pinot] Tabla verificada y lista")
            return
    raise RuntimeError("Timeout: la tabla no se registró en Pinot tras 30 segundos")


# ── Preparación del DataFrame ─────────────────────────────────────────────────

def prepare_dataframe() -> pd.DataFrame:
    print(f"Leyendo Parquet: {PARQUET_PATH}")
    df = pd.read_parquet(PARQUET_PATH).fillna("")

    print("Convirtiendo fechas...")
    default_sec = int(pd.Timestamp("2000-01-01").timestamp())
    min_sec     = int(pd.Timestamp("1971-01-02").timestamp())
    max_sec     = int(pd.Timestamp("2070-12-31").timestamp())

    ts_raw = pd.to_datetime(
        df["released"].astype(str).str.strip().replace({"nan": None, "": None}),
        errors="coerce",
        dayfirst=True,
    )
    ts_sec = (ts_raw.astype("int64") // 10**9).where(ts_raw.notna(), default_sec)
    ts_sec = ts_sec.where((ts_sec >= min_sec) & (ts_sec <= max_sec), default_sec)
    df["released_ts"] = ts_sec.astype(int)

    for col in ["metacritic", "rating"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)

    for col in ["achievements", "ratings_count", "suggestions_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    str_cols = ["id", "slug", "name", "released", "updated",
                "esrb_rating", "platforms", "developers", "genres", "publishers"]
    for col in str_cols:
        df[col] = (
            df[col].astype(str)
            .str.normalize("NFKD")
            .str.encode("ascii", errors="ignore")
            .str.decode("ascii")
            .str.strip()
        )

    df["tba"] = df["tba"].astype(str).str.upper().map(
        {"TRUE": True, "FALSE": False}
    ).fillna(False)

    print(f"  {len(df)} registros base listos")
    return df


# ── Variación por semana ──────────────────────────────────────────────────────

def apply_variation(df: pd.DataFrame, semana: int) -> pd.DataFrame:
    """
    Aplica variación reproducible al dataset según la semana.
    Semana 1 = datos originales sin cambios.
    Semanas 2-17 = variación en rating y metacritic con semilla fija,
    simulando que los datos cambian semana a semana.
    """
    if semana == 1:
        return df

    rng = np.random.default_rng(seed=semana * 137)
    df  = df.copy()

    # Rating varía ±0.5 (escala 0-5)
    df["rating"] = (
        df["rating"] + rng.uniform(-0.5, 0.5, len(df))
    ).clip(0, 5).round(2)

    # Metacritic varía ±10 (escala 0-100)
    df["metacritic"] = (
        df["metacritic"] + rng.integers(-10, 11, len(df))
    ).clip(0, 100)

    return df


# ── Ingesta ───────────────────────────────────────────────────────────────────

def ingest_dataframe(df: pd.DataFrame, semana: int) -> int:
    total        = len(df)
    batches      = max(1, (total + BATCH_SIZE - 1) // BATCH_SIZE)
    batch_config = json.dumps({"inputFormat": "json"})
    exitosos     = 0

    for i in range(batches):
        start = i * BATCH_SIZE
        end   = min(start + BATCH_SIZE, total)
        if start >= total:
            break

        chunk      = df.iloc[start:end]
        json_bytes = chunk.to_json(orient="records", lines=True).encode("utf-8")

        try:
            resp = requests.post(
                f"{PINOT_CONTROLLER}/ingestFromFile",
                params={
                    "tableNameWithType": f"{TABLE_NAME}_OFFLINE",
                    "batchConfigMapStr": batch_config,
                },
                files={"file": ("batch.json", io.BytesIO(json_bytes), "application/json")},
                timeout=300,
            )
            if resp.status_code == 200:
                exitosos += 1
                print(f"    ✅ Sem{semana} lote{i+1}/{batches} ({end-start:,} filas): OK")
            else:
                print(f"    ❌ Sem{semana} lote{i+1}/{batches}: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"    ❌ Sem{semana} lote{i+1}/{batches}: {e}")

    return exitosos


def ingest_semana(df_base: pd.DataFrame, semana: int) -> bool:
    print(f"\n=== Cargando Semana {semana} ({len(df_base):,} registros) ===")
    df        = apply_variation(df_base.copy(), semana)
    df["semana"] = semana
    df        = df[COLUMNAS]
    lotes_ok  = ingest_dataframe(df, semana)
    print(f"  ✅ Semana {semana} completada ({lotes_ok} lotes OK)")
    return lotes_ok > 0


# ── Punto de entrada ──────────────────────────────────────────────────────────

def ingest():
    semanas_cargadas = get_semanas_cargadas()
    pinot_tiene_tabla = tabla_existe()

    print("=" * 60)
    print(f"  GameMetrics S.A. - Carga Semana {SEMANA_TARGET}")
    print(f"  Semanas en estado: {sorted(semanas_cargadas) or 'ninguna'}")
    print(f"  Tabla en Pinot: {'SÍ' if pinot_tiene_tabla else 'NO'}")
    print(f"  Modo: {'FORZAR REEMPLAZO' if FORCE_RESET else 'ACUMULATIVO'}")
    print("=" * 60)

    df_base = prepare_dataframe()

    if not pinot_tiene_tabla or not semanas_cargadas:
        # Tabla no existe en Pinot (primer arranque o Pinot fue reiniciado)
        # o es la primera carga. Hay que crear la tabla y recargar semanas previas.
        if not semanas_cargadas:
            print("\n[INFO] Primera carga — creando tabla en Pinot...")
        else:
            print(f"\n[WARN] Tabla ausente en Pinot pero estado dice {sorted(semanas_cargadas)}.")
            print("[INFO] Recreando tabla y recargando semanas previas...")
        reset_table()
        for s in sorted(semanas_cargadas):
            if s != SEMANA_TARGET:
                ingest_semana(df_base, s)

    elif FORCE_RESET and SEMANA_TARGET in semanas_cargadas:
        # Reemplazar semana existente: Pinot no soporta DELETE por fila,
        # así que se resetea la tabla y se recargan todas las semanas.
        print(f"\n[FORCE] Reemplazando semana {SEMANA_TARGET} — recargando todas las semanas...")
        reset_table()
        for s in sorted(semanas_cargadas):
            if s != SEMANA_TARGET:
                ingest_semana(df_base, s)
        # La semana target se carga al final (fuera del if)

    # Cargar la semana objetivo
    ok = ingest_semana(df_base, SEMANA_TARGET)

    if ok:
        semanas_cargadas.add(SEMANA_TARGET)
        save_semanas_cargadas(semanas_cargadas)
        print("\n" + "=" * 60)
        print(f"  CARGA COMPLETA — Semanas en Pinot: {sorted(semanas_cargadas)}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print(f"  ERROR — No se pudo ingestar semana {SEMANA_TARGET}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    ingest()

"""
GameMetrics S.A. - Creacion de tablas de dimensiones en Apache Pinot.
Lee el Parquet de videojuegos, extrae valores unicos de cada dimension
y los carga en tablas separadas: dim_plataformas, dim_generos,
dim_desarrolladores, dim_publicadores, dim_esrb.
"""
import os
import json
import unicodedata
import pandas as pd
import requests

PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://localhost:9000")
PARQUET_PATH = "data/stage/videogames.parquet"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ESRB_CATALOG = {
    "Everyone":       {"codigo": "E",    "edad_minima": 3},
    "Everyone 10+":   {"codigo": "E10+", "edad_minima": 10},
    "Teen":           {"codigo": "T",    "edad_minima": 13},
    "Mature":         {"codigo": "M",    "edad_minima": 17},
    "Adults Only":    {"codigo": "AO",   "edad_minima": 18},
    "Rating Pending": {"codigo": "RP",   "edad_minima": 0},
}


def normalize(s):
    n = unicodedata.normalize("NFKD", str(s))
    return n.encode("ascii", errors="ignore").decode("ascii").strip()


def split_col(series):
    """Extrae valores unicos de una columna con valores separados por || o coma."""
    values = set()
    for val in series:
        raw = str(val)
        # Los datos en Pinot usan || como separador
        items = raw.split("||") if "||" in raw else raw.split(",")
        for item in items:
            clean = item.strip()
            if clean and clean.lower() not in ("", "nan", "none"):
                values.add(clean)
    return sorted(values)


def stable_id(name):
    """ID numerico estable basado en hash del nombre (0-999999)."""
    import hashlib
    return int(hashlib.md5(name.encode("utf-8")).hexdigest()[:8], 16) % 1_000_000


def reset_table(table_name):
    schema_path = os.path.join(BASE_DIR, "pinot_schemas", f"schema_{table_name}.json")
    table_path  = os.path.join(BASE_DIR, "pinot_schemas", f"table_{table_name}.json")

    requests.delete(f"{PINOT_CONTROLLER}/tables/{table_name}?type=offline")
    requests.delete(f"{PINOT_CONTROLLER}/schemas/{table_name}")

    with open(schema_path) as f:
        r = requests.post(f"{PINOT_CONTROLLER}/schemas", json=json.load(f))
    print(f"  Schema {table_name}: {r.status_code}")

    with open(table_path) as f:
        r = requests.post(f"{PINOT_CONTROLLER}/tables", json=json.load(f))
    print(f"  Table  {table_name}: {r.status_code}")


def ingest_records(table_name, records):
    """Carga lista de dicts en una tabla OFFLINE de Pinot."""
    json_lines = "\n".join(json.dumps(r, default=str) for r in records)
    resp = requests.post(
        f"{PINOT_CONTROLLER}/ingestFromFile",
        params={
            "tableNameWithType": f"{table_name}_OFFLINE",
            "batchConfigMapStr": json.dumps({"inputFormat": "json"}),
        },
        files={"file": ("data.json", json_lines.encode("utf-8"), "application/json")},
        timeout=120,
    )
    print(f"  Ingesta {table_name}: {resp.status_code} ({len(records)} registros)")
    if resp.status_code != 200:
        print(f"    Detalle: {resp.text[:300]}")


def build_simple_dim(values):
    return [{"dim_id": stable_id(v), "nombre": v} for v in values]


def main():
    print("=" * 55)
    print("  GameMetrics S.A. - Creacion de tablas de dimensiones")
    print("=" * 55)

    print(f"\nLeyendo Parquet: {PARQUET_PATH}")
    df = pd.read_parquet(PARQUET_PATH)
    df = df.fillna("")
    print(f"  {len(df)} registros cargados")

    # dim_plataformas
    print("\n--- dim_plataformas ---")
    plataformas = split_col(df["platforms"])
    reset_table("dim_plataformas")
    ingest_records("dim_plataformas", build_simple_dim(plataformas))

    # dim_generos
    print("\n--- dim_generos ---")
    generos = split_col(df["genres"])
    reset_table("dim_generos")
    ingest_records("dim_generos", build_simple_dim(generos))

    # dim_desarrolladores
    print("\n--- dim_desarrolladores ---")
    desarrolladores = split_col(df["developers"])
    reset_table("dim_desarrolladores")
    ingest_records("dim_desarrolladores", build_simple_dim(desarrolladores))

    # dim_publicadores
    print("\n--- dim_publicadores ---")
    publicadores = split_col(df["publishers"])
    reset_table("dim_publicadores")
    ingest_records("dim_publicadores", build_simple_dim(publicadores))

    # dim_esrb
    print("\n--- dim_esrb ---")
    esrb_vals = split_col(df["esrb_rating"])
    esrb_records = []
    for nombre in esrb_vals:
        info = ESRB_CATALOG.get(nombre, {"codigo": normalize(nombre)[:10], "edad_minima": 0})
        esrb_records.append({
            "dim_id":      stable_id(nombre),
            "codigo":      info["codigo"],
            "nombre":      nombre,
            "edad_minima": info["edad_minima"],
        })
    reset_table("dim_esrb")
    ingest_records("dim_esrb", esrb_records)

    print("\n=================================================")
    print("  Dimensiones creadas:")
    print(f"    dim_plataformas   -> {len(plataformas)} registros")
    print(f"    dim_generos       -> {len(generos)} registros")
    print(f"    dim_desarrolladores -> {len(desarrolladores)} registros")
    print(f"    dim_publicadores  -> {len(publicadores)} registros")
    print(f"    dim_esrb          -> {len(esrb_records)} registros")
    print("=================================================")


if __name__ == "__main__":
    main()

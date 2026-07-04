"""
GameMetrics S.A. - Catálogo comercial OFFLINE (Fase 1).
Crea fact_game_products, fact_price_catalog, fact_bundles, fact_bundle_items.
"""
import hashlib
import json
import os
import sys
import time

import pandas as pd
import requests

PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://pinot-controller:9000")
PARQUET_PATH = "data/stage/videogames.parquet"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEMANA = int(os.getenv("SEMANA_TARGET", "1"))
REGIONS = [("US", "USD"), ("EU", "EUR"), ("LATAM", "USD")]
BATCH_SIZE = 50_000

CATALOG_TABLES = [
    "fact_game_products",
    "fact_price_catalog",
    "fact_bundles",
    "fact_bundle_items",
]


def calc_price(rating: float, metacritic: float) -> float:
    if rating == 0.0 and metacritic == 0.0:
        return 0.0
    price = round((rating * 8) + (metacritic * 0.4), 2)
    return round(max(1.99, price), 2)


def stable_id(name: str) -> str:
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:12]


def wait_for_pinot():
    for _ in range(20):
        try:
            if requests.get(f"{PINOT_CONTROLLER}/health", timeout=5).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    print("ERROR: Pinot controller no disponible")
    sys.exit(1)


def reset_table(table_name: str):
    schema_path = os.path.join(BASE_DIR, "pinot_schemas", f"schema_{table_name}.json")
    table_path = os.path.join(BASE_DIR, "pinot_schemas", f"table_{table_name}.json")

    requests.delete(f"{PINOT_CONTROLLER}/tables/{table_name}?type=offline", timeout=30)
    time.sleep(1)
    requests.delete(f"{PINOT_CONTROLLER}/schemas/{table_name}", timeout=30)
    time.sleep(1)

    with open(schema_path, encoding="utf-8") as f:
        r = requests.post(f"{PINOT_CONTROLLER}/schemas", json=json.load(f), timeout=30)
    if r.status_code not in (200, 201):
        print(f"ERROR schema {table_name}: {r.status_code} {r.text[:300]}")
        sys.exit(1)
    print(f"  Schema {table_name}: {r.status_code}")

    with open(table_path, encoding="utf-8") as f:
        r = requests.post(f"{PINOT_CONTROLLER}/tables", json=json.load(f), timeout=30)
    if r.status_code not in (200, 201):
        print(f"ERROR table {table_name}: {r.status_code} {r.text[:300]}")
        sys.exit(1)
    print(f"  Table  {table_name}: {r.status_code}")


def ingest_records(table_name: str, records: list):
    if not records:
        print(f"  Ingesta {table_name}: sin registros")
        return
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        json_lines = "\n".join(json.dumps(r, default=str) for r in batch)
        resp = requests.post(
            f"{PINOT_CONTROLLER}/ingestFromFile",
            params={
                "tableNameWithType": f"{table_name}_OFFLINE",
                "batchConfigMapStr": json.dumps({"inputFormat": "json"}),
            },
            files={"file": ("data.json", json_lines.encode("utf-8"), "application/json")},
            timeout=300,
        )
        if resp.status_code not in (200, 201):
            print(f"ERROR ingesta {table_name}: {resp.status_code} {resp.text[:300]}")
            sys.exit(1)
        print(f"  Ingesta {table_name}: {resp.status_code} ({len(batch)} registros)")


def main():
    print("=" * 55)
    print("  Fase 1 - Catálogo comercial OFFLINE")
    print("=" * 55)

    wait_for_pinot()

    path = os.path.join(BASE_DIR, PARQUET_PATH)
    if not os.path.exists(path):
        print(f"ERROR: No existe {path}")
        sys.exit(1)

    df = pd.read_parquet(path)
    if "semana" in df.columns:
        df = df[df["semana"] <= SEMANA]

    products = []
    prices = []
    for _, row in df.iterrows():
        product_id = str(row.get("id", "")).strip()
        if not product_id:
            continue
        slug = str(row.get("slug", "")).strip()
        name = str(row.get("name", "")).strip()
        platforms = str(row.get("platforms", "")).strip()
        released = str(row.get("released", "")).strip()
        rating = float(row.get("rating", 0) or 0)
        metacritic = float(row.get("metacritic", 0) or 0)

        products.append({
            "product_id": product_id,
            "parent_game_id": product_id,
            "slug": slug,
            "name": name,
            "product_type": "base",
            "platform_targets": platforms,
            "released": released,
            "semana": SEMANA,
        })

        base = calc_price(rating, metacritic)
        for region, currency in REGIONS:
            mult = 1.0 if region == "US" else (0.92 if region == "EU" else 0.85)
            prices.append({
                "price_id": f"{product_id}_{region}",
                "product_id": product_id,
                "region_code": region,
                "currency": currency,
                "base_price": round(base * mult, 2),
                "semana": SEMANA,
            })

    top = df.sort_values("rating", ascending=False).head(6)
    bundle_id = stable_id("indie-essentials")
    bundles = [{
        "bundle_id": bundle_id,
        "slug": "indie-essentials",
        "name": "Indie Essentials Bundle",
        "description": "Pack curado estilo Steam — 6 títulos indie top.",
        "discount_pct": 25.0,
        "active": True,
        "semana": SEMANA,
    }]
    bundle_items = []
    for _, row in top.iterrows():
        pid = str(row.get("id", "")).strip()
        if not pid:
            continue
        bundle_items.append({
            "bundle_item_id": f"{bundle_id}_{pid}",
            "bundle_id": bundle_id,
            "product_id": pid,
            "semana": SEMANA,
        })

    for table in CATALOG_TABLES:
        print(f"\n--- {table} ---")
        reset_table(table)

    ingest_records("fact_game_products", products)
    ingest_records("fact_price_catalog", prices)
    ingest_records("fact_bundles", bundles)
    ingest_records("fact_bundle_items", bundle_items)

    print("\n" + "=" * 55)
    print(f"  Catálogo cargado: {len(products)} productos, {len(prices)} precios")
    print("=" * 55)


if __name__ == "__main__":
    main()

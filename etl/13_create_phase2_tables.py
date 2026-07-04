"""Crea solo las tablas REALTIME de Fase 2 (sin tocar Fase 1)."""
import json
import os
import sys
import time

import requests

PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://pinot-controller:9000")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PHASE2_TABLES = [
    "fact_user_wallets",
    "fact_wallet_transactions",
    "fact_gifts",
    "fact_coupons",
    "fact_coupon_redemptions",
    "fact_wishlist_price_alerts",
    "fact_review_votes",
    "fact_user_events",
]


def load_json(filename: str) -> dict:
    path = os.path.join(BASE_DIR, "pinot_schemas", filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def delete_table(name: str):
    r = requests.delete(f"{PINOT_CONTROLLER}/tables/{name}?type=realtime", timeout=30)
    print(f"  DELETE table {name}: {r.status_code}")


def delete_schema(name: str):
    r = requests.delete(f"{PINOT_CONTROLLER}/schemas/{name}", timeout=30)
    print(f"  DELETE schema {name}: {r.status_code}")


def create_schema(schema: dict) -> bool:
    r = requests.post(
        f"{PINOT_CONTROLLER}/schemas",
        json=schema,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"  POST schema {schema['schemaName']}: {r.status_code}")
    if r.status_code not in (200, 201):
        print(f"    {r.text[:200]}")
        return False
    return True


def create_table(table: dict) -> bool:
    r = requests.post(
        f"{PINOT_CONTROLLER}/tables",
        json=table,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"  POST table {table['tableName']}: {r.status_code}")
    if r.status_code not in (200, 201):
        print(f"    {r.text[:300]}")
        return False
    return True


def setup_table(name: str) -> bool:
    print(f"\n--- {name} ---")
    delete_table(name)
    time.sleep(1)
    delete_schema(name)
    time.sleep(1)
    if not create_schema(load_json(f"schema_{name}.json")):
        return False
    time.sleep(1)
    return create_table(load_json(f"table_{name}.json"))


if __name__ == "__main__":
    print("=" * 55)
    print("  GameMetrics — Tablas REALTIME Fase 2")
    print("=" * 55)

    for attempt in range(20):
        try:
            r = requests.get(f"{PINOT_CONTROLLER}/health", timeout=5)
            if r.status_code == 200:
                print("Pinot Controller listo.")
                break
        except Exception:
            pass
        print(f"  Esperando Pinot... {attempt + 1}/20")
        time.sleep(5)
    else:
        print("ERROR: Pinot no disponible")
        sys.exit(1)

    failed = [n for n in PHASE2_TABLES if not setup_table(n)]
    if failed:
        print(f"\nERROR: fallidas: {failed}")
        sys.exit(1)

    print(f"\nOK: {len(PHASE2_TABLES)} tablas Fase 2 creadas")

"""
GameMetrics S.A. - Crear tablas REALTIME en Apache Pinot (Fase 1 + Fase 2).
"""
import json
import os
import sys
import time

import requests

PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://pinot-controller:9000")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REALTIME_TABLES = [
    "fact_users",
    "fact_wishlist",
    "emp_records",
    # Fase 1
    "fact_cart",
    "fact_orders",
    "fact_order_items",
    "fact_payments",
    "fact_purchases",
    "fact_refunds",
    "fact_reviews",
    "fact_promotions",
    "fact_user_sessions",
    # Fase 2 — Tienda pro
    "fact_user_wallets",
    "fact_wallet_transactions",
    "fact_gifts",
    "fact_coupons",
    "fact_coupon_redemptions",
    "fact_wishlist_price_alerts",
    "fact_review_votes",
    "fact_user_events",
    # Fase 3 — Distribución
    "fact_builds",
    "fact_download_tokens",
    "fact_install_states",
    "fact_play_sessions",
    "fact_achievements",
    "fact_user_achievements",
    # Fase 4 — Ecosistema
    "fact_friendships",
    "fact_user_activity",
    "fact_notifications",
    "fact_partner_accounts",
    "fact_partner_games",
    "fact_revenue_snapshots",
    "fact_support_tickets",
    "fact_user_sanctions",
    # Fase 5 — Steam completo
    "fact_forum_threads",
    "fact_forum_posts",
    "fact_family_groups",
    "fact_family_shares",
    "fact_api_keys",
    "fact_search_queries",
]


def load_json(filename: str) -> dict:
    path = os.path.join(BASE_DIR, "pinot_schemas", filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def delete_table(name: str, table_type: str = "realtime"):
    r = requests.delete(f"{PINOT_CONTROLLER}/tables/{name}?type={table_type}", timeout=30)
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
    schema = load_json(f"schema_{name}.json")
    if not create_schema(schema):
        return False
    time.sleep(1)
    table = load_json(f"table_{name}.json")
    return create_table(table)


if __name__ == "__main__":
    print("=" * 55)
    print("  GameMetrics S.A. - Crear tablas REALTIME en Pinot")
    print("=" * 55)

    for attempt in range(20):
        try:
            r = requests.get(f"{PINOT_CONTROLLER}/health", timeout=5)
            if r.status_code == 200:
                print("Pinot Controller listo.")
                break
        except Exception:
            pass
        print(f"  Esperando Pinot Controller... intento {attempt + 1}/20")
        time.sleep(5)
    else:
        print("ERROR: Pinot controller no disponible")
        sys.exit(1)

    failed = []
    for name in REALTIME_TABLES:
        if not setup_table(name):
            failed.append(name)

    if failed:
        print(f"\nERROR: tablas fallidas: {failed}")
        sys.exit(1)

    print("\n" + "=" * 55)
    print(f"  Tablas REALTIME creadas: {len(REALTIME_TABLES)}")
    print("=" * 55)

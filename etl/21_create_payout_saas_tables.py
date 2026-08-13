"""Crea tablas REALTIME Fase 3–4: payouts, SaaS, branding, featured."""
import json
import os
import sys
import time

import requests

PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://pinot-controller:9000")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TABLES = [
    "fact_partner_payouts",
    "fact_partner_payout_accounts",
    "fact_saas_subscriptions",
    "fact_partner_branding",
    "fact_featured_placements",
]


def load_json(filename: str) -> dict:
    with open(os.path.join(BASE_DIR, "pinot_schemas", filename), encoding="utf-8") as f:
        return json.load(f)


def setup_table(name: str) -> bool:
    print(f"\n--- {name} ---")
    requests.delete(f"{PINOT_CONTROLLER}/tables/{name}?type=realtime", timeout=30)
    time.sleep(1)
    requests.delete(f"{PINOT_CONTROLLER}/schemas/{name}", timeout=30)
    time.sleep(1)
    r1 = requests.post(
        f"{PINOT_CONTROLLER}/schemas",
        json=load_json(f"schema_{name}.json"),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"  schema: {r1.status_code}")
    if r1.status_code not in (200, 201):
        print(r1.text[:200])
        return False
    time.sleep(1)
    r2 = requests.post(
        f"{PINOT_CONTROLLER}/tables",
        json=load_json(f"table_{name}.json"),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"  table: {r2.status_code}")
    if r2.status_code not in (200, 201):
        print(r2.text[:300])
        return False
    return True


if __name__ == "__main__":
    print("=" * 55)
    print("  GameMetrics — payouts + SaaS (Fase 3–4)")
    print("=" * 55)
    for _ in range(20):
        try:
            if requests.get(f"{PINOT_CONTROLLER}/health", timeout=5).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(5)
    else:
        print("ERROR: Pinot no disponible")
        sys.exit(1)

    ok = True
    for t in TABLES:
        if not setup_table(t):
            ok = False
    if not ok:
        sys.exit(1)
    print("\nOK: tablas Fase 3–4 listas")

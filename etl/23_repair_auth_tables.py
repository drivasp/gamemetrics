"""Repara tablas Pinot críticas para login/registro (segmentos OFFLINE)."""
from __future__ import annotations

import json
import os
import sys
import time

import requests

PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://pinot-controller:9000")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Solo auth — no toca partners/ledger del negocio
TABLES = [
    "fact_users",
    "fact_user_roles",
    "fact_user_locale",
    "fact_user_sessions",
]


def load_json(filename: str) -> dict:
    with open(os.path.join(BASE_DIR, "pinot_schemas", filename), encoding="utf-8") as f:
        return json.load(f)


def wait_pinot() -> None:
    for _ in range(30):
        try:
            if requests.get(f"{PINOT_CONTROLLER}/health", timeout=5).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("Pinot no disponible")


def recreate(name: str) -> bool:
    print(f"\n--- {name} ---")
    requests.delete(f"{PINOT_CONTROLLER}/tables/{name}?type=realtime", timeout=60)
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
        print(r1.text[:300])
        return False
    time.sleep(1)
    r2 = requests.post(
        f"{PINOT_CONTROLLER}/tables",
        json=load_json(f"table_{name}.json"),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"  table:  {r2.status_code}")
    if r2.status_code not in (200, 201):
        print(r2.text[:300])
        return False
    return True


if __name__ == "__main__":
    print("=" * 55)
    print("  GameMetrics — repair auth tables (login/register)")
    print("=" * 55)
    wait_pinot()
    ok = True
    for t in TABLES:
        if not recreate(t):
            ok = False
    if not ok:
        sys.exit(1)
    print("\nOK: fact_users y tablas de auth recreadas")
    print("Espera ~10s a que Pinot consuma Kafka, luego prueba login.")

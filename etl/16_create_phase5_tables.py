"""Crea tablas REALTIME de Fase 5 (Steam completo — 50 tablas)."""
import json
import os
import sys
import time

import requests

PINOT = os.getenv("PINOT_CONTROLLER", "http://pinot-controller:9000")
BASE = os.path.dirname(os.path.abspath(__file__))

TABLES = [
    "fact_forum_threads",
    "fact_forum_posts",
    "fact_family_groups",
    "fact_family_shares",
    "fact_api_keys",
    "fact_search_queries",
]


def load(name: str) -> dict:
    with open(os.path.join(BASE, "pinot_schemas", name), encoding="utf-8") as f:
        return json.load(f)


def setup(name: str) -> bool:
    print(f"\n--- {name} ---")
    requests.delete(f"{PINOT}/tables/{name}?type=realtime", timeout=30)
    time.sleep(0.8)
    requests.delete(f"{PINOT}/schemas/{name}", timeout=30)
    time.sleep(0.8)
    r1 = requests.post(f"{PINOT}/schemas", json=load(f"schema_{name}.json"),
                       headers={"Content-Type": "application/json"}, timeout=30)
    print("  schema", r1.status_code)
    if r1.status_code not in (200, 201):
        print(r1.text[:200])
        return False
    time.sleep(0.8)
    r2 = requests.post(f"{PINOT}/tables", json=load(f"table_{name}.json"),
                       headers={"Content-Type": "application/json"}, timeout=30)
    print("  table", r2.status_code)
    if r2.status_code not in (200, 201):
        print(r2.text[:300])
        return False
    return True


if __name__ == "__main__":
    for _ in range(20):
        try:
            if requests.get(f"{PINOT}/health", timeout=5).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(5)
    else:
        sys.exit(1)
    failed = [t for t in TABLES if not setup(t)]
    if failed:
        print("ERROR", failed)
        sys.exit(1)
    print(f"\nOK: {len(TABLES)} tablas Fase 5 — plataforma 50 tablas completa")

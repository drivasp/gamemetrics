"""
E2E financiero (API) — smoke de rutas nuevas.
Requiere backend en localhost:8080.
Skip automático si no hay API.
"""
from __future__ import annotations

import os
import sys

import urllib.request
import urllib.error
import json

BASE = os.getenv("GM_API", "http://localhost:8080")


def get(path: str):
    req = urllib.request.Request(BASE + path, method="GET")
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read().decode() or "{}")


def main():
    try:
        status, data = get("/openapi.json")
    except Exception as e:
        print(f"SKIP: backend no disponible ({e})")
        return 0

    paths = data.get("paths") or {}
    required = [
        "/marketplace/fees",
        "/tax/rules",
        "/admin/finance/policy",
        "/admin/chargebacks",
    ]
    missing = [p for p in required if p not in paths]
    if missing:
        print("FAIL missing paths:", missing)
        return 1
    print("PASS openapi contains marketplace/tax/finance routes")
    print(f"OK openapi paths checked ({len(required)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

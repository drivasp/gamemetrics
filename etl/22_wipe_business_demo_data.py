"""
Limpia datos B2B del modelo de negocio para demo desde cero.
Borra topics Kafka + recrea tablas Pinot REALTIME (vacías).

Tablas:
  fact_partner_accounts, fact_partner_games, fact_partner_ledger,
  fact_partner_payouts, fact_partner_payout_accounts,
  fact_saas_subscriptions, fact_partner_branding, fact_featured_placements
"""
from __future__ import annotations

import json
import os
import sys
import time

import requests
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError

PINOT_CONTROLLER = os.getenv("PINOT_CONTROLLER", "http://pinot-controller:9000")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TABLES = [
    "fact_partner_accounts",
    "fact_partner_games",
    "fact_partner_ledger",
    "fact_partner_payouts",
    "fact_partner_payout_accounts",
    "fact_saas_subscriptions",
    "fact_partner_branding",
    "fact_featured_placements",
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


def drop_pinot_table(name: str) -> None:
    print(f"  drop Pinot {name}")
    requests.delete(f"{PINOT_CONTROLLER}/tables/{name}?type=realtime", timeout=30)
    time.sleep(0.5)
    requests.delete(f"{PINOT_CONTROLLER}/schemas/{name}", timeout=30)
    time.sleep(0.5)


def create_pinot_table(name: str) -> bool:
    r1 = requests.post(
        f"{PINOT_CONTROLLER}/schemas",
        json=load_json(f"schema_{name}.json"),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"  schema {name}: {r1.status_code}")
    if r1.status_code not in (200, 201):
        print(r1.text[:200])
        return False
    time.sleep(0.5)
    r2 = requests.post(
        f"{PINOT_CONTROLLER}/tables",
        json=load_json(f"table_{name}.json"),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    print(f"  table  {name}: {r2.status_code}")
    if r2.status_code not in (200, 201):
        print(r2.text[:300])
        return False
    return True


def wipe_kafka_topics(names: list[str]) -> None:
    admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP, client_id="wipe-business-demo")
    try:
        print("  delete Kafka topics…")
        try:
            admin.delete_topics(names, timeout_ms=30000)
        except UnknownTopicOrPartitionError:
            pass
        except Exception as e:
            print(f"  (delete warn: {e})")
        time.sleep(3)
        print("  create Kafka topics vacíos…")
        topics = [NewTopic(name=n, num_partitions=1, replication_factor=1) for n in names]
        try:
            admin.create_topics(topics, validate_only=False)
        except TopicAlreadyExistsError:
            pass
        except Exception as e:
            # algunos brokers lanzan por topic individual
            print(f"  (create info: {e})")
            for n in names:
                try:
                    admin.create_topics([NewTopic(name=n, num_partitions=1, replication_factor=1)])
                except TopicAlreadyExistsError:
                    pass
                except Exception as e2:
                    print(f"  topic {n}: {e2}")
    finally:
        admin.close()


if __name__ == "__main__":
    print("=" * 55)
    print("  GameMetrics — wipe modelo de negocio (demo limpia)")
    print("=" * 55)
    wait_pinot()

    print("\n1) Drop tablas Pinot")
    for t in TABLES:
        drop_pinot_table(t)

    print("\n2) Vaciar topics Kafka")
    wipe_kafka_topics(TABLES)
    time.sleep(2)

    print("\n3) Recrear tablas Pinot vacías")
    ok = True
    for t in TABLES:
        if not create_pinot_table(t):
            ok = False
        time.sleep(0.5)

    if not ok:
        sys.exit(1)
    print("\nOK: publishers, ledger, payouts, SaaS y featured en cero")
    print("IMPORTANTE: reinicia el backend para vaciar caches en memoria:")
    print("  docker compose restart backend")

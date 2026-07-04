"""Seed de cupones demo (Fase 2)."""
import json
import os
import sys
import time
import uuid

from kafka import KafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")

COUPONS = [
    ("STEAM10", "pct", 10.0, 1000),
    ("GAME20", "pct", 20.0, 500),
    ("WELCOME5", "fixed", 5.0, 200),
]


def main() -> int:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    now = int(time.time() * 1000)
    year = 365 * 24 * 60 * 60 * 1000
    for code, dtype, value, max_uses in COUPONS:
        payload = {
            "coupon_code": code,
            "discount_type": dtype,
            "discount_value": value,
            "max_uses": max_uses,
            "uses_count": 0,
            "valid_from": now,
            "valid_until": now + year,
            "deleted": False,
        }
        producer.send("fact_coupons", key=code, value=payload)
        print(f"  cupón {code} ({dtype} {value})")
    producer.flush()
    producer.close()
    print(f"OK: {len(COUPONS)} cupones sembrados")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

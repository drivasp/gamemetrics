"""Productor Kafka compartido por los DAGs — mismo patrón que etl/24_seed_reports_demo.py."""
from __future__ import annotations

import json
import os

from kafka import KafkaProducer

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

_producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8"),
            acks="all",
            retries=3,
        )
    return _producer


def send_and_flush(topic: str, rows_by_key: dict[str, dict]) -> int:
    """Envía cada (key, value) al topic y hace flush. Devuelve cuántos envió."""
    producer = get_producer()
    for key, value in rows_by_key.items():
        producer.send(topic, key=key, value=value)
    producer.flush()
    return len(rows_by_key)

"""
GameMetrics S.A. - Seed promociones REALTIME vía Kafka (Fase 1).
Ejecutar después de crear tablas REALTIME.
"""
import json
import os
import time

from kafka import KafkaProducer

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    print("=" * 55)
    print("  Fase 1 - Seed fact_promotions")
    print("=" * 55)

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )

    now = int(time.time() * 1000)
    end = now + (30 * 24 * 60 * 60 * 1000)

    promos = [
        {
            "promo_id": "steam-style-weekend-sale",
            "name": "Weekend Sale -25%",
            "product_id": "*",
            "discount_pct": 25.0,
            "start_at": now,
            "end_at": end,
            "active": True,
            "deleted": False,
        },
        {
            "promo_id": "new-releases-10",
            "name": "Nuevos lanzamientos -10%",
            "product_id": "*",
            "discount_pct": 10.0,
            "start_at": now,
            "end_at": end,
            "active": True,
            "deleted": False,
        },
    ]

    for p in promos:
        producer.send("fact_promotions", key=p["promo_id"], value=p)
        print(f"  Enviado promo: {p['name']}")

    producer.flush()
    producer.close()
    print("  Listo.")


if __name__ == "__main__":
    main()

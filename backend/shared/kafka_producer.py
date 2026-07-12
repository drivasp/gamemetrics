import json
import os

from aiokafka import AIOKafkaProducer

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

_producer: AIOKafkaProducer | None = None


async def start_producer() -> None:
    global _producer
    try:
        _producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8"),
        )
        await _producer.start()
        print(f"[Kafka] Producer connected to {KAFKA_SERVERS}")
    except Exception as exc:
        print(f"[Kafka] WARNING: No se pudo conectar a Kafka: {exc}")
        _producer = None


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def kafka_send(topic: str, key: str, value: dict) -> None:
    global _producer
    if _producer is None:
        await start_producer()
    if _producer is None:
        raise RuntimeError("Kafka producer no disponible")
    await _producer.send_and_wait(topic, key=key, value=value)

"""Genera table_*.json REALTIME para Fase 1."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS = os.path.join(BASE, "pinot_schemas")

TABLES = [
    ("fact_cart", ["user_id", "deleted"], "added_at"),
    ("fact_orders", ["user_id", "deleted"], "created_at"),
    ("fact_order_items", ["order_id", "deleted"], "created_at"),
    ("fact_payments", ["user_id", "order_id", "deleted"], "created_at"),
    ("fact_purchases", ["user_id", "game_slug", "deleted"], "purchased_at"),
    ("fact_refunds", ["user_id", "purchase_id", "deleted"], "created_at"),
    ("fact_reviews", ["game_slug", "user_id", "deleted"], "created_at"),
    ("fact_promotions", ["product_id", "active", "deleted"], "start_at"),
    ("fact_user_sessions", ["user_id", "deleted"], "created_at"),
]


def build(name: str, inverted: list[str], time_col: str) -> dict:
    return {
        "tableName": name,
        "tableType": "REALTIME",
        "segmentsConfig": {
            "timeColumnName": time_col,
            "timeType": "MILLISECONDS",
            "replication": "1",
            "replicasPerPartition": "1",
        },
        "tableIndexConfig": {
            "loadMode": "MMAP",
            "invertedIndexColumns": inverted,
            "streamConfigs": {
                "streamType": "kafka",
                "stream.kafka.consumer.type": "lowlevel",
                "stream.kafka.topic.name": name,
                "stream.kafka.decoder.class.name": "org.apache.pinot.plugin.stream.kafka.KafkaJSONMessageDecoder",
                "stream.kafka.consumer.factory.class.name": "org.apache.pinot.plugin.stream.kafka20.KafkaConsumerFactory",
                "stream.kafka.broker.list": "kafka:9092",
                "realtime.segment.flush.threshold.rows": "0",
                "realtime.segment.flush.threshold.time": "24h",
                "realtime.segment.flush.desired.size": "50M",
                "stream.kafka.consumer.prop.auto.offset.reset": "smallest",
            },
        },
        "upsertConfig": {"mode": "FULL", "deleteRecordColumn": "deleted"},
        "routing": {"instanceSelectorType": "strictReplicaGroup"},
        "tenants": {},
        "metadata": {},
    }


if __name__ == "__main__":
    for name, inverted, time_col in TABLES:
        path = os.path.join(SCHEMAS, f"table_{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(build(name, inverted, time_col), f, indent=2)
        print(f"Wrote {path}")

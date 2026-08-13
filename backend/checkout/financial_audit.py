"""
Auditoría financiera en memoria (+ Kafka opcional si existe topic).

Registra quién / qué / cuándo / montos / estados para operaciones críticas.
No sustituye un SIEM ni compliance PCI.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

_AUDIT: list[dict[str, Any]] = []
_MAX = 2000


def audit_event(
    *,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    amount: float | None = None,
    currency: str = "USD",
    before: dict | None = None,
    after: dict | None = None,
    meta: dict | None = None,
) -> dict[str, Any]:
    import json

    row = {
        "audit_id": uuid.uuid4().hex[:16],
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "amount": amount,
        "currency": currency,
        "before": before or {},
        "after": after or {},
        "meta": meta or {},
        "created_at": int(time.time() * 1000),
    }
    _AUDIT.insert(0, row)
    del _AUDIT[_MAX:]
    # Persist best-effort to Pinot topic (non-blocking fire)
    try:
        import asyncio
        from shared.kafka_producer import kafka_send

        payload = {
            "audit_id": row["audit_id"],
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "currency": currency,
            "meta_json": json.dumps({"before": before or {}, "after": after or {}, "meta": meta or {}}),
            "amount": float(amount or 0),
            "created_at": row["created_at"],
            "deleted": False,
        }

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(kafka_send("fact_audit_log", row["audit_id"], payload))
        except Exception:
            pass
    except Exception:
        pass
    return row


def list_audit(limit: int = 100, entity_id: str | None = None) -> list[dict[str, Any]]:
    items = _AUDIT
    if entity_id:
        items = [a for a in items if a.get("entity_id") == entity_id]
    return items[:limit]

"""Webhook / event idempotency store (in-memory + optional kafka)."""
from __future__ import annotations

import time
from typing import Any

_SEEN: dict[str, dict[str, Any]] = {}


def already_processed(event_id: str) -> dict[str, Any] | None:
    return _SEEN.get(event_id)


def mark_processed(event_id: str, result: dict[str, Any]) -> dict[str, Any]:
    row = {
        "event_id": event_id,
        "result": result,
        "processed_at": int(time.time() * 1000),
    }
    _SEEN[event_id] = row
    return row


def process_once(event_id: str, handler) -> tuple[dict[str, Any], bool]:
    """
    Returns (result, is_duplicate).
    handler() only runs if event_id unseen.
    """
    existing = already_processed(event_id)
    if existing:
        return existing["result"], True
    result = handler()
    mark_processed(event_id, result)
    return result, False

"""
Webhook / event idempotency — durable via SQLite claims (sobrevive reinicios).

In-memory cache acelera retries del mismo proceso; SoT = financial_operation_claims.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from ledger.sqlite_store import claim_exists, try_claim

logger = logging.getLogger("gamemetrics.webhook_idempotency")

_SEEN: dict[str, dict[str, Any]] = {}


def already_processed(event_id: str) -> dict[str, Any] | None:
    eid = (event_id or "").strip()
    if not eid:
        return None
    if eid in _SEEN:
        return _SEEN[eid]
    if claim_exists(f"webhook_event_{eid}"):
        row = {"event_id": eid, "result": {"duplicate": True}, "processed_at": 0}
        _SEEN[eid] = row
        return row
    return None


def mark_processed(event_id: str, result: dict[str, Any]) -> dict[str, Any]:
    eid = (event_id or "").strip()
    row = {"event_id": eid, "result": result, "processed_at": 0}
    _SEEN[eid] = row
    # Claim best-effort (puede ya existir si try_claim ganó antes)
    try:
        try_claim(f"webhook_event_{eid}", "stripe_webhook", metadata={"result_keys": list(result.keys())})
    except Exception as exc:
        logger.warning("webhook mark_processed claim: %s", exc)
    return row


def process_once(event_id: str, handler: Callable[[], Any]) -> tuple[Any, bool]:
    """
    Returns (result, is_duplicate).
    handler() only runs if claim_key is new (SQLite UNIQUE).
    """
    eid = (event_id or "").strip()
    if not eid:
        raise ValueError("event_id requerido para idempotencia de webhook")

    existing = already_processed(eid)
    if existing and existing.get("result") is not None and existing.get("processed_at"):
        return existing["result"], True

    claimed = try_claim(f"webhook_event_{eid}", "stripe_webhook", metadata={"event_id": eid})
    if not claimed:
        cached = _SEEN.get(eid) or {"result": {"ok": True, "duplicate": True}}
        return cached.get("result") or {"ok": True, "duplicate": True}, True

    result = handler()
    if hasattr(result, "__await__"):
        raise TypeError("process_once sync handler only; use process_once_async for coroutines")
    row = {"event_id": eid, "result": result, "processed_at": 1}
    _SEEN[eid] = row
    return result, False


async def process_once_async(event_id: str, handler) -> tuple[Any, bool]:
    """Async variant for FastAPI webhook handlers."""
    eid = (event_id or "").strip()
    if not eid:
        raise ValueError("event_id requerido")

    existing = already_processed(eid)
    if existing and existing.get("processed_at"):
        return existing.get("result") or {"ok": True, "duplicate": True}, True

    claimed = try_claim(f"webhook_event_{eid}", "stripe_webhook", metadata={"event_id": eid})
    if not claimed:
        return {"ok": True, "duplicate": True}, True

    result = await handler()
    _SEEN[eid] = {"event_id": eid, "result": result, "processed_at": 1}
    return result, False

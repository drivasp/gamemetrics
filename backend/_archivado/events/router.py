"""Eventos de comportamiento / funnel (analytics)."""
from __future__ import annotations

import json
import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from shared.auth_deps import require_token
from shared.kafka_producer import kafka_send

router = APIRouter(prefix="/events", tags=["events"])


class TrackEventDTO(BaseModel):
    event_type: str = Field(min_length=2, max_length=64)
    product_id: str | None = None
    metadata: dict[str, Any] | None = None


class TrackEventResponse(BaseModel):
    event_id: str
    status: str = "ok"


@router.post("", response_model=TrackEventResponse, status_code=201)
async def track_event(
    body: TrackEventDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    event_id = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    meta = json.dumps(body.metadata or {}, ensure_ascii=False)[:2000]
    await kafka_send("fact_user_events", event_id, {
        "event_id": event_id,
        "user_id": user_id,
        "event_type": body.event_type[:64],
        "product_id": body.product_id or "",
        "metadata_json": meta,
        "created_at": now_ms,
        "deleted": False,
    })
    return TrackEventResponse(event_id=event_id)

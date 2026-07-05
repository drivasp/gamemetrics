"""Helpers sociales: notificaciones y actividad."""
from __future__ import annotations

import time
import uuid

from shared.kafka_producer import kafka_send


async def notify(user_id: str, ntype: str, title: str, body: str) -> str:
    nid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_notifications", nid, {
        "notification_id": nid,
        "user_id": user_id,
        "type": ntype,
        "title": title[:120],
        "body": body[:500],
        "read": False,
        "created_at": now_ms,
        "deleted": False,
    })
    return nid


async def post_activity(user_id: str, activity_type: str, summary: str, reference_id: str = "") -> str:
    aid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_user_activity", aid, {
        "activity_id": aid,
        "user_id": user_id,
        "activity_type": activity_type,
        "reference_id": reference_id or "",
        "summary": summary[:300],
        "created_at": now_ms,
        "deleted": False,
    })
    return aid

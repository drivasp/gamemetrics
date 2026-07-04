"""Notificaciones in-app."""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_bool

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT notification_id, user_id, type, title, body, read, created_at "
        f"FROM fact_notifications WHERE user_id = '{esc(user_id)}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT 50"
    )
    items = [
        {
            "notification_id": r[0],
            "type": r[2],
            "title": r[3],
            "body": r[4] or "",
            "read": to_bool(r[5]),
            "created_at": str(r[6]),
        }
        for r in rows
    ]
    unread = sum(1 for i in items if not i["read"])
    return {"items": items, "unread": unread}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT notification_id, user_id, type, title, body, read, created_at "
        f"FROM fact_notifications WHERE notification_id = '{esc(notification_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Notificación no encontrada")
    r = rows[0]
    if r[1] != user_id:
        raise HTTPException(403, "No autorizado")
    await kafka_send("fact_notifications", r[0], {
        "notification_id": r[0],
        "user_id": r[1],
        "type": r[2],
        "title": r[3],
        "body": r[4] or "",
        "read": True,
        "created_at": int(r[6]) if str(r[6]).isdigit() else int(time.time() * 1000),
        "deleted": False,
    })
    return {"status": "read"}


@router.post("/read-all")
async def mark_all_read(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT notification_id, user_id, type, title, body, read, created_at "
        f"FROM fact_notifications WHERE user_id = '{esc(user_id)}' "
        f"AND deleted = false AND read = false LIMIT 50"
    )
    now_ms = int(time.time() * 1000)
    for r in rows:
        await kafka_send("fact_notifications", r[0], {
            "notification_id": r[0],
            "user_id": r[1],
            "type": r[2],
            "title": r[3],
            "body": r[4] or "",
            "read": True,
            "created_at": int(r[6]) if str(r[6]).isdigit() else now_ms,
            "deleted": False,
        })
    return {"marked": len(rows)}

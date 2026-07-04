"""Tickets de soporte."""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from social.servicio import notify

router = APIRouter(prefix="/support", tags=["support"])


class TicketCreateDTO(BaseModel):
    subject: str = Field(min_length=3, max_length=120)
    body: str = Field(min_length=5, max_length=2000)
    priority: str = Field(default="normal")


@router.get("/tickets")
async def list_tickets(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT ticket_id, user_id, subject, body, status, priority, created_at "
        f"FROM fact_support_tickets WHERE user_id = '{esc(user_id)}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT 50"
    )
    return {
        "items": [
            {
                "ticket_id": r[0],
                "subject": r[2],
                "body": r[3],
                "status": r[4],
                "priority": r[5],
                "created_at": str(r[6]),
            }
            for r in rows
        ]
    }


@router.post("/tickets", status_code=201)
async def create_ticket(
    body: TicketCreateDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    tid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    priority = body.priority if body.priority in ("low", "normal", "high") else "normal"
    await kafka_send("fact_support_tickets", tid, {
        "ticket_id": tid,
        "user_id": user_id,
        "subject": body.subject.strip(),
        "body": body.body.strip(),
        "status": "open",
        "priority": priority,
        "created_at": now_ms,
        "deleted": False,
    })
    await notify(
        user_id, "support",
        "Ticket recibido",
        f"Tu solicitud «{body.subject.strip()}» fue registrada. Te responderemos pronto.",
    )
    return {
        "ticket_id": tid,
        "status": "open",
        "message": "Ticket creado correctamente",
    }


@router.post("/tickets/{ticket_id}/close")
async def close_ticket(
    ticket_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT ticket_id, user_id, subject, body, status, priority, created_at "
        f"FROM fact_support_tickets WHERE ticket_id = '{esc(ticket_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Ticket no encontrado")
    r = rows[0]
    if r[1] != user_id:
        raise HTTPException(403, "No autorizado")
    await kafka_send("fact_support_tickets", r[0], {
        "ticket_id": r[0],
        "user_id": r[1],
        "subject": r[2],
        "body": r[3],
        "status": "closed",
        "priority": r[5],
        "created_at": int(r[6]) if str(r[6]).isdigit() else int(time.time() * 1000),
        "deleted": False,
    })
    return {"status": "closed"}

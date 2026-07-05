"""Alertas de precio en wishlist — estilo Steam."""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from carrito.precio_item import resolve_item_price
from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_bool

router = APIRouter(prefix="/alerts", tags=["alerts"])


class CreateAlertDTO(BaseModel):
    product_id: str
    game_slug: str
    game_name: str
    target_price: float = Field(gt=0)


class AlertDTO(BaseModel):
    alert_id: str
    user_id: str
    product_id: str
    game_slug: str
    game_name: str
    target_price: float
    current_price: float | None = None
    triggered: bool
    created_at: str


@router.get("", response_model=list[AlertDTO])
async def list_alerts(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT alert_id, user_id, product_id, game_slug, game_name, "
        f"target_price, triggered, created_at FROM fact_wishlist_price_alerts "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT 50"
    )
    result: list[AlertDTO] = []
    for r in rows:
        current = None
        try:
            final, _, _ = await resolve_item_price(r[2], r[3])
            current = final
            triggered = to_bool(r[6]) or (final <= float(r[5]))
        except Exception:
            triggered = to_bool(r[6])
        result.append(AlertDTO(
            alert_id=r[0],
            user_id=r[1],
            product_id=r[2],
            game_slug=r[3],
            game_name=r[4],
            target_price=float(r[5]),
            current_price=current,
            triggered=triggered,
            created_at=str(r[7]),
        ))
    return result


@router.post("", response_model=AlertDTO, status_code=201)
async def create_alert(
    body: CreateAlertDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    alert_id = f"{user_id}_{body.product_id}"
    existing = await pinot_query(
        f"SELECT alert_id FROM fact_wishlist_price_alerts "
        f"WHERE alert_id = '{esc(alert_id)}' AND deleted = false LIMIT 1"
    )
    if existing:
        raise HTTPException(409, "Ya tienes una alerta para este juego")

    now_ms = int(time.time() * 1000)
    final, _, _ = await resolve_item_price(body.product_id, body.game_slug)
    triggered = final <= body.target_price

    await kafka_send("fact_wishlist_price_alerts", alert_id, {
        "alert_id": alert_id,
        "user_id": user_id,
        "product_id": body.product_id,
        "game_slug": body.game_slug,
        "game_name": body.game_name,
        "target_price": round(body.target_price, 2),
        "triggered": triggered,
        "created_at": now_ms,
        "deleted": False,
    })
    return AlertDTO(
        alert_id=alert_id,
        user_id=user_id,
        product_id=body.product_id,
        game_slug=body.game_slug,
        game_name=body.game_name,
        target_price=round(body.target_price, 2),
        current_price=final,
        triggered=triggered,
        created_at=str(now_ms),
    )


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT alert_id, product_id, game_slug, game_name, target_price, "
        f"triggered, created_at FROM fact_wishlist_price_alerts "
        f"WHERE alert_id = '{esc(alert_id)}' AND user_id = '{esc(user_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Alerta no encontrada")
    r = rows[0]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_wishlist_price_alerts", alert_id, {
        "alert_id": alert_id,
        "user_id": user_id,
        "product_id": r[1],
        "game_slug": r[2],
        "game_name": r[3],
        "target_price": float(r[4]),
        "triggered": to_bool(r[5]),
        "created_at": now_ms,
        "deleted": True,
    })

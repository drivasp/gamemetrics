"""Regalos entre usuarios — estilo Steam Gift."""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_bool
from carrito.precio_item import resolve_item_price
from wallet.servicio import apply_transaction, get_balance

router = APIRouter(prefix="/gifts", tags=["gifts"])


class SendGiftDTO(BaseModel):
    product_id: str
    game_slug: str
    game_name: str
    game_image: str | None = None
    recipient_email: str = Field(min_length=3, max_length=200)
    message: str = Field(default="", max_length=500)
    payment_method: str = Field(default="wallet")  # wallet | sandbox


class GiftDTO(BaseModel):
    gift_id: str
    sender_id: str
    recipient_id: str
    recipient_email: str
    product_id: str
    game_slug: str
    game_name: str
    game_image: str | None
    purchase_id: str
    message: str
    status: str
    amount: float
    created_at: str


def _row_to_gift(r) -> GiftDTO:
    return GiftDTO(
        gift_id=r[0],
        sender_id=r[1],
        recipient_id=r[2] or "",
        recipient_email=r[3] or "",
        product_id=r[4],
        game_slug=r[5],
        game_name=r[6],
        game_image=r[7] or None,
        purchase_id=r[8] or "",
        message=r[9] or "",
        status=r[10],
        amount=float(r[11] or 0),
        created_at=str(r[12]),
    )


GIFT_COLS = (
    "gift_id, sender_id, recipient_id, recipient_email, product_id, game_slug, "
    "game_name, game_image, purchase_id, message, status, amount, created_at"
)


async def _find_user_by_email(email: str) -> str | None:
    rows = await pinot_query(
        f"SELECT user_id FROM fact_users "
        f"WHERE email = '{esc(email.strip().lower())}' AND deleted = false LIMIT 1"
    )
    return rows[0][0] if rows else None


async def _owns(user_id: str, product_id: str) -> bool:
    rows = await pinot_query(
        f"SELECT purchase_id FROM fact_purchases "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false AND refunded = false LIMIT 1"
    )
    return len(rows) > 0


@router.post("", response_model=GiftDTO, status_code=201)
async def send_gift(
    body: SendGiftDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, sender_id = require_token(authorization)
    email = body.recipient_email.strip().lower()
    recipient_id = await _find_user_by_email(email)
    if not recipient_id:
        raise HTTPException(404, "No hay ninguna cuenta con ese correo")
    if recipient_id == sender_id:
        raise HTTPException(400, "No puedes enviarte un regalo a ti mismo")
    if await _owns(recipient_id, body.product_id):
        raise HTTPException(409, "El destinatario ya posee este juego")

    final_price, _, _ = await resolve_item_price(body.product_id, body.game_slug)
    amount = max(0.0, float(final_price))

    method = (body.payment_method or "wallet").lower()
    if method == "wallet":
        bal = await get_balance(sender_id)
        if bal < amount:
            raise HTTPException(
                402,
                f"Saldo insuficiente. Tienes ${bal:.2f} y el regalo cuesta ${amount:.2f}.",
            )
    elif method != "sandbox":
        raise HTTPException(400, "Método de pago no soportado para regalos")

    gift_id = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)

    if method == "wallet" and amount > 0:
        try:
            await apply_transaction(
                sender_id,
                -amount,
                tx_type="purchase",
                reference_id=gift_id,
                idempotency_key=f"gift_pay_{gift_id}",
            )
        except ValueError as exc:
            raise HTTPException(402, str(exc)) from exc

    await kafka_send("fact_gifts", gift_id, {
        "gift_id": gift_id,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "recipient_email": email,
        "product_id": body.product_id,
        "game_slug": body.game_slug,
        "game_name": body.game_name,
        "game_image": body.game_image or "",
        "purchase_id": "",
        "message": body.message or "",
        "status": "pending",
        "amount": amount,
        "created_at": now_ms,
        "deleted": False,
    })

    try:
        from social.servicio import notify, post_activity
        await notify(
            recipient_id, "gift",
            "¡Te han enviado un regalo!",
            f"Recibiste «{body.game_name}». Ábrelo en Regalos para aceptarlo.",
        )
        await post_activity(sender_id, "gift_sent", f"Envió «{body.game_name}» como regalo", gift_id)
    except Exception:
        pass

    return GiftDTO(
        gift_id=gift_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        recipient_email=email,
        product_id=body.product_id,
        game_slug=body.game_slug,
        game_name=body.game_name,
        game_image=body.game_image,
        purchase_id="",
        message=body.message or "",
        status="pending",
        amount=amount,
        created_at=str(now_ms),
    )


@router.get("/inbox", response_model=list[GiftDTO])
async def inbox(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT {GIFT_COLS} FROM fact_gifts "
        f"WHERE recipient_id = '{esc(user_id)}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT 50"
    )
    return [_row_to_gift(r) for r in rows]


@router.get("/sent", response_model=list[GiftDTO])
async def sent(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT {GIFT_COLS} FROM fact_gifts "
        f"WHERE sender_id = '{esc(user_id)}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT 50"
    )
    return [_row_to_gift(r) for r in rows]


@router.post("/{gift_id}/accept", response_model=GiftDTO)
async def accept_gift(
    gift_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT {GIFT_COLS} FROM fact_gifts "
        f"WHERE gift_id = '{esc(gift_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Regalo no encontrado")
    g = _row_to_gift(rows[0])
    if g.recipient_id != user_id:
        raise HTTPException(403, "Este regalo no es para ti")
    if g.status != "pending":
        raise HTTPException(409, f"El regalo ya está en estado '{g.status}'")
    if await _owns(user_id, g.product_id):
        raise HTTPException(409, "Ya posees este juego")

    now_ms = int(time.time() * 1000)
    purchase_id = f"{user_id}_{g.product_id}"
    order_id = f"gift_{gift_id}"

    await kafka_send("fact_purchases", purchase_id, {
        "purchase_id": purchase_id,
        "order_id": order_id,
        "user_id": user_id,
        "product_id": g.product_id,
        "game_slug": g.game_slug,
        "game_name": g.game_name,
        "game_image": g.game_image or "",
        "amount": g.amount,
        "purchased_at": now_ms,
        "refunded": False,
        "deleted": False,
    })

    await kafka_send("fact_gifts", gift_id, {
        "gift_id": gift_id,
        "sender_id": g.sender_id,
        "recipient_id": g.recipient_id,
        "recipient_email": g.recipient_email,
        "product_id": g.product_id,
        "game_slug": g.game_slug,
        "game_name": g.game_name,
        "game_image": g.game_image or "",
        "purchase_id": purchase_id,
        "message": g.message,
        "status": "accepted",
        "amount": g.amount,
        "created_at": int(g.created_at) if str(g.created_at).isdigit() else now_ms,
        "deleted": False,
    })

    g.purchase_id = purchase_id
    g.status = "accepted"
    return g


@router.post("/{gift_id}/decline", response_model=GiftDTO)
async def decline_gift(
    gift_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT {GIFT_COLS} FROM fact_gifts "
        f"WHERE gift_id = '{esc(gift_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Regalo no encontrado")
    g = _row_to_gift(rows[0])
    if g.recipient_id != user_id:
        raise HTTPException(403, "Este regalo no es para ti")
    if g.status != "pending":
        raise HTTPException(409, f"El regalo ya está en estado '{g.status}'")

    now_ms = int(time.time() * 1000)
    # Devolver saldo al remitente
    if g.amount > 0:
        await apply_transaction(
            g.sender_id,
            g.amount,
            tx_type="refund",
            reference_id=gift_id,
            idempotency_key=f"gift_refund_{gift_id}",
        )

    await kafka_send("fact_gifts", gift_id, {
        "gift_id": gift_id,
        "sender_id": g.sender_id,
        "recipient_id": g.recipient_id,
        "recipient_email": g.recipient_email,
        "product_id": g.product_id,
        "game_slug": g.game_slug,
        "game_name": g.game_name,
        "game_image": g.game_image or "",
        "purchase_id": "",
        "message": g.message,
        "status": "declined",
        "amount": g.amount,
        "created_at": int(g.created_at) if str(g.created_at).isdigit() else now_ms,
        "deleted": False,
    })
    g.status = "declined"
    return g

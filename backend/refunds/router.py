import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_bool, to_ms
from wallet.servicio import apply_transaction

router = APIRouter(prefix="/refunds", tags=["refunds"])

REFUND_WINDOW_MS = 14 * 24 * 60 * 60 * 1000


class RefundRequestDTO(BaseModel):
    purchase_id: str
    reason: str = "Solicitud del usuario (política 14 días)"


class RefundResponseDTO(BaseModel):
    refund_id: str
    status: str
    amount: float
    message: str


@router.post("", response_model=RefundResponseDTO)
async def request_refund(
    body: RefundRequestDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT purchase_id, order_id, product_id, game_slug, game_name, "
        f"game_image, amount, purchased_at, refunded FROM fact_purchases "
        f"WHERE purchase_id = '{esc(body.purchase_id)}' AND user_id = '{esc(user_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Compra no encontrada")
    purchase_id, order_id, product_id, slug, name, image, amount, purchased_at, refunded = rows[0]
    if to_bool(refunded):
        raise HTTPException(409, "Esta compra ya fue reembolsada")

    purchased_ms = to_ms(purchased_at)
    now_ms = int(time.time() * 1000)
    if now_ms - purchased_ms > REFUND_WINDOW_MS:
        raise HTTPException(400, "El plazo de reembolso de 14 días ha expirado")

    payment_rows = await pinot_query(
        f"SELECT payment_id FROM fact_payments "
        f"WHERE order_id = '{esc(order_id)}' AND deleted = false LIMIT 1"
    )
    payment_id = payment_rows[0][0] if payment_rows else ""

    refund_id = uuid.uuid4().hex[:15]
    amt = float(amount or 0)

    await kafka_send("fact_refunds", refund_id, {
        "refund_id": refund_id,
        "purchase_id": body.purchase_id,
        "payment_id": payment_id,
        "user_id": user_id,
        "amount": amt,
        "reason": body.reason,
        "status": "approved",
        "created_at": now_ms,
        "deleted": False,
    })

    await kafka_send("fact_purchases", purchase_id, {
        "purchase_id": purchase_id,
        "order_id": order_id,
        "user_id": user_id,
        "product_id": product_id,
        "game_slug": slug,
        "game_name": name,
        "game_image": image or "",
        "amount": float(amount or 0),
        "purchased_at": purchased_ms,
        "refunded": True,
        "deleted": False,
    })

    try:
        await apply_transaction(
            user_id,
            amt,
            tx_type="refund",
            reference_id=refund_id,
            idempotency_key=f"refund_wallet_{refund_id}",
        )
        msg = (
            f"Reembolso procesado. ${amt:.2f} se añadieron a tu cartera GameMetrics. "
            "El juego ya no aparecerá como activo en tu biblioteca."
        )
    except Exception:
        msg = "Reembolso procesado. El juego ya no aparecerá como activo en tu biblioteca."

    return RefundResponseDTO(
        refund_id=refund_id,
        status="approved",
        amount=amt,
        message=msg,
    )

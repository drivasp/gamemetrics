import hashlib
import logging
import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from checkout.partner_ledger import record_refund_ledger
from ledger.sqlite_store import claim_exists, get_by_idempotency, try_claim
from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_bool, to_ms
from wallet.servicio import apply_transaction

router = APIRouter(prefix="/refunds", tags=["refunds"])
logger = logging.getLogger("gamemetrics.refunds")

REFUND_WINDOW_MS = 14 * 24 * 60 * 60 * 1000


class RefundRequestDTO(BaseModel):
    purchase_id: str
    reason: str = "Solicitud del usuario (política 14 días)"


class RefundResponseDTO(BaseModel):
    refund_id: str
    status: str
    amount: float
    message: str


def _stable_refund_id(purchase_id: str) -> str:
    """Determinista por purchase — retry/carrera no genera nuevo id ni doble wallet credit."""
    digest = hashlib.sha256(f"refund:{purchase_id}".encode()).hexdigest()
    return f"rf_{digest[:13]}"


@router.post("", response_model=RefundResponseDTO)
async def request_refund(
    body: RefundRequestDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    purchase_id = (body.purchase_id or "").strip()
    if not purchase_id:
        raise HTTPException(400, "purchase_id requerido")

    # Claim durable ANTES de side effects (anti carrera doble-refund)
    claim_key = f"refund_claim_{purchase_id}"
    wallet_key = f"refund_wallet_{purchase_id}"
    refund_id = _stable_refund_id(purchase_id)

    prior_wallet = get_by_idempotency(wallet_key)
    if prior_wallet or claim_exists(claim_key):
        raise HTTPException(
            409,
            f"Reembolso ya procesado (refund_id={refund_id}). Operación idempotente rechazada.",
        )

    rows = await pinot_query(
        f"SELECT purchase_id, order_id, product_id, game_slug, game_name, "
        f"game_image, amount, purchased_at, refunded FROM fact_purchases "
        f"WHERE purchase_id = '{esc(purchase_id)}' AND user_id = '{esc(user_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Compra no encontrada")
    purchase_id, order_id, product_id, slug, name, image, amount, purchased_at, refunded = rows[0]
    if to_bool(refunded):
        raise HTTPException(409, "Esta compra ya fue reembolsada")

    prior = await pinot_query(
        f"SELECT refund_id, status, amount FROM fact_refunds "
        f"WHERE purchase_id = '{esc(purchase_id)}' AND deleted = false "
        f"AND status = 'approved' LIMIT 1"
    )
    if prior:
        raise HTTPException(
            409,
            f"Reembolso ya procesado (refund_id={prior[0][0]}). Operación idempotente rechazada.",
        )

    purchased_ms = to_ms(purchased_at)
    now_ms = int(time.time() * 1000)
    if now_ms - purchased_ms > REFUND_WINDOW_MS:
        raise HTTPException(400, "El plazo de reembolso de 14 días ha expirado")

    if not try_claim(claim_key, "refund", metadata={"purchase_id": purchase_id, "user_id": user_id}):
        raise HTTPException(
            409,
            f"Reembolso ya procesado (refund_id={refund_id}). Operación idempotente rechazada.",
        )

    payment_rows = await pinot_query(
        f"SELECT payment_id FROM fact_payments "
        f"WHERE order_id = '{esc(order_id)}' AND deleted = false LIMIT 1"
    )
    payment_id = payment_rows[0][0] if payment_rows else ""
    amt = float(amount or 0)

    await kafka_send("fact_refunds", refund_id, {
        "refund_id": refund_id,
        "purchase_id": purchase_id,
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
        await record_refund_ledger(
            purchase_id=purchase_id,
            order_id=str(order_id or ""),
            buyer_user_id=user_id,
            product_id=str(product_id or ""),
            game_name=str(name or ""),
            amount=amt,
            currency="USD",
        )
    except Exception as exc:
        logger.error("ledger refund purchase=%s: %s", purchase_id, exc)

    try:
        await apply_transaction(
            user_id,
            amt,
            tx_type="refund",
            reference_id=purchase_id,
            idempotency_key=wallet_key,
        )
        msg = (
            f"Reembolso procesado. ${amt:.2f} se añadieron a tu cartera GameMetrics. "
            "El juego ya no aparecerá como activo en tu biblioteca."
        )
    except Exception as exc:
        logger.error("wallet refund purchase=%s: %s", purchase_id, exc)
        msg = "Reembolso procesado. El juego ya no aparecerá como activo en tu biblioteca."

    return RefundResponseDTO(
        refund_id=refund_id,
        status="approved",
        amount=amt,
        message=msg,
    )

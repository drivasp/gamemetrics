from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token
from wallet.servicio import apply_transaction, get_balance, list_transactions

router = APIRouter(prefix="/wallet", tags=["wallet"])


class WalletDTO(BaseModel):
    balance: float
    currency: str = "USD"


class WalletTxDTO(BaseModel):
    tx_id: str
    amount: float
    tx_type: str
    reference_id: str
    created_at: str


class TopUpDTO(BaseModel):
    amount: float = Field(gt=0, le=500)
    idempotency_key: str = ""


class TopUpResponseDTO(BaseModel):
    balance: float
    tx_id: str
    message: str


@router.get("", response_model=WalletDTO)
async def wallet_balance(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    bal = await get_balance(user_id)
    return WalletDTO(balance=bal)


@router.get("/transactions", response_model=list[WalletTxDTO])
async def wallet_transactions(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    rows = await list_transactions(user_id)
    return [WalletTxDTO(**r) for r in rows]


@router.post("/topup", response_model=TopUpResponseDTO)
async def wallet_topup(
    body: TopUpDTO,
    authorization: Annotated[str | None, Header()] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """Recarga sandbox de la cartera. Idempotency-Key estable requerida (header o body)."""
    _, user_id = require_token(authorization)
    amount = round(float(body.amount), 2)
    if amount < 1:
        raise HTTPException(400, "El mínimo de recarga es $1.00")
    key = (body.idempotency_key or idempotency_key_header or "").strip()
    if not key:
        # Clave estable por usuario+monto redondeado+ventana de 1s no — usar solo header/body.
        # Fallback sandbox: clave por centavos (permite 1 topup idéntico por monto; E2E pasa key).
        key = f"topup_{user_id}_{int(amount * 100)}"
    try:
        bal, tx_id = await apply_transaction(
            user_id,
            amount,
            tx_type="topup",
            reference_id=f"topup_{amount}",
            idempotency_key=key[:128],
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return TopUpResponseDTO(
        balance=bal,
        tx_id=tx_id,
        message=f"Se añadieron ${amount:.2f} a tu cartera GameMetrics.",
    )

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from marketplace.fees_calc import GAME_FEE_PCT, PLATFORM_FEE_PCT, fee_breakdown
from marketplace.service import (
    cancel_listing,
    create_listing,
    history_for_user,
    inventory_for_user,
    list_active_listings,
    mint_item,
    purchase_listing,
    seller_balance_from_market,
)
from security.rate_limit import rate_limit
from shared.auth_deps import require_token

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class MintDTO(BaseModel):
    game_id: str = Field(min_length=1, max_length=64)
    item_name: str = Field(min_length=1, max_length=120)
    item_type: str = "cosmetic"


class ListingDTO(BaseModel):
    item_id: str
    price_usd: float = Field(gt=0)


class BuyDTO(BaseModel):
    listing_id: str
    idempotency_key: str = ""


@router.get("/fees")
async def marketplace_fees():
    """
    Preview/calculadora PÚBLICA de fees.

    Decisión de producto (auditoría): permanece público porque:
    - NO modifica balances
    - NO crea transacciones / listings / pagos
    - NO cambia ownership
    - NO escribe en el ledger durable
    Solo calcula porcentajes a partir de env + precio de ejemplo.
    """
    return {
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "game_fee_pct": GAME_FEE_PCT,
        "example_10": fee_breakdown(10),
        "mutates_money": False,
        "auth_required": False,
        "note": (
            "Preview público de comisiones. No ejecuta operaciones financieras. "
            "Fee % = política GameMetrics configurable (env)."
        ),
        "payment": "Sandbox wallet — PSP real pendiente de credenciales",
    }


@router.get("/listings")
async def get_listings(authorization: Annotated[str | None, Header()] = None):
    require_token(authorization)
    return {"items": list_active_listings(100)}


@router.get("/inventory")
async def get_inventory(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    return {"items": inventory_for_user(user_id)}


@router.get("/history")
async def get_history(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    return {
        "items": history_for_user(user_id),
        "seller_market_earnings": seller_balance_from_market(user_id),
    }


@router.post("/items", status_code=201)
async def post_mint(body: MintDTO, authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    await rate_limit(user_id, "market_mint", limit=20, window_s=3600)
    item = await mint_item(
        owner_user_id=user_id,
        game_id=body.game_id,
        item_name=body.item_name,
        item_type=body.item_type,
    )
    return item


@router.post("/listings", status_code=201)
async def post_listing(body: ListingDTO, authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    await rate_limit(user_id, "market_list", limit=30, window_s=3600)
    try:
        return await create_listing(seller_user_id=user_id, item_id=body.item_id, price_usd=body.price_usd)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/listings/{listing_id}/cancel")
async def post_cancel(listing_id: str, authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    try:
        return await cancel_listing(seller_user_id=user_id, listing_id=listing_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/buy", status_code=201)
async def post_buy(
    body: BuyDTO,
    authorization: Annotated[str | None, Header()] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    _, user_id = require_token(authorization)
    await rate_limit(user_id, "market_buy", limit=40, window_s=3600)
    key = body.idempotency_key or (idempotency_key_header or "")
    try:
        from fraud.service import FraudDetectionService

        decision = FraudDetectionService().evaluate(
            user_id=user_id,
            action="market_buy",
            entity_type="listing",
            entity_id=body.listing_id,
            amount=0,
        )
        if decision["action"] == "block":
            raise HTTPException(429, f"Bloqueado por fraude: {decision['reason']}")
        return await purchase_listing(
            buyer_user_id=user_id,
            listing_id=body.listing_id,
            idempotency_key=key,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

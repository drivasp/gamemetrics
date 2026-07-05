from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from coupons.servicio import validate_coupon
from shared.auth_deps import require_token

router = APIRouter(prefix="/coupons", tags=["coupons"])


class ValidateCouponDTO(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    subtotal: float = Field(ge=0)


class CouponPreviewDTO(BaseModel):
    code: str
    discount_type: str
    discount_value: float
    discount_applied: float
    message: str


@router.post("/validate", response_model=CouponPreviewDTO)
async def validate(
    body: ValidateCouponDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    try:
        c = await validate_coupon(body.code, body.subtotal, user_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    label = (
        f"-{c.discount_value:.0f}%"
        if c.discount_type == "pct"
        else f"-${c.discount_value:.2f}"
    )
    return CouponPreviewDTO(
        code=c.code,
        discount_type=c.discount_type,
        discount_value=c.discount_value,
        discount_applied=c.discount_applied,
        message=f"Cupón {c.code} aplicado ({label})",
    )

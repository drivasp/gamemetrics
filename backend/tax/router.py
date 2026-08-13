from fastapi import APIRouter, Header, HTTPException
from typing import Annotated
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, require_roles
from tax.engine import calculate_tax, get_jurisdiction, list_tax_audit, load_rules

router = APIRouter(prefix="/tax", tags=["tax"])


class TaxQuoteDTO(BaseModel):
    amount: float = Field(gt=0)
    country_code: str = Field(min_length=2, max_length=2)
    order_id: str = ""


@router.get("/rules")
async def tax_rules(authorization: Annotated[str | None, Header()] = None):
    require_token(authorization)
    return load_rules()


@router.get("/jurisdictions/{country_code}")
async def tax_jurisdiction(country_code: str, authorization: Annotated[str | None, Header()] = None):
    require_token(authorization)
    return get_jurisdiction(country_code)


@router.post("/quote")
async def tax_quote(body: TaxQuoteDTO, authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    return calculate_tax(body.amount, body.country_code, order_id=body.order_id, actor_id=user_id)


@router.get("/audit")
async def tax_audit(authorization: Annotated[str | None, Header()] = None):
    await require_roles(authorization, "admin")
    return {"items": list_tax_audit(100)}

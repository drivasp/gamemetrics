"""Panel publisher B2B."""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

router = APIRouter(prefix="/partners", tags=["partners"])


class PartnerRegisterDTO(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)


class PartnerGameDTO(BaseModel):
    product_id: str
    game_name: str


async def _partner_for_user(user_id: str, email: str) -> dict | None:
    rows = await pinot_query(
        f"SELECT partner_id, company_name, contact_email, revenue_share_pct, status, created_at "
        f"FROM fact_partner_accounts WHERE contact_email = '{esc(email)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        return None
    r = rows[0]
    return {
        "partner_id": r[0],
        "company_name": r[1],
        "contact_email": r[2],
        "revenue_share_pct": float(r[3] or 70),
        "status": r[4],
        "created_at": str(r[5]),
    }


@router.get("/me")
async def my_partner(authorization: Annotated[str | None, Header()] = None):
    token_user, user_id = require_token(authorization)
    # require_token returns (payload or email?, user_id) - check auth_deps
    email_rows = await pinot_query(
        f"SELECT email FROM fact_users WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    email = email_rows[0][0] if email_rows else ""
    partner = await _partner_for_user(user_id, email)
    if not partner:
        return {"partner": None, "games": [], "revenue": []}

    games = await pinot_query(
        f"SELECT partner_game_id, partner_id, product_id, game_name, submission_status, created_at "
        f"FROM fact_partner_games WHERE partner_id = '{esc(partner['partner_id'])}' "
        f"AND deleted = false LIMIT 50"
    )
    revenue = await pinot_query(
        f"SELECT snapshot_id, partner_id, product_id, game_name, units_sold, gross_revenue, "
        f"period_start, period_end, created_at FROM fact_revenue_snapshots "
        f"WHERE partner_id = '{esc(partner['partner_id'])}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT 50"
    )
    return {
        "partner": partner,
        "games": [
            {
                "partner_game_id": g[0],
                "product_id": g[2],
                "game_name": g[3],
                "submission_status": g[4],
                "created_at": str(g[5]),
            }
            for g in games
        ],
        "revenue": [
            {
                "snapshot_id": r[0],
                "product_id": r[2],
                "game_name": r[3],
                "units_sold": int(r[4] or 0),
                "gross_revenue": float(r[5] or 0),
                "created_at": str(r[8]),
            }
            for r in revenue
        ],
    }


@router.post("/register", status_code=201)
async def register_partner(
    body: PartnerRegisterDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    email_rows = await pinot_query(
        f"SELECT email FROM fact_users WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    email = email_rows[0][0] if email_rows else ""
    if not email:
        raise HTTPException(400, "Cuenta sin email")
    existing = await _partner_for_user(user_id, email)
    if existing:
        raise HTTPException(409, "Ya tienes una cuenta publisher")

    partner_id = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_partner_accounts", partner_id, {
        "partner_id": partner_id,
        "company_name": body.company_name.strip(),
        "contact_email": email,
        "revenue_share_pct": 70.0,
        "status": "active",
        "created_at": now_ms,
        "deleted": False,
    })
    return {
        "partner_id": partner_id,
        "message": "Cuenta publisher activada",
    }


@router.post("/games", status_code=201)
async def add_partner_game(
    body: PartnerGameDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    email_rows = await pinot_query(
        f"SELECT email FROM fact_users WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    email = email_rows[0][0] if email_rows else ""
    partner = await _partner_for_user(user_id, email)
    if not partner:
        raise HTTPException(403, "No eres publisher. Regístrate primero.")

    pgid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_partner_games", pgid, {
        "partner_game_id": pgid,
        "partner_id": partner["partner_id"],
        "product_id": body.product_id,
        "game_name": body.game_name,
        "submission_status": "approved",
        "created_at": now_ms,
        "deleted": False,
    })
    # Snapshot demo de ingresos
    sid = uuid.uuid4().hex[:15]
    await kafka_send("fact_revenue_snapshots", sid, {
        "snapshot_id": sid,
        "partner_id": partner["partner_id"],
        "product_id": body.product_id,
        "game_name": body.game_name,
        "units_sold": 12,
        "gross_revenue": 359.88,
        "period_start": now_ms - 30 * 24 * 3600 * 1000,
        "period_end": now_ms,
        "created_at": now_ms,
        "deleted": False,
    })
    return {"partner_game_id": pgid, "message": "Juego añadido al catálogo partner"}

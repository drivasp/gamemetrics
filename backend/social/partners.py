"""Panel publisher B2B."""
from __future__ import annotations

import re
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from launcher.servicio import list_builds, publish_build_bytes
from auth.roles import set_user_role
from checkout.partner_ledger import partner_earnings_summary
from checkout.partner_payouts import (
    create_connect_onboarding_link,
    create_payout,
    get_connect_account,
    refresh_connect_status,
)
from checkout.saas_billing import (
    create_saas_checkout_session,
    get_branding,
    get_partner_subscription,
    list_partner_placements,
    list_plans,
    purchase_featured,
    save_branding,
)
from shared.auth_deps import require_token, require_roles, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from social.partner_game_claims import cache_partner_game, list_cached_claims

router = APIRouter(prefix="/partners", tags=["partners"])

MAX_BUILD_BYTES = 20 * 1024 * 1024


class PartnerRegisterDTO(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)


class PartnerGameDTO(BaseModel):
    product_id: str
    game_name: str


async def _partner_email(user_id: str) -> str:
    email_rows = await pinot_query(
        f"SELECT email FROM fact_users WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    return email_rows[0][0] if email_rows else ""


async def _owns_partner_game(partner_id: str, product_id: str) -> bool:
    rows = await pinot_query(
        f"SELECT partner_game_id FROM fact_partner_games "
        f"WHERE partner_id = '{esc(partner_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    return len(rows) > 0


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
        return {
            "partner": None,
            "games": [],
            "revenue": [],
            "earnings": None,
            "ledger": [],
        }

    games_raw = await pinot_query(
        f"SELECT partner_game_id, partner_id, product_id, game_name, submission_status, created_at "
        f"FROM fact_partner_games WHERE partner_id = '{esc(partner['partner_id'])}' "
        f"AND deleted = false LIMIT 50"
    )
    games_by_id: dict[str, dict] = {}
    for g in games_raw or []:
        games_by_id[str(g[0])] = {
            "partner_game_id": g[0],
            "product_id": g[2],
            "game_name": g[3],
            "submission_status": g[4],
            "created_at": str(g[5]),
        }
    for cached in list_cached_claims():
        if str(cached.get("partner_id")) == str(partner["partner_id"]):
            games_by_id[str(cached["partner_game_id"])] = {
                "partner_game_id": cached["partner_game_id"],
                "product_id": cached["product_id"],
                "game_name": cached.get("game_name") or "",
                "submission_status": cached.get("submission_status") or "pending",
                "created_at": str(cached.get("created_at") or ""),
            }
    games = list(games_by_id.values())
    earnings = await partner_earnings_summary(partner["partner_id"])
    # Compat UI: "revenue" ahora refleja totales reales por producto (no demos).
    revenue = [
        {
            "snapshot_id": f"live_{p['product_id']}",
            "product_id": p["product_id"],
            "game_name": p["game_name"],
            "units_sold": int(p["units_sold"]),
            "gross_revenue": float(p["gross_revenue"]),
            "platform_fee": float(p["platform_fee"]),
            "publisher_net": float(p["publisher_net"]),
            "created_at": "",
        }
        for p in earnings.get("by_product", [])
    ]
    partner["balance_available"] = float(earnings.get("balance_available") or 0)
    partner["balance_pending"] = float(earnings.get("balance_pending") or 0)
    partner["balance_paid_out"] = float(earnings.get("balance_paid_out") or 0)
    partner["gross_revenue"] = float(earnings.get("gross_revenue") or 0)
    partner["platform_fee"] = float(earnings.get("platform_fee") or 0)
    partner["publisher_net"] = float(earnings.get("publisher_net") or 0)
    partner["units_sold"] = int(earnings.get("units_sold") or 0)

    sub = await get_partner_subscription(partner["partner_id"])
    brand = await get_branding(partner["partner_id"])
    connect = await get_connect_account(partner["partner_id"])
    placements = await list_partner_placements(partner["partner_id"])

    return {
        "partner": partner,
        "games": games,
        "revenue": revenue,
        "earnings": {
            "gross_revenue": partner["gross_revenue"],
            "platform_fee": partner["platform_fee"],
            "publisher_net": partner["publisher_net"],
            "balance_available": partner["balance_available"],
            "balance_pending": partner["balance_pending"],
            "balance_paid_out": partner["balance_paid_out"],
            "payout_min_usd": earnings.get("payout_min_usd"),
            "hold_days": earnings.get("hold_days"),
            "can_request_payout": earnings.get("can_request_payout"),
            "units_sold": partner["units_sold"],
            "refund_count": int(earnings.get("refund_count") or 0),
            "publisher_share_pct": partner["revenue_share_pct"],
            "platform_take_rate_pct": round(100.0 - float(partner["revenue_share_pct"]), 2),
        },
        "payouts": earnings.get("payouts") or [],
        "subscription": sub,
        "plans": list_plans(),
        "branding": brand,
        "connect": connect,
        "featured_placements": placements,
        "ledger": [
            {
                "ledger_entry_id": e["ledger_entry_id"],
                "entry_type": e["entry_type"],
                "product_id": e["product_id"],
                "game_name": e["game_name"],
                "order_id": e["order_id"],
                "quantity": e["quantity"],
                "gross_amount": e["gross_amount"],
                "platform_fee_amount": e["platform_fee_amount"],
                "publisher_net_amount": e["publisher_net_amount"],
                "currency": e["currency"],
                "status": e["status"],
                "created_at": e["created_at"],
            }
            for e in earnings.get("entries", [])[:50]
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
    role = await set_user_role(user_id, "publisher")
    return {
        "partner_id": partner_id,
        "role": role,
        "message": "Cuenta publisher activada. Tu rol ahora es publisher.",
    }


@router.post("/games", status_code=201)
async def add_partner_game(
    body: PartnerGameDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id, _role = await require_roles(authorization, "publisher", "admin")
    email_rows = await pinot_query(
        f"SELECT email FROM fact_users WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    email = email_rows[0][0] if email_rows else ""
    partner = await _partner_for_user(user_id, email)
    if not partner:
        raise HTTPException(403, "No eres publisher. Regístrate primero.")

    existing = await pinot_query(
        f"SELECT partner_id, submission_status FROM fact_partner_games "
        f"WHERE product_id = '{esc(body.product_id)}' AND deleted = false LIMIT 10"
    )
    for row in existing or []:
        owner = str(row[0])
        status = str(row[1] or "").lower()
        if owner != partner["partner_id"] and status in ("approved", "pending"):
            raise HTTPException(
                409,
                "Este juego ya tiene un claim de otro publisher (pendiente o aprobado).",
            )
        if owner == partner["partner_id"] and status in ("approved", "pending"):
            raise HTTPException(400, "Ya reclamaste este juego.")

    pgid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    row = {
        "partner_game_id": pgid,
        "partner_id": partner["partner_id"],
        "product_id": body.product_id,
        "game_name": body.game_name,
        "submission_status": "pending",
        "created_at": now_ms,
        "deleted": False,
    }
    await kafka_send("fact_partner_games", pgid, row)
    cache_partner_game(row)
    return {
        "partner_game_id": pgid,
        "submission_status": "pending",
        "message": (
            "Claim enviado. Un admin de GameMetrics debe aprobarlo "
            "(como revisión Steamworks). Hasta entonces no recibes ingresos de este juego."
        ),
    }


@router.get("/games/{product_id}/builds")
async def list_partner_builds(
    product_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id, _role = await require_roles(authorization, "publisher", "admin")
    email = await _partner_email(user_id)
    partner = await _partner_for_user(user_id, email)
    if not partner:
        raise HTTPException(403, "No eres publisher")
    if not await _owns_partner_game(partner["partner_id"], product_id):
        raise HTTPException(403, "Este producto no pertenece a tu cuenta publisher")
    builds = await list_builds(product_id, limit=20)
    return {"items": builds}


@router.post("/games/{product_id}/builds", status_code=201)
async def upload_partner_build(
    product_id: str,
    authorization: Annotated[str | None, Header()] = None,
    version: Annotated[str, Form()] = "1.0.1",
    file: UploadFile = File(...),
):
    """Upload a real ZIP build for a partner-owned product."""
    _, user_id, _role = await require_roles(authorization, "publisher", "admin")
    email = await _partner_email(user_id)
    partner = await _partner_for_user(user_id, email)
    if not partner:
        raise HTTPException(403, "No eres publisher. Regístrate primero.")
    if not await _owns_partner_game(partner["partner_id"], product_id):
        raise HTTPException(403, "Este producto no pertenece a tu cuenta publisher")

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Archivo vacío")
    if len(raw) > MAX_BUILD_BYTES:
        raise HTTPException(413, f"Build demasiado grande (máx {MAX_BUILD_BYTES // (1024*1024)} MB)")
    if raw[:2] != b"PK":
        raise HTTPException(400, "El build debe ser un archivo ZIP")

    safe_ver = re.sub(r"[^0-9A-Za-z._-]", "_", (version or "1.0.1").strip())[:32]
    if not safe_ver:
        safe_ver = "1.0.1"

    game_rows = await pinot_query(
        f"SELECT game_name FROM fact_partner_games "
        f"WHERE partner_id = '{esc(partner['partner_id'])}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    game_name = game_rows[0][0] if game_rows else product_id

    build = await publish_build_bytes(product_id, safe_ver, raw, game_name or product_id)
    return {
        "build": build,
        "message": f"Build v{safe_ver} publicado",
    }


class BrandingDTO(BaseModel):
    store_name: str = Field(min_length=2, max_length=80)
    logo_url: str = ""
    accent_color: str = "#e94560"
    tagline: str = ""


class FeaturedBuyDTO(BaseModel):
    product_id: str
    game_name: str = ""
    pay_method: str = "sandbox"  # sandbox | stripe


class SaasPlanDTO(BaseModel):
    plan_id: str
    pay_method: str = "sandbox"


async def _require_partner(authorization: str | None) -> tuple[str, dict]:
    _, user_id, _role = await require_roles(authorization, "publisher", "admin")
    email = await _partner_email(user_id)
    partner = await _partner_for_user(user_id, email)
    if not partner:
        raise HTTPException(403, "No eres publisher. Regístrate primero.")
    return user_id, partner


@router.post("/connect/onboard")
async def partner_connect_onboard(authorization: Annotated[str | None, Header()] = None):
    """Stripe Connect Express onboarding (opcional; requiere STRIPE_SECRET_KEY)."""
    _, partner = await _require_partner(authorization)
    try:
        return await create_connect_onboarding_link(
            partner["partner_id"],
            partner.get("contact_email") or "",
            partner.get("company_name") or "",
        )
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Stripe Connect error: {e}")


@router.get("/connect/status")
async def partner_connect_status(authorization: Annotated[str | None, Header()] = None):
    _, partner = await _require_partner(authorization)
    return await refresh_connect_status(partner["partner_id"]) or {
        "onboarding_status": "none",
        "payouts_enabled": False,
    }


@router.post("/saas/subscribe")
async def partner_saas_subscribe(
    body: SaasPlanDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, partner = await _require_partner(authorization)
    try:
        if body.plan_id == "free":
            from checkout.saas_billing import activate_subscription
            sub = await activate_subscription(partner["partner_id"], "free")
            return {"mode": "sandbox", "subscription": sub}
        return await create_saas_checkout_session(partner["partner_id"], body.plan_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/branding")
async def partner_save_branding(
    body: BrandingDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, partner = await _require_partner(authorization)
    try:
        return await save_branding(
            partner["partner_id"],
            body.store_name,
            body.logo_url,
            body.accent_color,
            body.tagline,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))


@router.get("/branding/{partner_id}")
async def public_partner_branding(partner_id: str):
    brand = await get_branding(partner_id)
    if not brand:
        raise HTTPException(404, "Sin branding white-label")
    return brand


@router.post("/featured/buy")
async def partner_buy_featured(
    body: FeaturedBuyDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, partner = await _require_partner(authorization)
    if not await _owns_partner_game(partner["partner_id"], body.product_id):
        raise HTTPException(403, "Solo puedes destacar juegos de tu catálogo partner")
    try:
        return await purchase_featured(
            partner["partner_id"],
            body.product_id,
            body.game_name or body.product_id,
            body.pay_method,
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/plans")
async def partner_plans():
    return {"plans": list_plans()}


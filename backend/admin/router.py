"""Panel admin Fase 0 — salud y asignación de roles."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from auth.cliente_jwt import create_token
from auth.roles import ROLES, get_user_role, normalize_role, set_user_role
from checkout.partner_ledger import admin_business_dashboard, platform_gmv_summary
from checkout.partner_payouts import create_payout, list_all_payouts, partner_balance
from shared.auth_deps import require_roles, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

router = APIRouter(prefix="/admin", tags=["admin"])


class SetRoleDTO(BaseModel):
    role: str = Field(min_length=4, max_length=20)


class AdminPayoutDTO(BaseModel):
    partner_id: str
    amount: float = Field(gt=0)
    method: str = "manual"  # manual | stripe_connect
    reference: str = ""
    notes: str = ""


@router.get("/health")
async def admin_health(authorization: Annotated[str | None, Header()] = None):
    _, user_id, role = await require_roles(authorization, "admin")
    return {
        "ok": True,
        "role": role,
        "user_id": user_id,
        "message": "Panel admin operativo (roles + GMV)",
    }


@router.get("/gmv")
async def admin_gmv(authorization: Annotated[str | None, Header()] = None):
    """GMV y take rate (compat). Preferir /admin/dashboard."""
    await require_roles(authorization, "admin")
    summary = await platform_gmv_summary(limit=500)
    return {
        "ok": True,
        **summary,
        "note": (
            "GMV = suma de precios de juego pre-impuesto en ventas netas de reembolsos. "
            "platform_revenue = take rate. publisher_payouts_owed = neto a publishers."
        ),
    }


@router.get("/dashboard")
async def admin_dashboard(authorization: Annotated[str | None, Header()] = None):
    """Dashboard B2B: GMV, ingresos GameMetrics, partners con estado y comisión."""
    await require_roles(authorization, "admin")
    dash = await admin_business_dashboard(limit=500)
    return {"ok": True, **dash}


@router.put("/users/{target_user_id}/role")
async def admin_set_role(
    target_user_id: str,
    body: SetRoleDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, admin_id, _ = await require_roles(authorization, "admin")
    role = normalize_role(body.role)
    if role not in ROLES:
        raise HTTPException(400, f"Rol inválido. Usa: {', '.join(sorted(ROLES))}")

    rows = await pinot_query(
        f"SELECT user_id, email FROM fact_users "
        f"WHERE user_id = '{esc(target_user_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Usuario no encontrado")

    new_role = await set_user_role(target_user_id, role)
    email = rows[0][1]
    # Token fresco solo informativo (el cliente del target debe re-login)
    return {
        "user_id": target_user_id,
        "email": email,
        "role": new_role,
        "changed_by": admin_id,
        "message": f"Rol actualizado a {new_role}. El usuario debe volver a iniciar sesión.",
        "hint_token": create_token(target_user_id, email, role=new_role),
    }


@router.get("/me")
async def admin_me(authorization: Annotated[str | None, Header()] = None):
    _, user_id, role = await require_roles(authorization, "admin")
    return {"user_id": user_id, "role": role}


@router.get("/payouts")
async def admin_list_payouts(authorization: Annotated[str | None, Header()] = None):
    await require_roles(authorization, "admin")
    return {"items": await list_all_payouts(100)}


@router.get("/partners/{partner_id}/balance")
async def admin_partner_balance(
    partner_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    await require_roles(authorization, "admin")
    return await partner_balance(partner_id)


@router.post("/payouts", status_code=201)
async def admin_create_payout(
    body: AdminPayoutDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    """Marca un payout como pagado (manual + referencia) o Transfer Stripe Connect."""
    _, admin_id, _ = await require_roles(authorization, "admin")
    acct = await pinot_query(
        f"SELECT partner_id, company_name FROM fact_partner_accounts "
        f"WHERE partner_id = '{esc(body.partner_id)}' AND deleted = false LIMIT 1"
    )
    if not acct:
        raise HTTPException(404, "Partner no encontrado")
    try:
        row = await create_payout(
            partner_id=body.partner_id,
            amount=body.amount,
            created_by=admin_id,
            method=body.method,
            reference=body.reference,
            notes=body.notes,
        )
        return {
            "ok": True,
            "payout": row,
            "company_name": acct[0][1],
            "message": "Payout registrado como pagado (política tipo Steam: hold + mínimo).",
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"No se pudo completar el payout: {e}")


@router.get("/game-claims")
async def admin_list_game_claims(
    status: str = "pending",
    authorization: Annotated[str | None, Header()] = None,
):
    """Claims de ownership tipo Steamworks review queue."""
    await require_roles(authorization, "admin")
    from social.partner_game_claims import list_cached_claims, cache_partner_game

    want = (status or "pending").lower()
    rows = await pinot_query(
        "SELECT partner_game_id, partner_id, product_id, game_name, submission_status, created_at "
        "FROM fact_partner_games WHERE deleted = false "
        f"AND submission_status = '{esc(want)}' "
        "ORDER BY created_at DESC LIMIT 100"
    )
    by_id: dict[str, dict] = {}
    for r in rows or []:
        item = {
            "partner_game_id": str(r[0]),
            "partner_id": str(r[1]),
            "product_id": str(r[2]),
            "game_name": r[3] or "",
            "submission_status": str(r[4] or want),
            "created_at": int(r[5] or 0),
            "deleted": False,
        }
        by_id[item["partner_game_id"]] = item
        cache_partner_game(item)
    for cached in list_cached_claims(want):
        by_id[str(cached["partner_game_id"])] = cached

    # Enrich with company name
    items = []
    for item in sorted(by_id.values(), key=lambda x: int(x.get("created_at") or 0), reverse=True):
        acct = await pinot_query(
            f"SELECT company_name, contact_email FROM fact_partner_accounts "
            f"WHERE partner_id = '{esc(item['partner_id'])}' AND deleted = false LIMIT 1"
        )
        items.append({
            **item,
            "company_name": (acct[0][0] if acct else "—"),
            "contact_email": (acct[0][1] if acct else "—"),
        })
    return {"items": items, "status": want}


@router.post("/game-claims/{partner_game_id}/approve")
async def admin_approve_game_claim(
    partner_game_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    await require_roles(authorization, "admin")
    from social.partner_game_claims import cache_partner_game, get_claim

    row = get_claim(partner_game_id)
    if not row:
        rows = await pinot_query(
            f"SELECT partner_game_id, partner_id, product_id, game_name, submission_status, created_at "
            f"FROM fact_partner_games WHERE partner_game_id = '{esc(partner_game_id)}' "
            f"AND deleted = false LIMIT 1"
        )
        if not rows:
            raise HTTPException(404, "Claim no encontrado")
        row = {
            "partner_game_id": str(rows[0][0]),
            "partner_id": str(rows[0][1]),
            "product_id": str(rows[0][2]),
            "game_name": rows[0][3] or "",
            "submission_status": str(rows[0][4] or "pending"),
            "created_at": int(rows[0][5] or 0),
            "deleted": False,
        }

    # Un solo owner aprobado por product_id
    others = await pinot_query(
        f"SELECT partner_game_id, partner_id FROM fact_partner_games "
        f"WHERE product_id = '{esc(row['product_id'])}' AND deleted = false "
        f"AND submission_status = 'approved' LIMIT 5"
    )
    for o in others or []:
        if str(o[0]) != partner_game_id:
            raise HTTPException(409, "Ya hay otro publisher aprobado para este juego.")

    updated = {**row, "submission_status": "approved"}
    await kafka_send("fact_partner_games", partner_game_id, updated)
    cache_partner_game(updated)
    return {
        "ok": True,
        "claim": updated,
        "message": "Claim aprobado. Las ventas de este juego ya se atribuyen al publisher.",
    }


@router.post("/game-claims/{partner_game_id}/reject")
async def admin_reject_game_claim(
    partner_game_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    await require_roles(authorization, "admin")
    from social.partner_game_claims import cache_partner_game, get_claim

    row = get_claim(partner_game_id)
    if not row:
        rows = await pinot_query(
            f"SELECT partner_game_id, partner_id, product_id, game_name, submission_status, created_at "
            f"FROM fact_partner_games WHERE partner_game_id = '{esc(partner_game_id)}' "
            f"AND deleted = false LIMIT 1"
        )
        if not rows:
            raise HTTPException(404, "Claim no encontrado")
        row = {
            "partner_game_id": str(rows[0][0]),
            "partner_id": str(rows[0][1]),
            "product_id": str(rows[0][2]),
            "game_name": rows[0][3] or "",
            "submission_status": str(rows[0][4] or "pending"),
            "created_at": int(rows[0][5] or 0),
            "deleted": False,
        }

    updated = {**row, "submission_status": "rejected"}
    await kafka_send("fact_partner_games", partner_game_id, updated)
    cache_partner_game(updated)
    return {"ok": True, "claim": updated, "message": "Claim rechazado."}

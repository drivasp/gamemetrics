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
    method: str = "manual"  # manual | stripe_connect | sandbox_fail
    reference: str = ""
    notes: str = ""
    force_fail: bool = False
    idempotency_key: str = ""


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
            idempotency_key=body.idempotency_key,
            force_fail=body.force_fail,
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
    _, admin_id, _ = await require_roles(authorization, "admin")
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

    fee_entry = None
    try:
        from checkout.direct_fee import charge_publication_fee, publication_fee_policy
        from checkout.financial_audit import audit_event

        fee_entry = await charge_publication_fee(
            partner_id=str(updated["partner_id"]),
            product_id=str(updated["product_id"]),
            game_name=str(updated.get("game_name") or ""),
            charged_by=admin_id,
        )
        audit_event(
            actor_id=admin_id,
            action="approve_claim_and_charge_publication_fee",
            entity_type="partner_game",
            entity_id=partner_game_id,
            amount=(fee_entry or {}).get("platform_fee_amount"),
            after=updated,
            meta={"fee_policy": publication_fee_policy()},
        )
    except Exception as exc:
        print(f"[direct_fee] ERROR claim={partner_game_id}: {exc}")

    return {
        "ok": True,
        "claim": updated,
        "publication_fee": fee_entry,
        "message": (
            "Claim aprobado. Las ventas de este juego ya se atribuyen al publisher."
            + (" Tarifa de publicación registrada en ledger." if fee_entry else "")
        ),
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


class ChargebackDTO(BaseModel):
    payment_id: str
    order_id: str
    product_id: str
    buyer_user_id: str = ""
    game_name: str = ""
    amount: float = Field(gt=0)
    reason: str = "payment_dispute"


@router.post("/chargebacks", status_code=201)
async def admin_record_chargeback(
    body: ChargebackDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    """
    Registra un chargeback en el ledger (idempotente).
    Integración automática Stripe Disputes: pendiente de STRIPE_WEBHOOK_SECRET + decisión ops.
    """
    _, admin_id, _ = await require_roles(authorization, "admin")
    from checkout.chargebacks import record_chargeback_ledger
    from checkout.financial_audit import audit_event

    try:
        entry = await record_chargeback_ledger(
            payment_id=body.payment_id,
            order_id=body.order_id,
            buyer_user_id=body.buyer_user_id or admin_id,
            product_id=body.product_id,
            game_name=body.game_name,
            amount=body.amount,
            reason=body.reason,
            created_by=admin_id,
        )
    except Exception as e:
        raise HTTPException(400, str(e))
    if not entry:
        raise HTTPException(404, "No hay partner atribuido para este producto; chargeback no registrado en B2B ledger.")
    audit_event(
        actor_id=admin_id,
        action="record_chargeback",
        entity_type="chargeback",
        entity_id=entry.get("ledger_entry_id", body.payment_id),
        amount=-abs(body.amount),
        after=entry,
    )
    return {
        "ok": True,
        "entry": entry,
        "message": "Chargeback registrado. Reduce AGR y saldo del publisher.",
        "open_dependency": (
            "Fee del PSP, disputa automática vía webhook y hold de cuenta "
            "requieren contrato con procesador + decisión empresarial."
        ),
    }


@router.get("/partners/{partner_id}/statement")
async def admin_partner_statement(
    partner_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    await require_roles(authorization, "admin")
    from checkout.financial_statement import build_partner_financial_statement

    return await build_partner_financial_statement(partner_id)


@router.get("/finance/policy")
async def admin_finance_policy(authorization: Annotated[str | None, Header()] = None):
    await require_roles(authorization, "admin")
    from checkout.direct_fee import publication_fee_policy
    from checkout.revenue_share import MODE, example_steam_math
    import os

    return {
        "revenue_share_mode": MODE,
        "publication_fee": publication_fee_policy(),
        "payout_min_usd": float(os.getenv("PAYOUT_MIN_USD", "1")),
        "payout_hold_ms": int(os.getenv("PAYOUT_HOLD_MS", "0")),
        "steam_tier_examples": {
            "1_000": example_steam_math(1_000),
            "100_000": example_steam_math(100_000),
            "1_000_000": example_steam_math(1_000_000),
            "10_000_000": example_steam_math(10_000_000),
            "50_000_000": example_steam_math(50_000_000),
            "60_000_000": example_steam_math(60_000_000),
        },
        "tier_note": (
            "Los ejemplos 30/25/20 son el modelo Steam reportado por la industria "
            "(anuncio Valve 2018). Activar con REVENUE_SHARE_MODE=steam_tiers."
        ),
    }


@router.get("/finance/audit")
async def admin_finance_audit(
    limit: int = 50,
    authorization: Annotated[str | None, Header()] = None,
):
    from shared.auth_deps import require_permission
    from checkout.financial_audit import list_audit
    from fraud.service import FraudDetectionService

    await require_permission(authorization, "finance.audit")
    return {
        "items": list_audit(limit=min(200, max(1, limit))),
        "fraud_events": FraudDetectionService.list_events(limit=min(100, max(1, limit))),
    }

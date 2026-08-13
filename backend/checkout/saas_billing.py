"""
Fase 4 — SaaS B2B para publishers (cliente = estudio).

Modelo profesional (Xsolla / white-label stores):
- Plan mensual: free | pro | studio
- White-label: nombre, logo, color, tagline (requiere pro+)
- Featured placement de pago: destaque en tienda por N días
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any

from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4000").rstrip("/")

SAAS_PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "plan_id": "free",
        "name": "Free",
        "price_usd": 0.0,
        "features": ["panel publisher", "ledger", "builds"],
        "white_label": False,
        "featured_discount_pct": 0,
    },
    "pro": {
        "plan_id": "pro",
        "name": "Pro",
        "price_usd": 29.0,
        "features": ["white-label branding", "featured 10% off", "API keys"],
        "white_label": True,
        "featured_discount_pct": 10,
    },
    "studio": {
        "plan_id": "studio",
        "name": "Studio",
        "price_usd": 79.0,
        "features": ["white-label", "featured 25% off", "prioridad soporte"],
        "white_label": True,
        "featured_discount_pct": 25,
    },
}

FEATURED_BASE_USD = float(os.getenv("FEATURED_PLACEMENT_USD", "49"))
FEATURED_DAYS = int(os.getenv("FEATURED_PLACEMENT_DAYS", "7"))

_SUB_CACHE: dict[str, dict[str, Any]] = {}
_BRAND_CACHE: dict[str, dict[str, Any]] = {}
_FEAT_CACHE: dict[str, dict[str, Any]] = {}


def list_plans() -> list[dict[str, Any]]:
    return list(SAAS_PLANS.values())


async def get_partner_subscription(partner_id: str) -> dict[str, Any]:
    if partner_id in _SUB_CACHE and _SUB_CACHE[partner_id].get("status") == "active":
        sub = _SUB_CACHE[partner_id]
        if int(sub.get("current_period_end") or 0) > int(time.time() * 1000):
            return {**sub, "plan": SAAS_PLANS.get(sub["plan_id"], SAAS_PLANS["free"])}

    rows = await pinot_query(
        f"SELECT subscription_id, partner_id, plan_id, status, billing_provider, "
        f"stripe_subscription_id, price_usd, current_period_end, created_at "
        f"FROM fact_saas_subscriptions WHERE partner_id = '{esc(partner_id)}' "
        f"AND deleted = false ORDER BY created_at DESC LIMIT 5"
    )
    now = int(time.time() * 1000)
    for r in rows or []:
        status = str(r[3] or "")
        end = int(r[7] or 0)
        if status == "active" and end > now:
            sub = {
                "subscription_id": r[0],
                "partner_id": r[1],
                "plan_id": r[2],
                "status": status,
                "billing_provider": r[4],
                "stripe_subscription_id": r[5] or "",
                "price_usd": float(r[6] or 0),
                "current_period_end": end,
                "created_at": int(r[8] or 0),
            }
            _SUB_CACHE[partner_id] = sub
            return {**sub, "plan": SAAS_PLANS.get(sub["plan_id"], SAAS_PLANS["free"])}

    return {
        "subscription_id": "",
        "partner_id": partner_id,
        "plan_id": "free",
        "status": "active",
        "billing_provider": "none",
        "stripe_subscription_id": "",
        "price_usd": 0.0,
        "current_period_end": 0,
        "created_at": 0,
        "plan": SAAS_PLANS["free"],
    }


async def activate_subscription(
    partner_id: str,
    plan_id: str,
    billing_provider: str = "sandbox",
    stripe_subscription_id: str = "",
    days: int = 30,
) -> dict[str, Any]:
    plan = SAAS_PLANS.get(plan_id)
    if not plan:
        raise ValueError(f"Plan inválido. Usa: {', '.join(SAAS_PLANS)}")

    now = int(time.time() * 1000)
    sid = uuid.uuid4().hex[:15]
    if plan_id == "free":
        row = {
            "subscription_id": sid,
            "partner_id": partner_id,
            "plan_id": "free",
            "status": "active",
            "billing_provider": "none",
            "stripe_subscription_id": "",
            "price_usd": 0.0,
            "current_period_end": now + 3650 * 24 * 3600 * 1000,
            "created_at": now,
            "deleted": False,
        }
    else:
        row = {
            "subscription_id": sid,
            "partner_id": partner_id,
            "plan_id": plan_id,
            "status": "active",
            "billing_provider": billing_provider,
            "stripe_subscription_id": stripe_subscription_id,
            "price_usd": float(plan["price_usd"]),
            "current_period_end": now + days * 24 * 3600 * 1000,
            "created_at": now,
            "deleted": False,
        }
    _SUB_CACHE[partner_id] = row
    await kafka_send("fact_saas_subscriptions", sid, row)
    return {**row, "plan": plan}


async def create_saas_checkout_session(partner_id: str, plan_id: str) -> dict[str, Any]:
    plan = SAAS_PLANS.get(plan_id)
    if not plan or plan_id == "free":
        raise ValueError("Elige plan pro o studio")
    if not STRIPE_SECRET:
        sub = await activate_subscription(partner_id, plan_id, "sandbox")
        return {"mode": "sandbox", "subscription": sub, "checkout_url": None}

    import stripe

    stripe.api_key = STRIPE_SECRET
    cents = max(50, int(round(float(plan["price_usd"]) * 100)))
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"GameMetrics SaaS — {plan['name']} (30 días)"},
                "unit_amount": cents,
            },
            "quantity": 1,
        }],
        success_url=f"{FRONTEND_URL}/my-partner?saas=ok&plan={plan_id}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/my-partner?saas=cancel",
        metadata={
            "kind": "saas_subscription",
            "partner_id": partner_id,
            "plan_id": plan_id,
        },
    )
    return {"mode": "stripe", "checkout_url": session.url, "session_id": session.id}


async def get_branding(partner_id: str) -> dict[str, Any] | None:
    if partner_id in _BRAND_CACHE:
        return _BRAND_CACHE[partner_id]
    rows = await pinot_query(
        f"SELECT partner_id, store_name, logo_url, accent_color, tagline, updated_at "
        f"FROM fact_partner_branding WHERE partner_id = '{esc(partner_id)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        return None
    r = rows[0]
    brand = {
        "partner_id": r[0],
        "store_name": r[1] or "",
        "logo_url": r[2] or "",
        "accent_color": r[3] or "#e94560",
        "tagline": r[4] or "",
        "updated_at": int(r[5] or 0),
    }
    _BRAND_CACHE[partner_id] = brand
    return brand


async def save_branding(
    partner_id: str,
    store_name: str,
    logo_url: str = "",
    accent_color: str = "#e94560",
    tagline: str = "",
) -> dict[str, Any]:
    sub = await get_partner_subscription(partner_id)
    if not (sub.get("plan") or {}).get("white_label"):
        raise PermissionError("White-label requiere plan Pro o Studio")
    now = int(time.time() * 1000)
    row = {
        "partner_id": partner_id,
        "store_name": (store_name or "").strip()[:80],
        "logo_url": (logo_url or "").strip()[:500],
        "accent_color": (accent_color or "#e94560").strip()[:20],
        "tagline": (tagline or "").strip()[:160],
        "updated_at": now,
        "deleted": False,
    }
    _BRAND_CACHE[partner_id] = row
    await kafka_send("fact_partner_branding", partner_id, row)
    return row


def featured_price_for_plan(plan_id: str) -> float:
    plan = SAAS_PLANS.get(plan_id, SAAS_PLANS["free"])
    disc = float(plan.get("featured_discount_pct") or 0) / 100.0
    return round(FEATURED_BASE_USD * (1.0 - disc), 2)


async def activate_featured_placement(
    partner_id: str,
    product_id: str,
    game_name: str,
    amount_paid: float,
    billing_provider: str = "sandbox",
    days: int | None = None,
) -> dict[str, Any]:
    now = int(time.time() * 1000)
    dur = days or FEATURED_DAYS
    pid = uuid.uuid4().hex[:15]
    row = {
        "placement_id": pid,
        "partner_id": partner_id,
        "product_id": product_id,
        "game_name": game_name or product_id,
        "status": "active",
        "billing_provider": billing_provider,
        "amount_paid": float(amount_paid),
        "duration_days": int(dur),
        "starts_at": now,
        "ends_at": now + dur * 24 * 3600 * 1000,
        "created_at": now,
        "deleted": False,
    }
    _FEAT_CACHE[pid] = row
    await kafka_send("fact_featured_placements", pid, row)
    return row


async def purchase_featured(
    partner_id: str,
    product_id: str,
    game_name: str,
    pay_method: str = "sandbox",
) -> dict[str, Any]:
    sub = await get_partner_subscription(partner_id)
    price = featured_price_for_plan(sub.get("plan_id") or "free")
    method = (pay_method or "sandbox").lower()

    if method == "stripe" and STRIPE_SECRET:
        import stripe

        stripe.api_key = STRIPE_SECRET
        cents = max(50, int(round(price * 100)))
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Featured placement — {game_name or product_id} ({FEATURED_DAYS} días)",
                    },
                    "unit_amount": cents,
                },
                "quantity": 1,
            }],
            success_url=(
                f"{FRONTEND_URL}/my-partner?featured=ok&product={product_id}"
                f"&session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{FRONTEND_URL}/my-partner?featured=cancel",
            metadata={
                "kind": "featured_placement",
                "partner_id": partner_id,
                "product_id": product_id,
                "game_name": game_name or product_id,
                "amount": str(price),
            },
        )
        return {"mode": "stripe", "checkout_url": session.url, "price_usd": price}

    placement = await activate_featured_placement(
        partner_id, product_id, game_name, price, "sandbox"
    )
    return {"mode": "sandbox", "placement": placement, "price_usd": price}


async def list_active_featured_product_ids(limit: int = 12) -> list[str]:
    now = int(time.time() * 1000)
    rows = await pinot_query(
        f"SELECT product_id, ends_at, placement_id FROM fact_featured_placements "
        f"WHERE deleted = false AND status = 'active' "
        f"ORDER BY created_at DESC LIMIT {int(limit) * 3}"
    )
    ids: list[str] = []
    seen: set[str] = set()
    for r in rows or []:
        pid, ends, _ = r[0], int(r[1] or 0), r[2]
        if ends > now and pid not in seen:
            seen.add(pid)
            ids.append(str(pid))
        if len(ids) >= limit:
            break
    for cached in _FEAT_CACHE.values():
        if (
            cached.get("status") == "active"
            and int(cached.get("ends_at") or 0) > now
            and cached["product_id"] not in seen
        ):
            ids.insert(0, cached["product_id"])
            seen.add(cached["product_id"])
    return ids[:limit]


async def list_partner_placements(partner_id: str, limit: int = 20) -> list[dict[str, Any]]:
    rows = await pinot_query(
        f"SELECT placement_id, partner_id, product_id, game_name, status, "
        f"billing_provider, amount_paid, duration_days, starts_at, ends_at, created_at "
        f"FROM fact_featured_placements WHERE partner_id = '{esc(partner_id)}' "
        f"AND deleted = false ORDER BY created_at DESC LIMIT {int(limit)}"
    )
    items = []
    for r in rows or []:
        items.append({
            "placement_id": r[0],
            "partner_id": r[1],
            "product_id": r[2],
            "game_name": r[3],
            "status": r[4],
            "billing_provider": r[5],
            "amount_paid": float(r[6] or 0),
            "duration_days": int(r[7] or 0),
            "starts_at": int(r[8] or 0),
            "ends_at": int(r[9] or 0),
            "created_at": int(r[10] or 0),
        })
    for c in _FEAT_CACHE.values():
        if c.get("partner_id") == partner_id and not any(
            i["placement_id"] == c["placement_id"] for i in items
        ):
            items.insert(0, c)
    return items[:limit]


async def fulfill_saas_from_stripe_session(session_id: str) -> dict[str, Any] | None:
    if not STRIPE_SECRET:
        return None
    import stripe

    stripe.api_key = STRIPE_SECRET
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != "paid":
        return None
    meta = session.metadata or {}
    if meta.get("kind") != "saas_subscription":
        return None
    return await activate_subscription(
        meta["partner_id"],
        meta["plan_id"],
        "stripe",
        stripe_subscription_id=session_id,
    )


async def fulfill_featured_from_stripe_session(session_id: str) -> dict[str, Any] | None:
    if not STRIPE_SECRET:
        return None
    import stripe

    stripe.api_key = STRIPE_SECRET
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != "paid":
        return None
    meta = session.metadata or {}
    if meta.get("kind") != "featured_placement":
        return None
    return await activate_featured_placement(
        meta["partner_id"],
        meta["product_id"],
        meta.get("game_name") or meta["product_id"],
        float(meta.get("amount") or FEATURED_BASE_USD),
        "stripe",
    )

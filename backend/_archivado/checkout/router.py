import hashlib

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from auth.cliente_jwt import new_id
from carrito.servicio import fetch_cart
from checkout.modelos_checkout import CheckoutRequestDTO, CheckoutResponseDTO
from checkout.servicio import (
    STRIPE_SECRET,
    STRIPE_WEBHOOK_SECRET,
    create_pending_order,
    create_stripe_session,
    fulfill_from_stripe_session,
    fulfill_order,
    order_already_paid,
)
from coupons.servicio import redeem_coupon, validate_coupon
from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from wallet.servicio import apply_transaction, get_balance

router = APIRouter(prefix="/checkout", tags=["checkout"])


async def _user_owns(user_id: str, product_id: str) -> bool:
    rows = await pinot_query(
        f"SELECT purchase_id FROM fact_purchases "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false AND refunded = false LIMIT 1"
    )
    return len(rows) > 0


async def _validate_cart(user_id: str):
    cart = await fetch_cart(user_id)
    if not cart.items:
        raise HTTPException(400, "Tu carrito está vacío")
    for item in cart.items:
        if await _user_owns(user_id, item.product_id):
            raise HTTPException(
                409,
                f"Ya posees '{item.game_name}'. Elimínalo del carrito antes de pagar.",
            )
        if item.unit_price > 0 and item.unit_price < 0.01:
            raise HTTPException(400, "Precio inválido en el carrito")
    return cart


async def _apply_coupon(user_id: str, code: str | None, subtotal: float):
    if not code or not code.strip():
        return None, 0.0, subtotal
    try:
        coupon = await validate_coupon(code, subtotal, user_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    final = round(max(0.0, subtotal - coupon.discount_applied), 2)
    return coupon, coupon.discount_applied, final


async def _redeem_if_needed(coupon, user_id: str, order_id: str) -> None:
    if not coupon:
        return
    await redeem_coupon(
        coupon.code,
        user_id,
        order_id,
        coupon.discount_applied,
        coupon.uses_count,
        coupon.discount_type,
        coupon.discount_value,
        coupon.max_uses,
        coupon.valid_from,
        coupon.valid_until,
    )


@router.post("", response_model=CheckoutResponseDTO)
async def checkout(
    body: CheckoutRequestDTO | None = None,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    req = body or CheckoutRequestDTO()
    cart = await _validate_cart(user_id)

    coupon, coupon_discount, final_total = await _apply_coupon(
        user_id, req.coupon_code, cart.total
    )

    method = (req.payment_method or "auto").lower()
    if method == "auto":
        if STRIPE_SECRET:
            method = "stripe"
        else:
            method = "sandbox"

    cart_key = hashlib.sha256(
        "|".join(sorted(f"{i.product_id}:{i.quantity}" for i in cart.items)).encode()
    ).hexdigest()[:16]
    coupon_part = (coupon.code if coupon else "none")
    idempotency_key = f"checkout_{user_id}_{cart_key}_{coupon_part}_{method}"

    dup = await pinot_query(
        f"SELECT payment_id FROM fact_payments "
        f"WHERE idempotency_key = '{esc(idempotency_key)}' AND status = 'completed' LIMIT 1"
    )
    if dup:
        raise HTTPException(409, "Esta orden ya fue procesada")

    order_id = new_id()
    payment_id = new_id()

    # ── Wallet ──────────────────────────────────────────────────────────────
    if method == "wallet":
        bal = await get_balance(user_id)
        if bal < final_total:
            raise HTTPException(
                402,
                f"Saldo insuficiente. Tienes ${bal:.2f} y el total es ${final_total:.2f}.",
            )
        await create_pending_order(
            user_id, cart, order_id, payment_id, idempotency_key,
            total=final_total, provider="wallet",
        )
        try:
            new_bal, _ = await apply_transaction(
                user_id,
                -final_total,
                tx_type="purchase",
                reference_id=order_id,
                idempotency_key=f"wallet_pay_{order_id}",
            )
        except ValueError as exc:
            raise HTTPException(402, str(exc)) from exc

        purchase_count = await fulfill_order(
            order_id, user_id, payment_id, cart.items, provider="wallet"
        )
        await _redeem_if_needed(coupon, user_id, order_id)
        return CheckoutResponseDTO(
            order_id=order_id,
            payment_id=payment_id,
            status="success",
            total=final_total,
            message="Pago con cartera completado. Los juegos están en tu biblioteca.",
            purchases_count=purchase_count,
            coupon_code=coupon.code if coupon else None,
            coupon_discount=coupon_discount,
            payment_method="wallet",
            wallet_balance=new_bal,
        )

    # ── Stripe ──────────────────────────────────────────────────────────────
    if method == "stripe":
        if not STRIPE_SECRET:
            raise HTTPException(400, "Stripe no está configurado")
        if final_total <= 0:
            # Gratis con cupón: cumplir sin pasarela
            await create_pending_order(
                user_id, cart, order_id, payment_id, idempotency_key,
                total=0.0, provider="coupon",
            )
            purchase_count = await fulfill_order(
                order_id, user_id, payment_id, cart.items, provider="coupon"
            )
            await _redeem_if_needed(coupon, user_id, order_id)
            return CheckoutResponseDTO(
                order_id=order_id,
                payment_id=payment_id,
                status="success",
                total=0.0,
                message="Pedido gratuito con cupón. Juegos añadidos a tu biblioteca.",
                purchases_count=purchase_count,
                coupon_code=coupon.code if coupon else None,
                coupon_discount=coupon_discount,
                payment_method="coupon",
            )

        await create_pending_order(
            user_id, cart, order_id, payment_id, idempotency_key,
            total=final_total, provider="stripe",
        )
        try:
            _, checkout_url = create_stripe_session(
                order_id, payment_id, user_id, cart,
                total=final_total,
                coupon_code=coupon.code if coupon else "",
            )
        except Exception as exc:
            raise HTTPException(502, f"Error con Stripe: {exc}") from exc
        return CheckoutResponseDTO(
            order_id=order_id,
            payment_id=payment_id,
            status="pending",
            total=final_total,
            message="Redirigiendo a pasarela de pago segura...",
            purchases_count=0,
            checkout_url=checkout_url,
            coupon_code=coupon.code if coupon else None,
            coupon_discount=coupon_discount,
            payment_method="stripe",
        )

    # ── Sandbox ─────────────────────────────────────────────────────────────
    await create_pending_order(
        user_id, cart, order_id, payment_id, idempotency_key,
        total=final_total, provider="sandbox",
    )
    purchase_count = await fulfill_order(
        order_id, user_id, payment_id, cart.items, provider="sandbox"
    )
    await _redeem_if_needed(coupon, user_id, order_id)
    return CheckoutResponseDTO(
        order_id=order_id,
        payment_id=payment_id,
        status="success",
        total=final_total,
        message="Compra completada. Los juegos aparecerán en tu biblioteca en unos segundos.",
        purchases_count=purchase_count,
        checkout_url=None,
        coupon_code=coupon.code if coupon else None,
        coupon_discount=coupon_discount,
        payment_method="sandbox",
    )


@router.get("/confirm", response_model=CheckoutResponseDTO)
async def confirm_stripe_session(
    session_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    """Confirma pago tras volver de Stripe (útil sin webhook en desarrollo)."""
    _, user_id = require_token(authorization)
    if not STRIPE_SECRET:
        raise HTTPException(400, "Stripe no configurado")

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET
        session = stripe.checkout.Session.retrieve(session_id)
        meta = session.metadata or {}
        if meta.get("user_id") != user_id:
            raise HTTPException(403, "Sesión de pago no corresponde a este usuario")
        if session.payment_status != "paid":
            raise HTTPException(402, "El pago aún no está confirmado")

        order_id = meta.get("order_id", "")
        if order_id and await order_already_paid(order_id):
            return CheckoutResponseDTO(
                order_id=order_id,
                payment_id=meta.get("payment_id", ""),
                status="success",
                total=float(session.amount_total or 0) / 100,
                message="Compra ya registrada en tu biblioteca.",
                purchases_count=0,
            )

        count = await fulfill_from_stripe_session(session_id)
        coupon_code = meta.get("coupon_code") or ""
        if coupon_code and order_id:
            try:
                coupon = await validate_coupon(
                    coupon_code, float(session.amount_total or 0) / 100 + 0.01, user_id
                )
                # Si ya se usó, validate falla — ignorar
                await _redeem_if_needed(coupon, user_id, order_id)
            except Exception:
                pass

        return CheckoutResponseDTO(
            order_id=meta.get("order_id", ""),
            payment_id=meta.get("payment_id", ""),
            status="success",
            total=float(session.amount_total or 0) / 100,
            message="¡Pago confirmado! Tus juegos están en la biblioteca.",
            purchases_count=count,
            coupon_code=coupon_code or None,
            payment_method="stripe",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Error confirmando pago: {exc}") from exc


@router.post("/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_SECRET:
        raise HTTPException(400, "Stripe no configurado")

    import stripe
    stripe.api_key = STRIPE_SECRET
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        else:
            import json
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except Exception as exc:
        raise HTTPException(400, f"Webhook inválido: {exc}") from exc

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("payment_status") == "paid":
            await fulfill_from_stripe_session(session["id"])

    return {"received": True}

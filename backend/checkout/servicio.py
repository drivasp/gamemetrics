import os
import time
import uuid
from decimal import Decimal

from carrito.modelos_cart import CartDTO, CartItemDTO
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4000").rstrip("/")
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


async def order_already_paid(order_id: str) -> bool:
    rows = await pinot_query(
        f"SELECT status FROM fact_orders "
        f"WHERE order_id = '{esc(order_id)}' AND deleted = false LIMIT 1"
    )
    return bool(rows) and str(rows[0][0]).lower() == "paid"


async def create_pending_order(
    user_id: str,
    cart: CartDTO,
    order_id: str,
    payment_id: str,
    idempotency_key: str,
    total: float | None = None,
    provider: str = "sandbox",
) -> int:
    now_ms = int(time.time() * 1000)
    final_total = round(float(total if total is not None else cart.total), 2)
    currency = "USD"

    await kafka_send("fact_orders", order_id, {
        "order_id": order_id,
        "user_id": user_id,
        "total_amount": final_total,
        "currency": currency,
        "status": "pending",
        "created_at": now_ms,
        "deleted": False,
    })

    for item in cart.items:
        oi_id = uuid.uuid4().hex[:15]
        await kafka_send("fact_order_items", oi_id, {
            "order_item_id": oi_id,
            "order_id": order_id,
            "product_id": item.product_id,
            "product_slug": item.game_slug,
            "product_name": item.game_name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "created_at": now_ms,
            "deleted": False,
        })

    await kafka_send("fact_payments", payment_id, {
        "payment_id": payment_id,
        "order_id": order_id,
        "user_id": user_id,
        "amount": final_total,
        "provider": provider,
        "stripe_session_id": "",
        "idempotency_key": idempotency_key,
        "status": "pending",
        "created_at": now_ms,
        "deleted": False,
    })
    return now_ms


async def fulfill_order(
    order_id: str,
    user_id: str,
    payment_id: str,
    items: list[CartItemDTO],
    stripe_session_id: str = "",
    provider: str = "sandbox",
) -> int:
    if await order_already_paid(order_id):
        return len(items)

    now_ms = int(time.time() * 1000)
    rows = await pinot_query(
        f"SELECT total_amount, currency FROM fact_orders "
        f"WHERE order_id = '{esc(order_id)}' AND deleted = false LIMIT 1"
    )
    total = float(rows[0][0]) if rows else sum(i.line_total for i in items)
    currency = rows[0][1] if rows else "USD"

    purchase_count = 0
    for item in items:
        purchase_id = f"{user_id}_{item.product_id}"
        await kafka_send("fact_purchases", purchase_id, {
            "purchase_id": purchase_id,
            "order_id": order_id,
            "user_id": user_id,
            "product_id": item.product_id,
            "game_slug": item.game_slug,
            "game_name": item.game_name,
            "game_image": item.game_image or "",
            "amount": item.line_total,
            "purchased_at": now_ms,
            "refunded": False,
            "deleted": False,
        })
        purchase_count += 1

        await kafka_send("fact_cart", item.id, {
            "cart_item_id": item.id,
            "user_id": user_id,
            "product_id": item.product_id,
            "game_slug": item.game_slug,
            "game_name": item.game_name,
            "game_image": item.game_image or "",
            "unit_price": 0.0,
            "quantity": 0,
            "added_at": now_ms,
            "deleted": True,
        })

    await kafka_send("fact_payments", payment_id, {
        "payment_id": payment_id,
        "order_id": order_id,
        "user_id": user_id,
        "amount": total,
        "provider": provider,
        "stripe_session_id": stripe_session_id,
        "idempotency_key": f"fulfill_{order_id}",
        "status": "completed",
        "created_at": now_ms,
        "deleted": False,
    })

    await kafka_send("fact_orders", order_id, {
        "order_id": order_id,
        "user_id": user_id,
        "total_amount": total,
        "currency": currency,
        "status": "paid",
        "created_at": now_ms,
        "deleted": False,
    })
    return purchase_count


async def load_cart_items_for_order(order_id: str, user_id: str) -> list[CartItemDTO]:
    rows = await pinot_query(
        f"SELECT order_item_id, product_id, product_slug, product_name, "
        f"unit_price, quantity FROM fact_order_items "
        f"WHERE order_id = '{esc(order_id)}' AND deleted = false LIMIT 50"
    )
    if not rows:
        return []

    items: list[CartItemDTO] = []
    for r in rows:
        product_id = r[1]
        slug = r[2]
        cid = f"{user_id}_{product_id}"
        img_rows = await pinot_query(
            f"SELECT game_image FROM fact_cart "
            f"WHERE cart_item_id = '{esc(cid)}' LIMIT 1"
        )
        image = img_rows[0][0] if img_rows else None
        qty = int(r[5] or 1)
        price = float(r[4] or 0)
        items.append(
            CartItemDTO(
                id=cid,
                product_id=product_id,
                game_slug=slug or "",
                game_name=r[3] or "",
                game_image=image,
                unit_price=price,
                quantity=qty,
                line_total=round(price * qty, 2),
            )
        )
    return items


def create_stripe_session(
    order_id: str,
    payment_id: str,
    user_id: str,
    cart: CartDTO,
    total: float | None = None,
    coupon_code: str = "",
) -> tuple[str, str]:
    import stripe

    stripe.api_key = STRIPE_SECRET
    final_total = round(float(total if total is not None else cart.total), 2)
    # Una línea con el total final (incluye cupón) para que Stripe cobre el monto correcto
    cents = max(50, int(round(Decimal(str(final_total)) * 100)))  # mínimo Stripe $0.50
    label = f"Pedido GameMetrics ({len(cart.items)} artículo(s))"
    if coupon_code:
        label += f" · cupón {coupon_code}"

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": label},
                "unit_amount": cents,
            },
            "quantity": 1,
        }],
        success_url=f"{FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/my-cart",
        metadata={
            "order_id": order_id,
            "payment_id": payment_id,
            "user_id": user_id,
            "coupon_code": coupon_code or "",
        },
    )
    return session.id, session.url or ""


async def fulfill_from_stripe_session(session_id: str) -> int:
    import stripe

    stripe.api_key = STRIPE_SECRET
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != "paid":
        return 0

    meta = session.metadata or {}
    order_id = meta.get("order_id", "")
    payment_id = meta.get("payment_id", "")
    user_id = meta.get("user_id", "")
    if not order_id or not user_id or not payment_id:
        return 0

    items = await load_cart_items_for_order(order_id, user_id)
    if not items:
        from carrito.servicio import fetch_cart
        cart = await fetch_cart(user_id)
        items = cart.items

    return await fulfill_order(
        order_id, user_id, payment_id, items,
        stripe_session_id=session_id,
        provider="stripe",
    )

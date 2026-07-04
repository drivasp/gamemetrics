import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from cart.modelos_cart import CartItemDTO, CartDTO, AddCartItemDTO
from cart.precio_item import resolve_item_price
from cart.servicio import fetch_cart
from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

router = APIRouter(prefix="/cart", tags=["cart"])


async def _owned(user_id: str, product_id: str) -> bool:
    rows = await pinot_query(
        f"SELECT purchase_id FROM fact_purchases "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false AND refunded = false LIMIT 1"
    )
    return len(rows) > 0


@router.get("/check/{product_id}")
async def check_cart(
    product_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    cid = f"{user_id}_{product_id}"
    rows = await pinot_query(
        f"SELECT cart_item_id FROM fact_cart WHERE cart_item_id = '{esc(cid)}' "
        f"AND deleted = false LIMIT 1"
    )
    return {"in_cart": len(rows) > 0}


@router.get("", response_model=CartDTO)
async def get_cart(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    return await fetch_cart(user_id)


@router.post("/items", response_model=CartItemDTO, status_code=201)
async def add_to_cart(
    body: AddCartItemDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if await _owned(user_id, body.product_id):
        raise HTTPException(409, "Ya posees este juego en tu biblioteca")

    cid = f"{user_id}_{body.product_id}"
    existing = await pinot_query(
        f"SELECT cart_item_id FROM fact_cart WHERE cart_item_id = '{esc(cid)}' "
        f"AND deleted = false LIMIT 1"
    )
    if existing:
        raise HTTPException(409, "El juego ya está en tu carrito")

    final_price, _, _ = await resolve_item_price(body.product_id, body.game_slug)
    if abs(body.unit_price - final_price) > 0.02:
        raise HTTPException(
            400,
            f"Precio desactualizado. El precio actual es ${final_price:.2f}",
        )

    now_ms = int(time.time() * 1000)
    await kafka_send("fact_cart", cid, {
        "cart_item_id": cid,
        "user_id": user_id,
        "product_id": body.product_id,
        "game_slug": body.game_slug,
        "game_name": body.game_name,
        "game_image": body.game_image or "",
        "unit_price": final_price,
        "quantity": body.quantity,
        "added_at": now_ms,
        "deleted": False,
    })
    return CartItemDTO(
        id=cid,
        product_id=body.product_id,
        game_slug=body.game_slug,
        game_name=body.game_name,
        game_image=body.game_image,
        unit_price=final_price,
        quantity=body.quantity,
        line_total=round(final_price * body.quantity, 2),
    )


@router.delete("/items/{product_id}", status_code=204)
async def remove_from_cart(
    product_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    cid = f"{user_id}_{product_id}"
    rows = await pinot_query(
        f"SELECT game_slug, game_name, game_image FROM fact_cart "
        f"WHERE cart_item_id = '{esc(cid)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "No encontrado en el carrito")

    slug, name, image = rows[0]
    await kafka_send("fact_cart", cid, {
        "cart_item_id": cid,
        "user_id": user_id,
        "product_id": product_id,
        "game_slug": slug or "",
        "game_name": name or "",
        "game_image": image or "",
        "unit_price": 0.0,
        "quantity": 0,
        "added_at": int(time.time() * 1000),
        "deleted": True,
    })


@router.delete("", status_code=204)
async def clear_cart(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    cart = await fetch_cart(user_id)
    now_ms = int(time.time() * 1000)
    for item in cart.items:
        cid = item.id
        await kafka_send("fact_cart", cid, {
            "cart_item_id": cid,
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

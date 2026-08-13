from carrito.modelos_cart import CartDTO, CartItemDTO
from carrito.precio_item import resolve_item_price
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.region_tax import compute_tax, get_locale
from tienda.imagen_juego import placeholder_image


async def fetch_cart(user_id: str, region: str = "US", country_code: str = "US") -> CartDTO:
    loc = get_locale(country_code)
    region = region or loc.pricing_region
    rows = await pinot_query(
        f"SELECT cart_item_id, product_id, game_slug, game_name, game_image, "
        f"unit_price, quantity FROM fact_cart "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false "
        f"ORDER BY added_at DESC LIMIT 100"
    )
    items: list[CartItemDTO] = []
    subtotal = 0.0
    discount_total = 0.0

    for r in rows:
        qty = int(r[6] or 1)
        final, base, _discount = await resolve_item_price(r[1], r[2], region=region)
        line = round(final * qty, 2)
        line_base = round(base * qty, 2)
        subtotal += line_base
        discount_total += round(line_base - line, 2)
        items.append(
            CartItemDTO(
                id=r[0],
                product_id=r[1],
                game_slug=r[2],
                game_name=r[3],
                game_image=r[4] or placeholder_image(r[3] or "", r[2] or ""),
                unit_price=final,
                quantity=qty,
                line_total=line,
            )
        )

    subtotal = round(subtotal, 2)
    discount_total = round(discount_total, 2)
    merchandise_total = round(sum(i.line_total for i in items), 2)
    tax = compute_tax(merchandise_total, country_code)
    return CartDTO(
        items=items,
        subtotal=subtotal,
        discount_total=discount_total,
        total=merchandise_total,
        item_count=sum(i.quantity for i in items),
        currency=loc.currency,
        country_code=loc.country_code,
        pricing_region=loc.pricing_region,
        tax_name=loc.tax_name,
        tax_rate_pct=loc.tax_rate_pct,
        tax_amount=tax["tax_amount"],
        total_with_tax=tax["total_with_tax"],
    )

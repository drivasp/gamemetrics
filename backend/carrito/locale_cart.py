"""Helpers de carrito con región / impuestos del usuario."""
from carrito.servicio import fetch_cart
from regional.router import get_user_country
from shared.region_tax import get_locale


async def fetch_user_cart(user_id: str):
    country = await get_user_country(user_id)
    loc = get_locale(country)
    return await fetch_cart(
        user_id,
        region=loc.pricing_region,
        country_code=loc.country_code,
    )

import asyncio

from shared.modelos import VideoGameDTO
from tienda.cliente_rawg import get_media
from tienda.imagen_juego import cover_proxy_url, placeholder_image
from tienda.modelos_store import StoreGameDTO, GameMediaDTO
from tienda.precio import calc_price, resolve_price


async def to_store_async(
    g: VideoGameDTO,
    bg: str | None = None,
    region: str = "US",
    trailer: str | None = None,
    currency: str = "USD",
    *,
    fast: bool = False,
) -> StoreGameDTO:
    if fast:
        price = calc_price(g.rating, g.metacritic)
        base, discount = price, 0.0
    else:
        price, base, discount = await resolve_price(g.id, g.rating, g.metacritic, region)
    cover = bg or placeholder_image(g.name, g.slug)
    return StoreGameDTO(
        id=g.id,
        product_id=g.id,
        slug=g.slug,
        name=g.name,
        released=g.released,
        rating=g.rating,
        metacritic=g.metacritic,
        genres=g.genres,
        platforms=g.platforms,
        developers=g.developers,
        publishers=g.publishers,
        esrb_rating=g.esrbRating,
        price=price,
        original_price=base if discount > 0 else None,
        discount_pct=discount,
        is_free=(price == 0.0),
        background_image=cover,
        trailer_url=trailer,
        currency=currency,
        pricing_region=region,
    )


def to_store(g: VideoGameDTO, bg: str | None = None) -> StoreGameDTO:
    price = calc_price(g.rating, g.metacritic)
    cover = bg or placeholder_image(g.name, g.slug)
    return StoreGameDTO(
        id=g.id,
        product_id=g.id,
        slug=g.slug,
        name=g.name,
        released=g.released,
        rating=g.rating,
        metacritic=g.metacritic,
        genres=g.genres,
        platforms=g.platforms,
        developers=g.developers,
        publishers=g.publishers,
        esrb_rating=g.esrbRating,
        price=price,
        is_free=(price == 0.0),
        background_image=cover,
    )


async def enrich(
    games: list[VideoGameDTO],
    region: str = "US",
    *,
    currency: str = "USD",
    with_media: bool = False,
) -> list[StoreGameDTO]:
    """
    Enriquece juegos con precio + URL de portada lazy (/store/cover/…).
    La tienda responde rápido; cada <img> llama RAWG vía el proxy de portadas.
    """
    if not games:
        return []

    covers = [cover_proxy_url(g.name, g.slug) for g in games]
    media_list = [GameMediaDTO() for _ in games]
    if with_media:
        media_list = await asyncio.gather(*[get_media(g.slug) for g in games])

    return list(await asyncio.gather(*[
        to_store_async(
            g,
            covers[i],
            region,
            media_list[i].trailer_url,
            currency=currency,
            fast=True,
        )
        for i, g in enumerate(games)
    ]))

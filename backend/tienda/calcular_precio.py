import asyncio

from shared.modelos import VideoGameDTO
from tienda.cliente_rawg import get_media
from tienda.imagen_juego import placeholder_image, resolve_cover
from tienda.modelos_store import StoreGameDTO, GameMediaDTO
from tienda.precio import calc_price, resolve_price


async def to_store_async(
    g: VideoGameDTO, bg: str | None = None, region: str = "US", trailer: str | None = None,
) -> StoreGameDTO:
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
    with_media: bool = False,
) -> list[StoreGameDTO]:
    """Enriquece juegos con portada (RAWG si hay API key, si no placeholder SVG local)."""
    if not games:
        return []

    covers = await asyncio.gather(*[resolve_cover(g.slug, g.name) for g in games])
    if with_media:
        media_list = await asyncio.gather(*[get_media(g.slug) for g in games])
    else:
        media_list = [GameMediaDTO() for _ in games]

    return list(await asyncio.gather(*[
        to_store_async(
            g,
            covers[i] or placeholder_image(g.name, g.slug),
            region,
            media_list[i].trailer_url,
        )
        for i, g in enumerate(games)
    ]))

import asyncio
import urllib.parse

from shared.modelos import VideoGameDTO
from store.cliente_rawg import get_media
from store.modelos_store import StoreGameDTO, GameMediaDTO


def calc_price(rating: float, metacritic: float) -> float:
    if rating == 0.0 and metacritic == 0.0:
        return 0.0
    price = round((rating * 8) + (metacritic * 0.4), 2)
    return round(max(1.99, price), 2)


def placeholder_image(name: str) -> str:
    encoded = urllib.parse.quote(name[:25], safe="")
    return f"https://via.placeholder.com/600x400/1a1a2e/e94560?text={encoded}"


async def to_store_async(
    g: VideoGameDTO, bg: str | None = None, region: str = "US", trailer: str | None = None,
) -> StoreGameDTO:
    from store.precio import resolve_price
    price, base, discount = await resolve_price(g.id, g.rating, g.metacritic, region)
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
        background_image=bg,
        trailer_url=trailer,
    )


def to_store(g: VideoGameDTO, bg: str | None = None) -> StoreGameDTO:
    price = calc_price(g.rating, g.metacritic)
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
        background_image=bg,
    )


async def enrich(
    games: list[VideoGameDTO],
    region: str = "US",
    *,
    with_media: bool = False,
) -> list[StoreGameDTO]:
    """Enriquece juegos. with_media=True solo para carrusel (RAWG es lento)."""
    if not games:
        return []

    if with_media:
        media_list = await asyncio.gather(*[get_media(g.slug) for g in games])
    else:
        media_list = [GameMediaDTO() for _ in games]

    return list(await asyncio.gather(*[
        to_store_async(
            g,
            m.background_image or placeholder_image(g.name),
            region,
            m.trailer_url,
        )
        for g, m in zip(games, media_list)
    ]))

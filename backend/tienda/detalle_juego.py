import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException

from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.helpers_filas import map_game
from shared.request_locale import resolve_request_locale
from tienda.calcular_precio import to_store_async
from tienda.cliente_rawg import get_media
from tienda.imagen_juego import resolve_cover
from tienda.precio import resolve_price
from tienda.modelos_store import StoreGameDetailDTO

router = APIRouter()


@router.get("/games/{slug}", response_model=StoreGameDetailDTO)
async def store_game_by_slug(
    slug: str,
    country: str | None = None,
    authorization: Annotated[str | None, Header()] = None,
):
    loc = await resolve_request_locale(authorization, country)
    region = loc["pricing_region"]
    currency = loc["currency"]

    safe_slug = slug.replace("'", "''")
    sql = (
        f"SELECT {GAME_COLUMNS} FROM {TABLE} "
        f"WHERE slug = '{safe_slug}' AND semana = 1 LIMIT 1"
    )
    rows = await pinot_query(sql)
    if not rows:
        raise HTTPException(status_code=404, detail="Game not found")
    base = map_game(rows[0])

    first_genre = base.genres.split("||")[0].strip() if base.genres else ""
    similar_sql = ""
    if first_genre:
        sg = first_genre.replace("'", "''")
        similar_sql = (
            f"SELECT {GAME_COLUMNS} FROM {TABLE} "
            f"WHERE genres LIKE '%{sg}%' AND slug != '{safe_slug}' "
            f"AND semana = 1 ORDER BY rating DESC LIMIT 4"
        )

    tasks: list[Any] = [resolve_cover(slug, base.name)]
    if similar_sql:
        tasks.append(pinot_query(similar_sql))

    results = await asyncio.gather(*tasks)
    bg: str = results[0]
    similar_rows: list = results[1] if len(results) > 1 else []

    media = await get_media(slug)

    similar_games = []
    for sr in similar_rows:
        sg = map_game(sr)
        cover = await resolve_cover(sg.slug, sg.name)
        similar_games.append(
            await to_store_async(sg, cover, region=region, currency=currency)
        )

    price, original, discount = await resolve_price(
        base.id, base.rating, base.metacritic, region=region
    )
    return StoreGameDetailDTO(
        id=base.id, product_id=base.id, slug=base.slug, name=base.name,
        released=base.released,
        rating=base.rating, metacritic=base.metacritic, genres=base.genres,
        platforms=base.platforms, developers=base.developers,
        publishers=base.publishers, esrb_rating=base.esrbRating,
        price=price, original_price=original if discount > 0 else None,
        discount_pct=discount, is_free=(price == 0.0), background_image=bg,
        currency=currency, pricing_region=region, country_code=loc["country_code"],
        description=media.description, screenshots=media.screenshots,
        trailer_url=media.trailer_url,
        similar=similar_games,
    )

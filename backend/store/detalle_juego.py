import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.helpers_filas import map_game
from store.calcular_precio import placeholder_image, to_store_async
from store.precio import resolve_price
from store.cliente_rawg import get_media
from store.modelos_store import StoreGameDetailDTO, GameMediaDTO

router = APIRouter()


# ⚠ Generic slug route must be LAST — placed after all /store/games/* specifics
@router.get("/games/{slug}", response_model=StoreGameDetailDTO)
async def store_game_by_slug(slug: str):
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

    tasks: list[Any] = [get_media(slug)]
    if similar_sql:
        tasks.append(pinot_query(similar_sql))

    results = await asyncio.gather(*tasks)
    media: GameMediaDTO = results[0]
    similar_rows: list = results[1] if len(results) > 1 else []

    bg = media.background_image or placeholder_image(base.name)
    similar_games = []
    for sr in similar_rows:
        sg = map_game(sr)
        similar_games.append(
            await to_store_async(sg, placeholder_image(sg.name))
        )

    price, original, discount = await resolve_price(base.id, base.rating, base.metacritic)
    return StoreGameDetailDTO(
        id=base.id, product_id=base.id, slug=base.slug, name=base.name, released=base.released,
        rating=base.rating, metacritic=base.metacritic, genres=base.genres,
        platforms=base.platforms, developers=base.developers,
        publishers=base.publishers, esrb_rating=base.esrbRating,
        price=price, original_price=original if discount > 0 else None,
        discount_pct=discount, is_free=(price == 0.0), background_image=bg,
        description=media.description, screenshots=media.screenshots,
        trailer_url=media.trailer_url,
        similar=similar_games,
    )

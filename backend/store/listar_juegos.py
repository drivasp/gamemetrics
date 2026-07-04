import asyncio

from fastapi import APIRouter

from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.helpers_filas import _int, map_game
from store.calcular_precio import enrich
from store.modelos_store import StorePageDTO

router = APIRouter()

_ORDER_MAP: dict[str, str] = {
    "rating":     "rating DESC",
    "metacritic": "metacritic DESC",
    "released":   "released_ts DESC",
    "name":       "name ASC",
    "price_asc":  "rating ASC, metacritic ASC",
    "price_desc": "rating DESC, metacritic DESC",
}


def _store_where(
    semana: int, genre: str, platform: str, search: str, price_filter: str
) -> str:
    q = lambda s: s.replace("'", "''")
    conds = [f"semana <= {semana}"]
    if genre:
        conds.append(f"genres LIKE '%{q(genre)}%'")
    if platform:
        conds.append(f"platforms LIKE '%{q(platform)}%'")
    if search:
        conds.append(f"name LIKE '%{q(search)}%'")
    if price_filter == "free":
        conds.append("rating = 0 AND metacritic = 0")
    elif price_filter == "paid":
        conds.append("(rating > 0 OR metacritic > 0)")
    return " AND ".join(conds)


@router.get("/games", response_model=StorePageDTO)
async def store_games(
    page: int = 0,
    size: int = 24,
    semana: int = 17,
    genre: str = "",
    platform: str = "",
    search: str = "",
    order_by: str = "rating",
    price_filter: str = "",
):
    where = _store_where(semana, genre, platform, search, price_filter)
    order = _ORDER_MAP.get(order_by, "rating DESC")
    offset = page * size
    sql = (
        f"SELECT {GAME_COLUMNS} FROM {TABLE} "
        f"WHERE {where} ORDER BY {order} LIMIT {size} OFFSET {offset}"
    )
    rows, count_rows = await asyncio.gather(
        pinot_query(sql),
        pinot_query(f"SELECT COUNT(*) FROM {TABLE} WHERE {where}"),
    )
    enriched = await enrich([map_game(r) for r in rows])
    total = _int(count_rows[0], 0) if count_rows else 0
    return StorePageDTO(games=enriched, total=total, page=page, size=size)

from fastapi import APIRouter

from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.helpers_filas import map_game
from store.calcular_precio import enrich
from store.modelos_store import StoreGameDTO

router = APIRouter()


@router.get("/new-releases", response_model=list[StoreGameDTO])
async def store_new_releases(semana: int = 17):
    sql = (
        f"SELECT {GAME_COLUMNS} FROM {TABLE} "
        f"WHERE semana <= {semana} AND released_ts > 0 "
        f"ORDER BY released_ts DESC LIMIT 12"
    )
    return await enrich([map_game(r) for r in await pinot_query(sql)])

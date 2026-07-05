from fastapi import APIRouter

from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.modelos import VideoGameDTO
from shared.helpers_filas import map_game

router = APIRouter()


@router.get("/top-rated", response_model=list[VideoGameDTO])
async def top_rated(semana: int = 1):
    sql = (
        f"SELECT {GAME_COLUMNS} FROM {TABLE} "
        f"WHERE semana = {semana} ORDER BY rating DESC LIMIT 10"
    )
    return [map_game(r) for r in await pinot_query(sql)]

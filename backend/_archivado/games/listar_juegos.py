from fastapi import APIRouter

from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.modelos import VideoGameDTO
from shared.helpers_filas import map_game

router = APIRouter()


@router.get("/", response_model=list[VideoGameDTO])
async def listar_juegos(page: int = 0, size: int = 20, semana: int = 1):
    offset = page * size
    sql = (
        f"SELECT {GAME_COLUMNS} FROM {TABLE} "
        f"WHERE semana = {semana} LIMIT {size} OFFSET {offset}"
    )
    return [map_game(r) for r in await pinot_query(sql)]

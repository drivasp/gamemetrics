from fastapi import APIRouter, HTTPException

from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.modelos import VideoGameDTO
from shared.helpers_filas import map_game

router = APIRouter()


@router.get("/{id}", response_model=VideoGameDTO)
async def obtener_juego(id: str):
    safe_id = id.replace("'", "''")
    sql = (
        f"SELECT {GAME_COLUMNS} FROM {TABLE} "
        f"WHERE id = '{safe_id}' AND semana = 1 LIMIT 1"
    )
    rows = await pinot_query(sql)
    if not rows:
        raise HTTPException(status_code=404, detail="Game not found")
    return map_game(rows[0])

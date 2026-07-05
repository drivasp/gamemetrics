from fastapi import APIRouter

from shared.cliente_pinot import pinot_query, TABLE
from shared.helpers_filas import _int

router = APIRouter()


@router.get("/count")
async def contar_juegos(semana: int = 17):
    rows = await pinot_query(
        f"SELECT COUNT(*) FROM {TABLE} WHERE semana <= {semana}"
    )
    return {"count": _int(rows[0], 0) if rows else 0}

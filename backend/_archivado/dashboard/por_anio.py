from fastapi import APIRouter

from shared.cliente_pinot import pinot_query, TABLE
from shared.modelos import CountDTO
from shared.helpers_filas import _str, _int

router = APIRouter()


@router.get("/by-year", response_model=list[CountDTO])
async def por_anio(semana: int = 17):
    sql = (
        f"SELECT YEAR(released_ts * 1000) AS anio, COUNT(*) AS total "
        f"FROM {TABLE} "
        f"WHERE released_ts > 0 AND semana <= {semana} "
        f"GROUP BY anio ORDER BY anio"
    )
    rows = await pinot_query(sql)
    return [CountDTO(label=_str(r, 0), count=_int(r, 1)) for r in rows]

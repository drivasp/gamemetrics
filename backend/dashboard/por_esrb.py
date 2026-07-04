from fastapi import APIRouter

from shared.cliente_pinot import pinot_query, TABLE
from shared.modelos import CountDTO
from shared.helpers_filas import _str, _int

router = APIRouter()


@router.get("/by-esrb", response_model=list[CountDTO])
async def por_esrb(semana: int = 17):
    sql = (
        f"SELECT esrb_rating, COUNT(*) AS cnt "
        f"FROM {TABLE} "
        f"WHERE esrb_rating != '' AND semana <= {semana} "
        f"GROUP BY esrb_rating ORDER BY cnt DESC"
    )
    rows = await pinot_query(sql)
    return [CountDTO(label=_str(r, 0), count=_int(r, 1)) for r in rows]

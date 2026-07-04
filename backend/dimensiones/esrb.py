from fastapi import APIRouter

from shared.cliente_pinot import pinot_query
from shared.modelos import DimRecordDTO
from shared.helpers_filas import _int, _str, count_table

router = APIRouter()


@router.get("/esrb", response_model=list[DimRecordDTO])
async def get_esrb(page: int = 0, size: int = 50):
    sql = (
        f"SELECT dim_id, nombre, codigo, edad_minima FROM dim_esrb "
        f"ORDER BY edad_minima LIMIT {size} OFFSET {page * size}"
    )
    rows = await pinot_query(sql)
    return [
        DimRecordDTO(dimId=_int(r, 0), nombre=_str(r, 1), codigo=_str(r, 2), edadMinima=_int(r, 3))
        for r in rows
    ]


@router.get("/esrb/count")
async def contar_esrb():
    return {"count": await count_table("dim_esrb")}

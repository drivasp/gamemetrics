from fastapi import APIRouter

from shared.cliente_pinot import pinot_query
from shared.modelos import DimRecordDTO
from shared.helpers_filas import _int, _str, count_table

router = APIRouter()


@router.get("/publicadores", response_model=list[DimRecordDTO])
async def get_publicadores(page: int = 0, size: int = 500):
    sql = f"SELECT dim_id, nombre FROM dim_publicadores ORDER BY nombre LIMIT {size} OFFSET {page * size}"
    return [DimRecordDTO(dimId=_int(r, 0), nombre=_str(r, 1)) for r in await pinot_query(sql)]


@router.get("/publicadores/count")
async def contar_publicadores():
    return {"count": await count_table("dim_publicadores")}

from fastapi import APIRouter

from shared.modelos import CountDTO
from shared.helpers_filas import count_by_split_field

router = APIRouter()


@router.get("/by-platform", response_model=list[CountDTO])
async def por_plataforma(semana: int = 17):
    return await count_by_split_field("platforms", semana)

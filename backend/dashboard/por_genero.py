from fastapi import APIRouter

from shared.modelos import CountDTO
from shared.helpers_filas import count_by_split_field

router = APIRouter()


@router.get("/by-genre", response_model=list[CountDTO])
async def por_genero(semana: int = 17):
    return await count_by_split_field("genres", semana)

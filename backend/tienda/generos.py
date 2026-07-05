from fastapi import APIRouter

from shared.helpers_filas import count_by_split_field
from shared.modelos import CountDTO

router = APIRouter()


@router.get("/genres", response_model=list[CountDTO])
async def store_genres(semana: int = 17):
    return await count_by_split_field("genres", semana)

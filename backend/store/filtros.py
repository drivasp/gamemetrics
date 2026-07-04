import asyncio

from fastapi import APIRouter

from shared.helpers_filas import count_by_split_field

router = APIRouter()


@router.get("/filters")
async def store_filters(semana: int = 17):
    genres, platforms = await asyncio.gather(
        count_by_split_field("genres", semana),
        count_by_split_field("platforms", semana),
    )
    return {
        "genres": [g.label for g in genres],
        "platforms": [p.label for p in platforms[:60]],
    }

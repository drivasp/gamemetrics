from typing import Annotated

from fastapi import APIRouter, Header

from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.helpers_filas import map_game
from shared.request_locale import resolve_request_locale
from tienda.calcular_precio import enrich
from tienda.modelos_store import StoreGameDTO

router = APIRouter()


@router.get("/popular", response_model=list[StoreGameDTO])
async def store_popular(
    semana: int = 17,
    country: str | None = None,
    authorization: Annotated[str | None, Header()] = None,
):
    loc = await resolve_request_locale(authorization, country)
    sql = (
        f"SELECT {GAME_COLUMNS} FROM {TABLE} "
        f"WHERE semana <= {semana} AND rating > 0 "
        f"ORDER BY rating DESC LIMIT 20"
    )
    return await enrich(
        [map_game(r) for r in await pinot_query(sql)],
        region=loc["pricing_region"],
        currency=loc["currency"],
    )

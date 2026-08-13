from typing import Annotated

from fastapi import APIRouter, Header

from checkout.saas_billing import list_active_featured_product_ids
from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query, TABLE, GAME_COLUMNS
from shared.helpers_filas import map_game
from shared.request_locale import resolve_request_locale
from tienda.calcular_precio import enrich
from tienda.modelos_store import StoreGameDTO

router = APIRouter()


@router.get("/featured", response_model=list[StoreGameDTO])
async def store_featured(
    semana: int = 17,
    country: str | None = None,
    authorization: Annotated[str | None, Header()] = None,
):
    """
    Destacados = placements de pago activos (SaaS Fase 4) + editorial metacritic.
    Los pagados van primero (como Steam featured / promoted).
    """
    loc = await resolve_request_locale(authorization, country)
    paid_ids = await list_active_featured_product_ids(6)
    mapped = []
    seen: set[str] = set()

    for product_id in paid_ids:
        rows = await pinot_query(
            f"SELECT {GAME_COLUMNS} FROM {TABLE} "
            f"WHERE id = '{esc(product_id)}' AND semana <= {semana} "
            f"ORDER BY semana DESC LIMIT 1"
        )
        if rows:
            g = map_game(rows[0])
            if g.id not in seen:
                seen.add(g.id)
                mapped.append(g)

    sql = (
        f"SELECT {GAME_COLUMNS} FROM {TABLE} "
        f"WHERE semana <= {semana} AND metacritic > 80 AND rating > 4 "
        f"ORDER BY metacritic DESC LIMIT 8"
    )
    for r in await pinot_query(sql):
        g = map_game(r)
        if g.id and g.id not in seen:
            seen.add(g.id)
            mapped.append(g)
        if len(mapped) >= 6:
            break

    return await enrich(
        mapped[:6],
        region=loc["pricing_region"],
        currency=loc["currency"],
        with_media=False,
    )

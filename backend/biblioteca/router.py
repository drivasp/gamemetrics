from typing import Annotated

from fastapi import APIRouter, Header

from biblioteca.modelos_library import LibraryItemDTO
from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.pinot_utils import to_bool
from tienda.imagen_juego import placeholder_image

router = APIRouter(prefix="/library", tags=["library"])


@router.get("", response_model=list[LibraryItemDTO])
async def get_library(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT purchase_id, product_id, game_slug, game_name, game_image, "
        f"amount, purchased_at, refunded FROM fact_purchases "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false AND refunded = false "
        f"ORDER BY purchased_at DESC LIMIT 500"
    )
    return [
        LibraryItemDTO(
            purchase_id=r[0],
            product_id=r[1],
            game_slug=r[2],
            game_name=r[3],
            game_image=r[4] or placeholder_image(r[3] or "", r[2] or ""),
            amount=float(r[5]),
            purchased_at=str(r[6]),
            refunded=to_bool(r[7]),
        )
        for r in rows
    ]


@router.get("/check/{game_slug}")
async def check_owned(
    game_slug: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT purchase_id FROM fact_purchases "
        f"WHERE user_id = '{esc(user_id)}' AND game_slug = '{esc(game_slug)}' "
        f"AND deleted = false AND refunded = false LIMIT 1"
    )
    return {"owned": len(rows) > 0}

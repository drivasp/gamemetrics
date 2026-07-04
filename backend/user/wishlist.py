import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from auth.cliente_jwt import verify_token
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from user.modelos_user import WishlistItemDTO, AddWishlistDTO

router = APIRouter()


def _require_token(authorization: str | None) -> tuple[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token requerido")
    token = authorization.split(" ", 1)[1]
    try:
        payload = verify_token(token)
        user_id = payload.get("id", "")
        if not user_id:
            raise HTTPException(401, "Token inválido")
        return token, user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Token inválido o expirado")


def _esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")


# ⚠ /wishlist/check/{slug} must be registered BEFORE /wishlist/{slug}
@router.get("/wishlist/check/{game_slug}")
async def check_wishlist(
    game_slug: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = _require_token(authorization)
    wid = f"{user_id}_{_esc(game_slug)}"
    rows = await pinot_query(
        f"SELECT wishlist_id FROM fact_wishlist WHERE wishlist_id = '{wid}' LIMIT 1"
    )
    return {"in_wishlist": len(rows) > 0}


@router.get("/wishlist", response_model=list[WishlistItemDTO])
async def get_wishlist(authorization: Annotated[str | None, Header()] = None):
    _, user_id = _require_token(authorization)
    rows = await pinot_query(
        f"SELECT wishlist_id, user_id, game_slug, game_name, game_image, game_price, created_at "
        f"FROM fact_wishlist WHERE user_id = '{_esc(user_id)}' "
        f"ORDER BY created_at DESC LIMIT 500"
    )
    return [
        WishlistItemDTO(
            id=r[0],
            game_slug=r[2],
            game_name=r[3],
            game_image=r[4] or None,
            game_price=float(r[5]),
            added_at=str(r[6]),
        )
        for r in rows
    ]


@router.post("/wishlist", response_model=WishlistItemDTO, status_code=201)
async def add_to_wishlist(
    body: AddWishlistDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = _require_token(authorization)
    wid = f"{user_id}_{body.game_slug}"

    existing = await pinot_query(
        f"SELECT wishlist_id FROM fact_wishlist WHERE wishlist_id = '{_esc(wid)}' LIMIT 1"
    )
    if existing:
        raise HTTPException(409, "El juego ya está en tu wishlist")

    now_ms = int(time.time() * 1000)
    await kafka_send("fact_wishlist", wid, {
        "wishlist_id": wid,
        "user_id": user_id,
        "game_slug": body.game_slug,
        "game_name": body.game_name,
        "game_image": body.game_image or "",
        "game_price": body.game_price,
        "created_at": now_ms,
    })

    return WishlistItemDTO(
        id=wid,
        game_slug=body.game_slug,
        game_name=body.game_name,
        game_image=body.game_image or None,
        game_price=body.game_price,
        added_at=str(now_ms),
    )


@router.delete("/wishlist/{game_slug}", status_code=204)
async def remove_from_wishlist(
    game_slug: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = _require_token(authorization)
    wid = f"{user_id}_{game_slug}"

    existing = await pinot_query(
        f"SELECT wishlist_id FROM fact_wishlist WHERE wishlist_id = '{_esc(wid)}' LIMIT 1"
    )
    if not existing:
        raise HTTPException(404, "No encontrado en wishlist")

    # Send tombstone — Pinot upsert with deleteRecordColumn removes this record
    await kafka_send("fact_wishlist", wid, {
        "wishlist_id": wid,
        "user_id": user_id,
        "game_slug": game_slug,
        "game_name": "",
        "game_image": "",
        "game_price": 0.0,
        "deleted": True,
        "created_at": int(time.time() * 1000),
    })

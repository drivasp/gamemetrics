from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from auth.cliente_jwt import verify_token
from auth.modelos_auth import UpdateProfileDTO, UserDTO
from shared.auth_deps import esc, require_token
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_ms

router = APIRouter()


async def _get_user(user_id: str) -> dict | None:
    rows = await pinot_query(
        f"SELECT user_id, email, password_hash, display_name, bio, avatar, created_at "
        f"FROM fact_users WHERE user_id = '{esc(user_id)}' AND deleted = FALSE LIMIT 1"
    )
    if not rows:
        return None
    r = rows[0]
    return {
        "user_id": r[0], "email": r[1], "password_hash": r[2],
        "display_name": r[3], "bio": r[4], "avatar": r[5], "created_at": r[6],
    }


@router.get("/profile", response_model=UserDTO)
async def get_profile(authorization: Annotated[str | None, Header()] = None):
    token, user_id = require_token(authorization)
    user = await _get_user(user_id)
    if not user:
        payload = verify_token(token)
        return UserDTO(
            id=user_id,
            email=payload.get("email", ""),
            display_name=None,
            bio=None,
            avatar=None,
        )
    return UserDTO(
        id=user["user_id"],
        email=user["email"],
        display_name=user["display_name"] or None,
        bio=user["bio"] or None,
        avatar=user["avatar"] or None,
    )


@router.put("/profile", response_model=UserDTO)
async def update_profile(
    body: UpdateProfileDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    user = await _get_user(user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    new_display_name = body.display_name if body.display_name is not None else (user["display_name"] or "")
    new_bio = body.bio if body.bio is not None else (user["bio"] or "")

    await kafka_send("fact_users", user_id, {
        "user_id": user["user_id"],
        "email": user["email"],
        "password_hash": user["password_hash"],
        "display_name": new_display_name,
        "bio": new_bio,
        "avatar": user["avatar"] or "",
        "deleted": False,
        "created_at": to_ms(user["created_at"]),
    })

    return UserDTO(
        id=user_id,
        email=user["email"],
        display_name=new_display_name or None,
        bio=new_bio or None,
        avatar=user["avatar"] or None,
    )

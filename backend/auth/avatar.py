import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from auth.modelos_auth import UserDTO
from shared.auth_deps import esc, require_token
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_ms

AVATAR_DIR = Path(os.getenv("AVATAR_DIR", "/app/static/avatars"))
MAX_AVATAR_BYTES = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
router = APIRouter()


@router.post("/avatar", response_model=UserDTO)
async def upload_avatar(
    file: UploadFile = File(...),
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)

    rows = await pinot_query(
        f"SELECT user_id, email, password_hash, display_name, bio, avatar, created_at "
        f"FROM fact_users WHERE user_id = '{esc(user_id)}' AND deleted = FALSE LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Usuario no encontrado")
    row = rows[0]

    ext = Path(file.filename or "avatar.jpg").suffix.lower() or ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Formato de imagen no permitido")

    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(400, "La imagen no puede superar 2 MB")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}{ext}"
    (AVATAR_DIR / filename).write_bytes(content)

    avatar_url = f"/static/avatars/{filename}"

    await kafka_send("fact_users", user_id, {
        "user_id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "display_name": row[3] or "",
        "bio": row[4] or "",
        "avatar": avatar_url,
        "deleted": False,
        "created_at": to_ms(row[6]),
    })

    return UserDTO(
        id=user_id,
        email=row[1],
        display_name=row[3] or None,
        bio=row[4] or None,
        avatar=avatar_url,
    )

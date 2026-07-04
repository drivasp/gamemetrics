from typing import Annotated

from fastapi import Header, HTTPException

from auth.cliente_jwt import verify_token


def esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")


def require_token(authorization: str | None) -> tuple[str, str]:
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


def optional_user_id(authorization: Annotated[str | None, Header()] = None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        _, user_id = require_token(authorization)
        return user_id
    except HTTPException:
        return None

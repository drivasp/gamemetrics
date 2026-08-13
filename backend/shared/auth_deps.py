from typing import Annotated

from fastapi import Header, HTTPException

from auth.cliente_jwt import verify_token
from auth.roles import get_user_role


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


async def require_roles(
    authorization: str | None,
    *allowed: str,
) -> tuple[str, str, str]:
    """Auth + rol efectivo desde fact_user_roles (source of truth)."""
    token, user_id = require_token(authorization)
    role = await get_user_role(user_id)
    if allowed and role not in {a.lower() for a in allowed}:
        raise HTTPException(
            403,
            f"Se requiere rol: {', '.join(allowed)}. Tu rol actual: {role}",
        )
    return token, user_id, role


def optional_user_id(authorization: Annotated[str | None, Header()] = None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        _, user_id = require_token(authorization)
        return user_id
    except HTTPException:
        return None

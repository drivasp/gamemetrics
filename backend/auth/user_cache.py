"""Cache en memoria de usuarios para login/registro con lag o Pinot inestable."""
from __future__ import annotations

from typing import Any

# email_lower -> row dict
_BY_EMAIL: dict[str, dict[str, Any]] = {}
# user_id -> row dict
_BY_ID: dict[str, dict[str, Any]] = {}


def cache_user(
    *,
    user_id: str,
    email: str,
    password_hash: str,
    display_name: str = "",
    bio: str = "",
    avatar: str = "",
    created_at: int = 0,
    deleted: bool = False,
) -> None:
    email_l = (email or "").strip().lower()
    row = {
        "user_id": user_id,
        "email": email_l,
        "password_hash": password_hash,
        "display_name": display_name or "",
        "bio": bio or "",
        "avatar": avatar or "",
        "created_at": int(created_at or 0),
        "deleted": bool(deleted),
    }
    if deleted:
        _BY_EMAIL.pop(email_l, None)
        _BY_ID.pop(user_id, None)
        return
    _BY_EMAIL[email_l] = row
    _BY_ID[user_id] = row


def get_by_email(email: str) -> dict[str, Any] | None:
    row = _BY_EMAIL.get((email or "").strip().lower())
    if not row or row.get("deleted"):
        return None
    return row


def get_by_id(user_id: str) -> dict[str, Any] | None:
    row = _BY_ID.get(user_id)
    if not row or row.get("deleted"):
        return None
    return row


def list_by_email(email: str) -> list[dict[str, Any]]:
    row = get_by_email(email)
    return [row] if row else []

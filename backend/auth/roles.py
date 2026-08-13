"""Roles de cuenta — ver auth.permissions para scopes granulares."""
from __future__ import annotations

import os
import time

from auth.permissions import DEFAULT_ROLE, ROLES, normalize_role
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

ROLE_BOOTSTRAP_SECRET = os.getenv("ROLE_BOOTSTRAP_SECRET", "dev_bootstrap_roles")

# re-export
__all__ = [
    "ROLES",
    "DEFAULT_ROLE",
    "ROLE_BOOTSTRAP_SECRET",
    "normalize_role",
    "get_user_role",
    "set_user_role",
    "cache_set_role",
]


def _esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")


_ROLE_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL_S = 300.0


def cache_set_role(user_id: str, role: str) -> None:
    _ROLE_CACHE[user_id] = (normalize_role(role), time.time())


def _cache_get(user_id: str) -> str | None:
    hit = _ROLE_CACHE.get(user_id)
    if not hit:
        return None
    role, ts = hit
    if time.time() - ts > _CACHE_TTL_S:
        _ROLE_CACHE.pop(user_id, None)
        return None
    return role


async def get_user_role(user_id: str) -> str:
    cached = _cache_get(user_id)
    if cached:
        return cached
    rows = await pinot_query(
        f"SELECT role FROM fact_user_roles "
        f"WHERE user_id = '{_esc(user_id)}' AND deleted = false LIMIT 1"
    )
    if not rows or not rows[0][0]:
        return DEFAULT_ROLE
    role = normalize_role(str(rows[0][0]))
    cache_set_role(user_id, role)
    return role


async def set_user_role(user_id: str, role: str) -> str:
    role = normalize_role(role)
    now_ms = int(time.time() * 1000)
    cache_set_role(user_id, role)
    await kafka_send("fact_user_roles", user_id, {
        "user_id": user_id,
        "role": role,
        "updated_at": now_ms,
        "deleted": False,
    })
    return role

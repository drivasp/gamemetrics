"""API keys B2B para publishers."""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


async def _partner_id(user_id: str) -> str | None:
    email_rows = await pinot_query(
        f"SELECT email FROM fact_users WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    if not email_rows:
        return None
    email = email_rows[0][0]
    rows = await pinot_query(
        f"SELECT partner_id FROM fact_partner_accounts "
        f"WHERE contact_email = '{esc(email)}' AND deleted = false LIMIT 1"
    )
    return rows[0][0] if rows else None


@router.get("")
async def list_keys(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    partner_id = await _partner_id(user_id)
    if not partner_id:
        raise HTTPException(403, "Necesitas una cuenta publisher")
    rows = await pinot_query(
        f"SELECT key_id, partner_id, key_prefix, scopes, rate_limit, expires_at, created_at "
        f"FROM fact_api_keys WHERE partner_id = '{esc(partner_id)}' AND deleted = false LIMIT 20"
    )
    return {
        "items": [
            {
                "key_id": r[0],
                "key_prefix": r[2],
                "scopes": r[3],
                "rate_limit": int(r[4] or 1000),
                "expires_at": str(r[5]),
                "created_at": str(r[6]),
            }
            for r in rows
        ]
    }


@router.post("", status_code=201)
async def create_key(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    partner_id = await _partner_id(user_id)
    if not partner_id:
        raise HTTPException(403, "Necesitas una cuenta publisher")

    raw = f"gm_{secrets.token_urlsafe(24)}"
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_id = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    expires = now_ms + 365 * 24 * 3600 * 1000
    await kafka_send("fact_api_keys", key_id, {
        "key_id": key_id,
        "partner_id": partner_id,
        "key_hash": key_hash,
        "key_prefix": raw[:10] + "…",
        "scopes": "read:sales,read:games",
        "rate_limit": 1000,
        "expires_at": expires,
        "created_at": now_ms,
        "deleted": False,
    })
    return {
        "key_id": key_id,
        "api_key": raw,
        "message": "Guarda esta clave ahora. No se volverá a mostrar completa.",
    }


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    partner_id = await _partner_id(user_id)
    if not partner_id:
        raise HTTPException(403, "Necesitas una cuenta publisher")
    rows = await pinot_query(
        f"SELECT key_id, partner_id, key_hash, key_prefix, scopes, rate_limit, expires_at, created_at "
        f"FROM fact_api_keys WHERE key_id = '{esc(key_id)}' AND deleted = false LIMIT 1"
    )
    if not rows or rows[0][1] != partner_id:
        raise HTTPException(404, "Clave no encontrada")
    r = rows[0]
    await kafka_send("fact_api_keys", r[0], {
        "key_id": r[0],
        "partner_id": r[1],
        "key_hash": r[2],
        "key_prefix": r[3],
        "scopes": r[4],
        "rate_limit": int(r[5] or 0),
        "expires_at": int(r[6] or 0),
        "created_at": int(r[7]) if str(r[7]).isdigit() else int(time.time() * 1000),
        "deleted": True,
    })

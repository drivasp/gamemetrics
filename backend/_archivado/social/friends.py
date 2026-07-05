"""Amigos — solicitudes, lista, bloquear."""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from social.servicio import notify, post_activity

router = APIRouter(prefix="/friends", tags=["friends"])


class FriendRequestDTO(BaseModel):
    email: str = Field(min_length=3, max_length=200)


async def _user_by_email(email: str) -> tuple[str, str] | None:
    rows = await pinot_query(
        f"SELECT user_id, display_name FROM fact_users "
        f"WHERE email = '{esc(email.strip().lower())}' AND deleted = false LIMIT 1"
    )
    if not rows:
        return None
    return str(rows[0][0]), (rows[0][1] or email)


async def _user_meta(user_id: str) -> dict:
    rows = await pinot_query(
        f"SELECT user_id, email, display_name, avatar FROM fact_users "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        return {"user_id": user_id, "email": "", "display_name": "Usuario", "avatar": None}
    return {
        "user_id": rows[0][0],
        "email": rows[0][1] or "",
        "display_name": rows[0][2] or rows[0][1] or "Usuario",
        "avatar": rows[0][3] or None,
    }


@router.get("")
async def list_friends(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    uid = esc(user_id)
    rows = await pinot_query(
        f"SELECT friendship_id, user_id, friend_id, status, created_at "
        f"FROM fact_friendships WHERE (user_id = '{uid}' OR friend_id = '{uid}') "
        f"AND deleted = false LIMIT 200"
    )
    friends, incoming, outgoing = [], [], []
    for fid, a, b, status, created in rows:
        status = str(status or "")
        other = b if a == user_id else a
        meta = await _user_meta(other)
        item = {
            "friendship_id": fid,
            "status": status,
            "created_at": str(created),
            "user": meta,
        }
        if status == "accepted":
            friends.append(item)
        elif status == "pending":
            if b == user_id:
                incoming.append(item)
            else:
                outgoing.append(item)
    return {"friends": friends, "incoming": incoming, "outgoing": outgoing}


@router.post("/request")
async def send_request(
    body: FriendRequestDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    found = await _user_by_email(body.email)
    if not found:
        raise HTTPException(404, "No hay ninguna cuenta con ese correo")
    friend_id, friend_name = found
    if friend_id == user_id:
        raise HTTPException(400, "No puedes agregarte a ti mismo")

    # ¿ya existe relación?
    rows = await pinot_query(
        f"SELECT friendship_id, user_id, friend_id, status FROM fact_friendships "
        f"WHERE deleted = false AND ("
        f"(user_id = '{esc(user_id)}' AND friend_id = '{esc(friend_id)}') OR "
        f"(user_id = '{esc(friend_id)}' AND friend_id = '{esc(user_id)}')"
        f") LIMIT 5"
    )
    for r in rows:
        st = str(r[3] or "")
        if st == "accepted":
            raise HTTPException(409, "Ya son amigos")
        if st == "pending":
            raise HTTPException(409, "Ya hay una solicitud pendiente")
        if st == "blocked":
            raise HTTPException(403, "No se puede enviar solicitud")

    me = await _user_meta(user_id)
    fid = f"f_{user_id}_{friend_id}"
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_friendships", fid, {
        "friendship_id": fid,
        "user_id": user_id,
        "friend_id": friend_id,
        "status": "pending",
        "created_at": now_ms,
        "deleted": False,
    })
    await notify(
        friend_id, "friend_request",
        "Nueva solicitud de amistad",
        f"{me['display_name']} quiere ser tu amigo en GameMetrics.",
    )
    await post_activity(user_id, "friend_request", f"Envió solicitud a {friend_name}", friend_id)
    return {"friendship_id": fid, "status": "pending", "message": "Solicitud enviada"}


@router.post("/{friendship_id}/accept")
async def accept_friend(
    friendship_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT friendship_id, user_id, friend_id, status, created_at FROM fact_friendships "
        f"WHERE friendship_id = '{esc(friendship_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Solicitud no encontrada")
    fid, sender, recipient, status, created = rows[0]
    if recipient != user_id:
        raise HTTPException(403, "Esta solicitud no es para ti")
    if status != "pending":
        raise HTTPException(409, f"Estado actual: {status}")

    now_ms = int(time.time() * 1000)
    await kafka_send("fact_friendships", fid, {
        "friendship_id": fid,
        "user_id": sender,
        "friend_id": recipient,
        "status": "accepted",
        "created_at": int(created or now_ms) if str(created).isdigit() else now_ms,
        "deleted": False,
    })
    me = await _user_meta(user_id)
    await notify(sender, "friend_accept", "Solicitud aceptada",
                 f"{me['display_name']} aceptó tu solicitud de amistad.")
    await post_activity(user_id, "friend_accept", f"Ahora es amigo de {me['display_name']}", sender)
    return {"status": "accepted", "message": "Ahora son amigos"}


@router.post("/{friendship_id}/decline")
async def decline_friend(
    friendship_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT friendship_id, user_id, friend_id, status, created_at FROM fact_friendships "
        f"WHERE friendship_id = '{esc(friendship_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Solicitud no encontrada")
    fid, sender, recipient, status, created = rows[0]
    if recipient != user_id and sender != user_id:
        raise HTTPException(403, "No autorizado")
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_friendships", fid, {
        "friendship_id": fid,
        "user_id": sender,
        "friend_id": recipient,
        "status": status,
        "created_at": now_ms,
        "deleted": True,
    })
    return {"status": "declined", "message": "Solicitud eliminada"}


@router.get("/activity")
async def friends_activity(authorization: Annotated[str | None, Header()] = None):
    """Feed de actividad propia + amigos."""
    _, user_id = require_token(authorization)
    uid = esc(user_id)
    fr = await pinot_query(
        f"SELECT user_id, friend_id FROM fact_friendships "
        f"WHERE status = 'accepted' AND deleted = false AND "
        f"(user_id = '{uid}' OR friend_id = '{uid}') LIMIT 100"
    )
    ids = {user_id}
    for a, b in fr:
        ids.add(a)
        ids.add(b)
    id_list = list(ids)[:12]
    # Una consulta amplia y filtramos en memoria
    rows = await pinot_query(
        f"SELECT activity_id, user_id, activity_type, summary, created_at "
        f"FROM fact_user_activity WHERE deleted = false "
        f"ORDER BY created_at DESC LIMIT 100"
    )
    id_set = set(id_list)
    meta_cache: dict[str, dict] = {}
    feed = []
    for r in rows:
        uid_i = str(r[1])
        if uid_i not in id_set:
            continue
        if uid_i not in meta_cache:
            meta_cache[uid_i] = await _user_meta(uid_i)
        meta = meta_cache[uid_i]
        feed.append({
            "activity_id": r[0],
            "user_id": uid_i,
            "display_name": meta["display_name"],
            "avatar": meta["avatar"],
            "activity_type": r[2],
            "summary": r[3],
            "created_at": str(r[4]),
        })
        if len(feed) >= 40:
            break
    return {"items": feed}

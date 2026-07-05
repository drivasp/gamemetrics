"""Family Sharing — grupo familiar y biblioteca compartida."""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from social.servicio import notify, post_activity

router = APIRouter(prefix="/family", tags=["family"])

MEMBER_MARKER = "__member__"


class FamilyCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class InviteDTO(BaseModel):
    email: str = Field(min_length=3, max_length=200)


class ShareGameDTO(BaseModel):
    purchase_id: str
    shared_with: str  # user_id del miembro


async def _user_by_email(email: str) -> tuple[str, str] | None:
    rows = await pinot_query(
        f"SELECT user_id, display_name FROM fact_users "
        f"WHERE email = '{esc(email.strip().lower())}' AND deleted = false LIMIT 1"
    )
    if not rows:
        return None
    return str(rows[0][0]), (rows[0][1] or email)


async def _user_name(user_id: str) -> str:
    rows = await pinot_query(
        f"SELECT display_name, email FROM fact_users "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        return "Usuario"
    return rows[0][0] or rows[0][1] or "Usuario"


async def _my_group(user_id: str) -> dict | None:
    # Owner
    rows = await pinot_query(
        f"SELECT group_id, owner_id, name, max_members, created_at "
        f"FROM fact_family_groups WHERE owner_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    if rows:
        r = rows[0]
        return {
            "group_id": r[0], "owner_id": r[1], "name": r[2],
            "max_members": int(r[3] or 6), "created_at": str(r[4]), "is_owner": True,
        }
    # Member via shares
    shares = await pinot_query(
        f"SELECT group_id FROM fact_family_shares "
        f"WHERE shared_with = '{esc(user_id)}' AND purchase_id = '{MEMBER_MARKER}' "
        f"AND deleted = false LIMIT 1"
    )
    if not shares:
        return None
    gid = shares[0][0]
    g = await pinot_query(
        f"SELECT group_id, owner_id, name, max_members, created_at "
        f"FROM fact_family_groups WHERE group_id = '{esc(gid)}' AND deleted = false LIMIT 1"
    )
    if not g:
        return None
    r = g[0]
    return {
        "group_id": r[0], "owner_id": r[1], "name": r[2],
        "max_members": int(r[3] or 6), "created_at": str(r[4]), "is_owner": False,
    }


@router.get("")
async def get_family(authorization: Annotated[str | None, Header()] = None):
    _, user_id = require_token(authorization)
    group = await _my_group(user_id)
    if not group:
        return {"group": None, "members": [], "shares": []}

    shares = await pinot_query(
        f"SELECT share_id, group_id, purchase_id, game_name, shared_by, shared_with, share_type, created_at "
        f"FROM fact_family_shares WHERE group_id = '{esc(group['group_id'])}' AND deleted = false LIMIT 100"
    )
    members = [{"user_id": group["owner_id"], "display_name": await _user_name(group["owner_id"]), "role": "owner"}]
    member_ids = {group["owner_id"]}
    game_shares = []
    for s in shares:
        purchase_id, shared_with = s[2], s[5]
        if purchase_id == MEMBER_MARKER:
            if shared_with not in member_ids:
                member_ids.add(shared_with)
                members.append({
                    "user_id": shared_with,
                    "display_name": await _user_name(shared_with),
                    "role": "member",
                })
        else:
            game_shares.append({
                "share_id": s[0],
                "purchase_id": purchase_id,
                "game_name": s[3],
                "shared_by": s[4],
                "shared_with": shared_with,
                "shared_with_name": await _user_name(shared_with),
                "created_at": str(s[7]),
            })
    return {"group": group, "members": members, "shares": game_shares}


@router.post("/create", status_code=201)
async def create_family(
    body: FamilyCreateDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if await _my_group(user_id):
        raise HTTPException(409, "Ya perteneces a un grupo familiar")
    gid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_family_groups", gid, {
        "group_id": gid,
        "owner_id": user_id,
        "name": body.name.strip(),
        "max_members": 6,
        "created_at": now_ms,
        "deleted": False,
    })
    await post_activity(user_id, "family", f"Creó el grupo familiar «{body.name.strip()}»", gid)
    return {"group_id": gid, "message": "Grupo familiar creado"}


@router.post("/invite")
async def invite_member(
    body: InviteDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    group = await _my_group(user_id)
    if not group or not group.get("is_owner"):
        raise HTTPException(403, "Solo el dueño puede invitar")
    found = await _user_by_email(body.email)
    if not found:
        raise HTTPException(404, "Usuario no encontrado")
    member_id, member_name = found
    if member_id == user_id:
        raise HTTPException(400, "Ya eres el dueño del grupo")

    shares = await pinot_query(
        f"SELECT share_id FROM fact_family_shares WHERE group_id = '{esc(group['group_id'])}' "
        f"AND purchase_id = '{MEMBER_MARKER}' AND deleted = false LIMIT 20"
    )
    if len(shares) + 1 >= group["max_members"]:
        raise HTTPException(400, "El grupo está lleno")

    sid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_family_shares", sid, {
        "share_id": sid,
        "group_id": group["group_id"],
        "purchase_id": MEMBER_MARKER,
        "game_name": "",
        "shared_by": user_id,
        "shared_with": member_id,
        "share_type": "member",
        "created_at": now_ms,
        "deleted": False,
    })
    await notify(
        member_id, "family",
        "Invitación familiar",
        f"Te añadieron al grupo «{group['name']}». Ya puedes recibir juegos compartidos.",
    )
    return {"message": f"{member_name} fue añadido al grupo"}


@router.post("/share")
async def share_game(
    body: ShareGameDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    group = await _my_group(user_id)
    if not group:
        raise HTTPException(400, "No tienes grupo familiar")

    purchases = await pinot_query(
        f"SELECT purchase_id, game_name FROM fact_purchases "
        f"WHERE purchase_id = '{esc(body.purchase_id)}' AND user_id = '{esc(user_id)}' "
        f"AND deleted = false AND refunded = false LIMIT 1"
    )
    if not purchases:
        raise HTTPException(404, "Compra no encontrada en tu biblioteca")

    # miembro válido
    members = await pinot_query(
        f"SELECT shared_with FROM fact_family_shares WHERE group_id = '{esc(group['group_id'])}' "
        f"AND purchase_id = '{MEMBER_MARKER}' AND deleted = false LIMIT 20"
    )
    member_ids = {group["owner_id"]} | {r[0] for r in members}
    if body.shared_with not in member_ids:
        raise HTTPException(400, "El destinatario no es miembro del grupo")

    sid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    game_name = purchases[0][1]
    await kafka_send("fact_family_shares", sid, {
        "share_id": sid,
        "group_id": group["group_id"],
        "purchase_id": body.purchase_id,
        "game_name": game_name,
        "shared_by": user_id,
        "shared_with": body.shared_with,
        "share_type": "game",
        "created_at": now_ms,
        "deleted": False,
    })
    await notify(
        body.shared_with, "family",
        "Juego compartido en familia",
        f"Te compartieron «{game_name}» en el grupo familiar.",
    )
    return {"share_id": sid, "message": f"«{game_name}» compartido"}

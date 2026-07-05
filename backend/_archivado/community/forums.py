"""Foros por juego — hilos y posts."""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from social.servicio import post_activity

router = APIRouter(prefix="/forums", tags=["forums"])


class ThreadCreateDTO(BaseModel):
    product_id: str
    game_slug: str = ""
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=2, max_length=4000)


class PostCreateDTO(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


async def _author_name(user_id: str) -> str:
    rows = await pinot_query(
        f"SELECT display_name, email FROM fact_users "
        f"WHERE user_id = '{esc(user_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        return "Usuario"
    return rows[0][0] or rows[0][1] or "Usuario"


@router.get("/{game_slug}/threads")
async def list_threads(game_slug: str):
    rows = await pinot_query(
        f"SELECT thread_id, product_id, game_slug, author_id, title, pinned, created_at "
        f"FROM fact_forum_threads WHERE game_slug = '{esc(game_slug)}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT 50"
    )
    items = []
    for r in rows:
        items.append({
            "thread_id": r[0],
            "product_id": r[1],
            "game_slug": r[2],
            "author_id": r[3],
            "author_name": await _author_name(r[3]),
            "title": r[4],
            "pinned": bool(r[5]),
            "created_at": str(r[6]),
        })
    items.sort(key=lambda x: (0 if x["pinned"] else 1, x["created_at"]), reverse=True)
    return {"items": items}


@router.post("/threads", status_code=201)
async def create_thread(
    body: ThreadCreateDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    tid = uuid.uuid4().hex[:15]
    pid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_forum_threads", tid, {
        "thread_id": tid,
        "product_id": body.product_id,
        "game_slug": body.game_slug or body.product_id,
        "author_id": user_id,
        "title": body.title.strip(),
        "pinned": False,
        "created_at": now_ms,
        "deleted": False,
    })
    await kafka_send("fact_forum_posts", pid, {
        "post_id": pid,
        "thread_id": tid,
        "author_id": user_id,
        "body": body.body.strip(),
        "edited_at": 0,
        "created_at": now_ms,
        "deleted": False,
    })
    await post_activity(user_id, "forum", f"Abrió un hilo: {body.title.strip()}", tid)
    return {"thread_id": tid, "message": "Hilo creado"}


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    rows = await pinot_query(
        f"SELECT thread_id, product_id, game_slug, author_id, title, pinned, created_at "
        f"FROM fact_forum_threads WHERE thread_id = '{esc(thread_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Hilo no encontrado")
    t = rows[0]
    posts = await pinot_query(
        f"SELECT post_id, thread_id, author_id, body, edited_at, created_at "
        f"FROM fact_forum_posts WHERE thread_id = '{esc(thread_id)}' AND deleted = false "
        f"ORDER BY created_at ASC LIMIT 100"
    )
    post_items = []
    for p in posts:
        post_items.append({
            "post_id": p[0],
            "author_id": p[2],
            "author_name": await _author_name(p[2]),
            "body": p[3],
            "created_at": str(p[5]),
        })
    return {
        "thread": {
            "thread_id": t[0],
            "product_id": t[1],
            "game_slug": t[2],
            "author_id": t[3],
            "author_name": await _author_name(t[3]),
            "title": t[4],
            "pinned": bool(t[5]),
            "created_at": str(t[6]),
        },
        "posts": post_items,
    }


@router.post("/threads/{thread_id}/posts", status_code=201)
async def add_post(
    thread_id: str,
    body: PostCreateDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    exists = await pinot_query(
        f"SELECT thread_id FROM fact_forum_threads "
        f"WHERE thread_id = '{esc(thread_id)}' AND deleted = false LIMIT 1"
    )
    if not exists:
        raise HTTPException(404, "Hilo no encontrado")
    pid = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_forum_posts", pid, {
        "post_id": pid,
        "thread_id": thread_id,
        "author_id": user_id,
        "body": body.body.strip(),
        "edited_at": 0,
        "created_at": now_ms,
        "deleted": False,
    })
    return {"post_id": pid, "message": "Respuesta publicada"}

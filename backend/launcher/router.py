"""Launcher API — instalar, jugar, logros (Fase 3)."""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from launcher.servicio import (
    ensure_achievements,
    ensure_build,
    get_install_state,
    playtime_minutes,
    set_install_state,
    unlock_achievement,
    user_achievements,
)
from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_ms

router = APIRouter(prefix="/launcher", tags=["launcher"])


class ProgressDTO(BaseModel):
    progress_pct: float = Field(ge=0, le=100)


class PlayStartDTO(BaseModel):
    product_id: str
    game_name: str = ""


class PlayEndDTO(BaseModel):
    session_id: str
    product_id: str = ""
    duration_seconds: float = Field(default=0, ge=0)


async def _owns(user_id: str, product_id: str) -> bool:
    rows = await pinot_query(
        f"SELECT purchase_id FROM fact_purchases "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false AND refunded = false LIMIT 1"
    )
    return len(rows) > 0


@router.get("/achievements/me")
async def my_achievements(authorization: Annotated[str | None, Header()] = None):
    """Todos los logros desbloqueados del usuario (sección Logros)."""
    _, user_id = require_token(authorization)
    uid = esc(user_id)
    unlocked_rows = await pinot_query(
        f"SELECT achievement_id, product_id, unlocked_at "
        f"FROM fact_user_achievements WHERE user_id = '{uid}' AND deleted = false LIMIT 200"
    )
    if not unlocked_rows:
        return {"items": [], "total": 0}

    # Mapa de nombres de juegos desde compras
    purchases = await pinot_query(
        f"SELECT product_id, game_name, game_image FROM fact_purchases "
        f"WHERE user_id = '{uid}' AND deleted = false LIMIT 100"
    )
    game_map = {str(r[0]): (r[1], r[2]) for r in purchases}

    defs = await pinot_query(
        f"SELECT achievement_id, name, description, points, product_id "
        f"FROM fact_achievements WHERE deleted = false LIMIT 500"
    )
    def_map = {str(r[0]): r for r in defs}

    items = []
    for achievement_id, product_id, unlocked_at in unlocked_rows:
        aid = str(achievement_id)
        pid = str(product_id)
        d = def_map.get(aid)
        gname, gimg = game_map.get(pid, ("Juego", None))
        items.append({
            "achievement_id": aid,
            "product_id": pid,
            "game_name": gname,
            "game_image": gimg,
            "name": d[1] if d else aid,
            "description": (d[2] if d else "") or "",
            "points": int(d[3] or 0) if d else 0,
            "unlocked_at": str(unlocked_at),
        })
    items.sort(key=lambda x: x["unlocked_at"], reverse=True)
    return {"items": items, "total": len(items)}


@router.get("/library-status")
async def library_status(authorization: Annotated[str | None, Header()] = None):
    """Estado de instalación + tiempo jugado (consultas en lote, no N+1)."""
    _, user_id = require_token(authorization)
    uid = esc(user_id)

    purchases = await pinot_query(
        f"SELECT product_id, game_slug, game_name, game_image, amount, purchased_at "
        f"FROM fact_purchases WHERE user_id = '{uid}' "
        f"AND deleted = false AND refunded = false LIMIT 100"
    )
    if not purchases:
        return {"items": []}

    installs = await pinot_query(
        f"SELECT product_id, build_id, status, progress_pct "
        f"FROM fact_install_states WHERE user_id = '{uid}' AND deleted = false LIMIT 200"
    )
    install_map: dict[str, tuple] = {str(r[0]): r for r in installs}

    sessions = await pinot_query(
        f"SELECT product_id, duration_minutes, ended_at, session_id "
        f"FROM fact_play_sessions WHERE user_id = '{uid}' AND deleted = false LIMIT 1000"
    )
    playtime_map: dict[str, float] = {}
    active_map: dict[str, str] = {}
    for product_id, duration, ended_at, session_id in sessions:
        pid = str(product_id)
        playtime_map[pid] = playtime_map.get(pid, 0.0) + float(duration or 0)
        if int(ended_at or 0) <= 0:
            active_map[pid] = str(session_id)

    items = []
    for p in purchases:
        product_id = str(p[0])
        inst = install_map.get(product_id)
        items.append({
            "product_id": product_id,
            "game_slug": p[1],
            "game_name": p[2],
            "game_image": p[3] or None,
            "amount": float(p[4] or 0),
            "purchased_at": str(p[5]),
            "install_status": (inst[2] if inst else "not_installed") or "not_installed",
            "progress_pct": float(inst[3] or 0) if inst else 0.0,
            "build_id": (inst[1] if inst else "") or "",
            "playtime_minutes": round(playtime_map.get(product_id, 0.0), 1),
            "active_session_id": active_map.get(product_id),
        })
    return {"items": items}


@router.get("/game/{product_id}")
async def game_launcher_detail(
    product_id: str,
    game_name: str = "",
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, product_id):
        raise HTTPException(403, "No posees este juego")

    build = await ensure_build(product_id, game_name)
    install = await get_install_state(user_id, product_id)
    minutes = await playtime_minutes(user_id, product_id)
    achievements = await ensure_achievements(product_id)
    unlocked = await user_achievements(user_id, product_id)

    sessions = await pinot_query(
        f"SELECT session_id, started_at, ended_at FROM fact_play_sessions "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false ORDER BY started_at DESC LIMIT 5"
    )
    session = None
    for r in sessions:
        if int(r[2] or 0) <= 0:
            session = {
                "session_id": r[0],
                "started_at": str(r[1]),
                "ended_at": 0,
                "active": True,
            }
            break

    return {
        "build": build,
        "install": install,
        "playtime_minutes": minutes,
        "active_session": session,
        "achievements": [
            {**a, "unlocked": a["achievement_id"] in unlocked}
            for a in achievements
        ],
        "achievements_unlocked": len(unlocked),
        "achievements_total": len(achievements),
    }


@router.post("/install/{product_id}")
async def start_install(
    product_id: str,
    game_name: str = "",
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, product_id):
        raise HTTPException(403, "No posees este juego")

    build = await ensure_build(product_id, game_name)
    token_id = uuid.uuid4().hex
    now_ms = int(time.time() * 1000)
    expires = now_ms + 30 * 60 * 1000
    await kafka_send("fact_download_tokens", token_id, {
        "token_id": token_id,
        "user_id": user_id,
        "build_id": build["build_id"],
        "used": False,
        "expires_at": expires,
        "created_at": now_ms,
        "deleted": False,
    })
    install = await set_install_state(
        user_id, product_id, "downloading", 0.0, build["build_id"]
    )
    return {
        "install": install,
        "build": build,
        "download_token": token_id,
        "download_url": f"/launcher/download/{token_id}",
        "message": "Descarga iniciada",
    }


@router.patch("/install/{product_id}/progress")
async def update_progress(
    product_id: str,
    body: ProgressDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, product_id):
        raise HTTPException(403, "No posees este juego")

    current = await get_install_state(user_id, product_id)
    pct = float(body.progress_pct)
    status = "installed" if pct >= 100 else "downloading"
    if pct >= 100:
        pct = 100.0
    install = await set_install_state(
        user_id, product_id, status, pct, current.get("build_id") or ""
    )
    return {"install": install}


@router.post("/uninstall/{product_id}")
async def uninstall(
    product_id: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, product_id):
        raise HTTPException(403, "No posees este juego")
    install = await set_install_state(user_id, product_id, "not_installed", 0.0, "")
    return {"install": install, "message": "Juego desinstalado"}


@router.get("/download/{token_id}")
async def download_package(token_id: str):
    """Entrega un paquete manifest (demo profesional sin MinIO)."""
    rows = await pinot_query(
        f"SELECT token_id, user_id, build_id, used, expires_at FROM fact_download_tokens "
        f"WHERE token_id = '{esc(token_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        content = (
            "GameMetrics Digital Delivery Package\n"
            f"token={token_id}\n"
            "status=pending_index\n"
        )
        return PlainTextResponse(content, media_type="text/plain")

    token_id_v, user_id, build_id, used, expires_at = rows[0]
    if to_ms(expires_at) and int(time.time() * 1000) > to_ms(expires_at):
        raise HTTPException(410, "Token de descarga expirado")

    builds = await pinot_query(
        f"SELECT version, os, file_path, file_size_bytes, checksum FROM fact_builds "
        f"WHERE build_id = '{esc(build_id)}' AND deleted = false LIMIT 1"
    )
    version = builds[0][0] if builds else "1.0.0"
    os_name = builds[0][1] if builds else "win"
    path = builds[0][2] if builds else ""
    size = builds[0][3] if builds else 0
    checksum = builds[0][4] if builds else ""

    await kafka_send("fact_download_tokens", token_id_v, {
        "token_id": token_id_v,
        "user_id": user_id,
        "build_id": build_id,
        "used": True,
        "expires_at": int(expires_at or 0),
        "created_at": int(time.time() * 1000),
        "deleted": False,
    })

    content = (
        "GameMetrics Digital Delivery Package\n"
        f"build_id={build_id}\n"
        f"version={version}\n"
        f"os={os_name}\n"
        f"file_path={path}\n"
        f"file_size_bytes={size}\n"
        f"checksum={checksum}\n"
        "format=zip\n"
        "note=Paquete de instalación gestionado por GameMetrics Launcher\n"
    )
    return PlainTextResponse(
        content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="gamemetrics_{build_id}.manifest"'},
    )


@router.post("/play/start")
async def play_start(
    body: PlayStartDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns(user_id, body.product_id):
        raise HTTPException(403, "No posees este juego")

    install = await get_install_state(user_id, body.product_id)
    if install["status"] != "installed":
        raise HTTPException(400, "Debes instalar el juego antes de jugar")

    sessions = await pinot_query(
        f"SELECT session_id, started_at, ended_at FROM fact_play_sessions "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(body.product_id)}' "
        f"AND deleted = false ORDER BY started_at DESC LIMIT 5"
    )
    for r in sessions:
        if int(r[2] or 0) <= 0:
            return {
                "session": {
                    "session_id": r[0],
                    "user_id": user_id,
                    "product_id": body.product_id,
                    "started_at": str(r[1]),
                    "ended_at": 0,
                    "duration_minutes": 0.0,
                    "active": True,
                },
                "unlocked_achievements": [],
                "message": "Sesión ya activa",
            }

    await ensure_achievements(body.product_id)
    session_id = uuid.uuid4().hex[:15]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_play_sessions", session_id, {
        "session_id": session_id,
        "user_id": user_id,
        "product_id": body.product_id,
        "started_at": now_ms,
        "ended_at": 0,
        "duration_minutes": 0.0,
        "deleted": False,
    })

    unlocked = []
    if await unlock_achievement(user_id, body.product_id, f"{body.product_id}_first_launch"):
        unlocked.append("Primer arranque")

    try:
        from social.servicio import post_activity, notify
        await post_activity(
            user_id, "play",
            f"Está jugando a {body.game_name or 'un juego'}",
            body.product_id,
        )
        for name in unlocked:
            await notify(user_id, "achievement", "¡Logro desbloqueado!", name)
            await post_activity(user_id, "achievement", f"Desbloqueó: {name}", body.product_id)
    except Exception:
        pass

    return {
        "session": {
            "session_id": session_id,
            "user_id": user_id,
            "product_id": body.product_id,
            "started_at": str(now_ms),
            "ended_at": 0,
            "duration_minutes": 0.0,
            "active": True,
        },
        "unlocked_achievements": unlocked,
        "message": "¡A jugar!",
    }


@router.post("/play/end")
async def play_end(
    body: PlayEndDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT session_id, user_id, product_id, started_at, ended_at, duration_minutes "
        f"FROM fact_play_sessions WHERE session_id = '{esc(body.session_id)}' "
        f"AND deleted = false LIMIT 1"
    )

    now_ms = int(time.time() * 1000)
    if rows:
        session_id, owner, product_id, started_at, ended_at, _ = rows[0]
        if owner != user_id:
            raise HTTPException(403, "Sesión no pertenece a este usuario")
        if int(ended_at or 0) > 0:
            return {
                "message": "Sesión ya finalizada",
                "duration_minutes": 0,
                "playtime_minutes": await playtime_minutes(user_id, product_id),
                "unlocked_achievements": [],
            }
        start_ms = to_ms(started_at)
        duration = max(0.1, round((now_ms - start_ms) / 60000.0, 2))
    else:
        session_id = body.session_id
        product_id = body.product_id
        if not product_id:
            raise HTTPException(404, "Sesión no encontrada")
        duration = max(0.1, round(float(body.duration_seconds or 0) / 60.0, 2))
        start_ms = now_ms - int(duration * 60000)

    await kafka_send("fact_play_sessions", session_id, {
        "session_id": session_id,
        "user_id": user_id,
        "product_id": product_id,
        "started_at": start_ms,
        "ended_at": now_ms,
        "duration_minutes": duration,
        "deleted": False,
    })

    total = await playtime_minutes(user_id, product_id) + duration
    unlocked = []
    if total >= 60 and await unlock_achievement(user_id, product_id, f"{product_id}_hour_one"):
        unlocked.append("Una hora de juego")
    if total >= 300 and await unlock_achievement(user_id, product_id, f"{product_id}_veteran"):
        unlocked.append("Veterano")

    ua = await user_achievements(user_id, product_id)
    if len(ua) >= 2 and await unlock_achievement(user_id, product_id, f"{product_id}_collector"):
        unlocked.append("Coleccionista")

    return {
        "duration_minutes": duration,
        "playtime_minutes": round(total, 1),
        "unlocked_achievements": unlocked,
        "message": f"Sesión finalizada · {duration} min",
    }

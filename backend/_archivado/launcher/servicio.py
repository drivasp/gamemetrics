"""Servicios de distribución digital (builds, install, play, achievements)."""
from __future__ import annotations

import hashlib
import time
import uuid

from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_bool, to_ms

DEFAULT_ACHIEVEMENTS = [
    ("first_launch", "Primer arranque", "Inicia el juego por primera vez.", 5),
    ("hour_one", "Una hora de juego", "Acumula al menos 60 minutos de juego.", 10),
    ("collector", "Coleccionista", "Desbloquea varios logros del título.", 15),
    ("veteran", "Veterano", "Acumula 5 horas de juego.", 25),
]


async def ensure_build(product_id: str, game_name: str = "") -> dict:
    rows = await pinot_query(
        f"SELECT build_id, product_id, version, os, file_path, file_size_bytes, checksum, created_at "
        f"FROM fact_builds WHERE product_id = '{esc(product_id)}' AND deleted = false "
        f"AND os = 'win' ORDER BY created_at DESC LIMIT 1"
    )
    if rows:
        r = rows[0]
        return {
            "build_id": r[0],
            "product_id": r[1],
            "version": r[2],
            "os": r[3],
            "file_path": r[4],
            "file_size_bytes": int(r[5] or 0),
            "checksum": r[6] or "",
            "created_at": str(r[7]),
        }

    now_ms = int(time.time() * 1000)
    build_id = f"b_{product_id[:12]}_win"
    size = 800_000_000 + (int(hashlib.md5(product_id.encode()).hexdigest()[:8], 16) % 2_000_000_000)
    checksum = hashlib.sha256(f"{product_id}:{build_id}".encode()).hexdigest()[:16]
    label = (game_name or product_id).replace(" ", "_")[:40]
    path = f"builds/{product_id}/{label}_1.0.0_win.zip"
    await kafka_send("fact_builds", build_id, {
        "build_id": build_id,
        "product_id": product_id,
        "version": "1.0.0",
        "os": "win",
        "file_path": path,
        "file_size_bytes": size,
        "checksum": checksum,
        "created_at": now_ms,
        "deleted": False,
    })
    return {
        "build_id": build_id,
        "product_id": product_id,
        "version": "1.0.0",
        "os": "win",
        "file_path": path,
        "file_size_bytes": size,
        "checksum": checksum,
        "created_at": str(now_ms),
    }


async def ensure_achievements(product_id: str) -> list[dict]:
    rows = await pinot_query(
        f"SELECT achievement_id, product_id, name, description, icon_url, points, created_at "
        f"FROM fact_achievements WHERE product_id = '{esc(product_id)}' AND deleted = false LIMIT 20"
    )
    if rows:
        return [
            {
                "achievement_id": r[0],
                "product_id": r[1],
                "name": r[2],
                "description": r[3] or "",
                "icon_url": r[4] or "",
                "points": int(r[5] or 0),
                "created_at": str(r[6]),
            }
            for r in rows
        ]

    now_ms = int(time.time() * 1000)
    out = []
    for key, name, desc, points in DEFAULT_ACHIEVEMENTS:
        aid = f"{product_id}_{key}"
        await kafka_send("fact_achievements", aid, {
            "achievement_id": aid,
            "product_id": product_id,
            "name": name,
            "description": desc,
            "icon_url": "",
            "points": points,
            "created_at": now_ms,
            "deleted": False,
        })
        out.append({
            "achievement_id": aid,
            "product_id": product_id,
            "name": name,
            "description": desc,
            "icon_url": "",
            "points": points,
            "created_at": str(now_ms),
        })
    return out


async def get_install_state(user_id: str, product_id: str) -> dict:
    install_id = f"{user_id}_{product_id}"
    rows = await pinot_query(
        f"SELECT install_id, user_id, product_id, build_id, status, progress_pct, updated_at "
        f"FROM fact_install_states WHERE install_id = '{esc(install_id)}' AND deleted = false LIMIT 1"
    )
    if not rows:
        return {
            "install_id": install_id,
            "user_id": user_id,
            "product_id": product_id,
            "build_id": "",
            "status": "not_installed",
            "progress_pct": 0.0,
            "updated_at": "",
        }
    r = rows[0]
    return {
        "install_id": r[0],
        "user_id": r[1],
        "product_id": r[2],
        "build_id": r[3] or "",
        "status": r[4] or "not_installed",
        "progress_pct": float(r[5] or 0),
        "updated_at": str(r[6]),
    }


async def set_install_state(
    user_id: str,
    product_id: str,
    status: str,
    progress_pct: float,
    build_id: str = "",
) -> dict:
    install_id = f"{user_id}_{product_id}"
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_install_states", install_id, {
        "install_id": install_id,
        "user_id": user_id,
        "product_id": product_id,
        "build_id": build_id,
        "status": status,
        "progress_pct": round(float(progress_pct), 1),
        "updated_at": now_ms,
        "deleted": False,
    })
    return {
        "install_id": install_id,
        "user_id": user_id,
        "product_id": product_id,
        "build_id": build_id,
        "status": status,
        "progress_pct": round(float(progress_pct), 1),
        "updated_at": str(now_ms),
    }


async def playtime_minutes(user_id: str, product_id: str) -> float:
    rows = await pinot_query(
        f"SELECT duration_minutes FROM fact_play_sessions "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false LIMIT 500"
    )
    return round(sum(float(r[0] or 0) for r in rows), 1)


async def active_session(user_id: str, product_id: str) -> dict | None:
    rows = await pinot_query(
        f"SELECT session_id, user_id, product_id, started_at, ended_at, duration_minutes "
        f"FROM fact_play_sessions WHERE user_id = '{esc(user_id)}' "
        f"AND product_id = '{esc(product_id)}' AND deleted = false "
        f"ORDER BY started_at DESC LIMIT 5"
    )
    for r in rows:
        ended = int(r[4] or 0)
        if ended <= 0:
            return {
                "session_id": r[0],
                "user_id": r[1],
                "product_id": r[2],
                "started_at": str(r[3]),
                "ended_at": 0,
                "duration_minutes": float(r[5] or 0),
                "active": True,
            }
    return None


async def unlock_achievement(user_id: str, product_id: str, achievement_id: str) -> bool:
    ua_id = f"{user_id}_{achievement_id}"
    existing = await pinot_query(
        f"SELECT user_achievement_id FROM fact_user_achievements "
        f"WHERE user_achievement_id = '{esc(ua_id)}' AND deleted = false LIMIT 1"
    )
    if existing:
        return False
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_user_achievements", ua_id, {
        "user_achievement_id": ua_id,
        "user_id": user_id,
        "achievement_id": achievement_id,
        "product_id": product_id,
        "unlocked_at": now_ms,
        "deleted": False,
    })
    return True


async def user_achievements(user_id: str, product_id: str) -> set[str]:
    rows = await pinot_query(
        f"SELECT achievement_id FROM fact_user_achievements "
        f"WHERE user_id = '{esc(user_id)}' AND product_id = '{esc(product_id)}' "
        f"AND deleted = false LIMIT 50"
    )
    return {r[0] for r in rows}

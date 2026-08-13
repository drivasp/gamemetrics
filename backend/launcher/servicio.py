"""Servicios de distribución digital (builds, install, play, achievements)."""
from __future__ import annotations

import re
import time
import uuid

from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.storage import ensure_package, object_exists, put_bytes, sha256_hex

DEFAULT_ACHIEVEMENTS = [
    ("first_launch", "Primer arranque", "Inicia el juego por primera vez.", 5),
    ("hour_one", "Una hora de juego", "Acumula al menos 60 minutos de juego.", 10),
    ("collector", "Coleccionista", "Desbloquea varios logros del título.", 15),
    ("veteran", "Veterano", "Acumula 5 horas de juego.", 25),
]


def version_key(version: str) -> tuple:
    """Parse dotted version for comparison (1.0.0 < 1.0.1)."""
    parts = re.findall(r"\d+", str(version or "0"))
    nums = [int(p) for p in parts[:4]] or [0]
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums)


def _row_to_build(r) -> dict:
    return {
        "build_id": r[0],
        "product_id": r[1],
        "version": r[2] or "1.0.0",
        "os": r[3] or "win",
        "file_path": r[4] or "",
        "file_size_bytes": int(r[5] or 0),
        "checksum": r[6] or "",
        "created_at": str(r[7]),
    }


async def list_builds(product_id: str, limit: int = 20) -> list[dict]:
    rows = await pinot_query(
        f"SELECT build_id, product_id, version, os, file_path, file_size_bytes, checksum, created_at "
        f"FROM fact_builds WHERE product_id = '{esc(product_id)}' AND deleted = false "
        f"AND os = 'win' ORDER BY created_at DESC LIMIT {int(limit)}"
    )
    builds = [_row_to_build(r) for r in rows]
    builds.sort(key=lambda b: version_key(b["version"]), reverse=True)
    return builds


async def get_build_by_id(build_id: str) -> dict | None:
    rows = await pinot_query(
        f"SELECT build_id, product_id, version, os, file_path, file_size_bytes, checksum, created_at "
        f"FROM fact_builds WHERE build_id = '{esc(build_id)}' AND deleted = false LIMIT 1"
    )
    return _row_to_build(rows[0]) if rows else None


async def latest_build(product_id: str) -> dict | None:
    builds = await list_builds(product_id, limit=50)
    return builds[0] if builds else None


async def register_build(
    product_id: str,
    version: str,
    file_path: str,
    file_size_bytes: int,
    checksum: str,
    os_name: str = "win",
) -> dict:
    """Register a new build version in Pinot (does not replace previous versions)."""
    safe_ver = re.sub(r"[^0-9A-Za-z._-]", "_", version)[:32] or "1.0.0"
    build_id = f"b_{product_id[:10]}_{safe_ver}_{uuid.uuid4().hex[:6]}"
    now_ms = int(time.time() * 1000)
    payload = {
        "build_id": build_id,
        "product_id": product_id,
        "version": safe_ver,
        "os": os_name,
        "file_path": file_path,
        "file_size_bytes": int(file_size_bytes),
        "checksum": checksum,
        "created_at": now_ms,
        "deleted": False,
    }
    await kafka_send("fact_builds", build_id, payload)
    return {**payload, "created_at": str(now_ms)}


async def publish_build_bytes(
    product_id: str,
    version: str,
    data: bytes,
    game_name: str = "",
) -> dict:
    """Upload ZIP bytes and register as a new fact_builds row."""
    safe_ver = re.sub(r"[^0-9A-Za-z._-]", "_", version)[:32] or "1.0.0"
    label = "".join(c if c.isalnum() or c in "-_" else "_" for c in (game_name or product_id))[:40]
    key = f"builds/{product_id}/{label}_{safe_ver}_win.zip"
    put_bytes(key, data, content_type="application/zip")
    return await register_build(
        product_id, safe_ver, key, len(data), sha256_hex(data),
    )


async def ensure_build(product_id: str, game_name: str = "") -> dict:
    """Ensure Pinot build metadata + real ZIP package in object storage."""
    existing = await latest_build(product_id)
    if existing:
        path = existing["file_path"]
        if path and not object_exists(path):
            pkg = ensure_package(product_id, game_name, existing["version"] or "1.0.0")
            existing["file_path"] = pkg["file_path"]
            existing["file_size_bytes"] = pkg["file_size_bytes"]
            existing["checksum"] = pkg["checksum"]
            await kafka_send("fact_builds", existing["build_id"], {
                "build_id": existing["build_id"],
                "product_id": existing["product_id"],
                "version": existing["version"],
                "os": existing.get("os") or "win",
                "file_path": pkg["file_path"],
                "file_size_bytes": pkg["file_size_bytes"],
                "checksum": pkg["checksum"],
                "created_at": int(time.time() * 1000),
                "deleted": False,
            })
        return existing

    pkg = ensure_package(product_id, game_name, "1.0.0")
    return await register_build(
        product_id, "1.0.0", pkg["file_path"], pkg["file_size_bytes"], pkg["checksum"],
    )


async def update_available(user_id: str, product_id: str, game_name: str = "") -> dict:
    """Compare installed build vs latest published build."""
    install = await get_install_state(user_id, product_id)
    latest = await ensure_build(product_id, game_name)
    installed_build = None
    installed_version = ""
    if install.get("build_id"):
        installed_build = await get_build_by_id(install["build_id"])
        installed_version = (installed_build or {}).get("version") or ""
    has_update = False
    if install.get("status") == "installed" and latest:
        if not installed_version:
            has_update = install.get("build_id") != latest["build_id"]
        else:
            has_update = version_key(latest["version"]) > version_key(installed_version)
            if not has_update and install.get("build_id") != latest["build_id"]:
                # Same version string but different checksum/build → treat as update
                if (installed_build or {}).get("checksum") != latest.get("checksum"):
                    has_update = True
    return {
        "product_id": product_id,
        "update_available": has_update,
        "installed_status": install.get("status") or "not_installed",
        "installed_build_id": install.get("build_id") or "",
        "installed_version": installed_version,
        "latest_build": latest,
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

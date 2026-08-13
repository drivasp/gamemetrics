import asyncio
import os
import time
import urllib.parse

import httpx
from dotenv import load_dotenv

from tienda.modelos_store import GameMediaDTO

load_dotenv()

RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
RAWG_BASE = "https://api.rawg.io/api"
_media_cache: dict[str, dict] = {}
_cover_cache: dict[str, str | None] = {}
_rawg_sem = asyncio.Semaphore(4)
# Si RAWG está caído/timeout, no bloquear cada portada 3–6s (rompe el <img> del navegador).
_rawg_fail_until = 0.0
_RAWG_TIMEOUT = float(os.getenv("RAWG_TIMEOUT_SEC", "1.2"))
_RAWG_COOLDOWN_SEC = float(os.getenv("RAWG_COOLDOWN_SEC", "60"))


def _rawg_available() -> bool:
    return bool(RAWG_API_KEY) and time.time() >= _rawg_fail_until


def _mark_rawg_down() -> None:
    global _rawg_fail_until
    _rawg_fail_until = time.time() + _RAWG_COOLDOWN_SEC
    print(f"[RAWG] cooldown {_RAWG_COOLDOWN_SEC:.0f}s — usando placeholders")


async def _rawg_get(path: str) -> dict:
    if not _rawg_available():
        return {}
    url = f"{RAWG_BASE}{path}{'&' if '?' in path else '?'}key={RAWG_API_KEY}"
    async with _rawg_sem:
        async with httpx.AsyncClient(timeout=_RAWG_TIMEOUT) as client:
            try:
                r = await client.get(url)
                r.raise_for_status()
                return r.json()
            except Exception as exc:
                print(f"[RAWG] ERROR {path}: {type(exc).__name__}")
                _mark_rawg_down()
                return {}


async def get_cover_url(slug: str, name: str = "") -> str | None:
    """Portada ligera vía RAWG. Si la API no responde, None inmediato (placeholder)."""
    if not _rawg_available():
        return None

    key = f"{slug}|{name}"
    if key in _cover_cache:
        return _cover_cache[key]

    if slug:
        detail = await _rawg_get(f"/games/{slug}")
        bg = detail.get("background_image") or detail.get("background_image_additional")
        if bg:
            _cover_cache[key] = bg
            return bg

    # Solo buscar por nombre si RAWG sigue disponible tras el intento por slug.
    if name and _rawg_available():
        q = urllib.parse.quote(name[:48])
        search = await _rawg_get(f"/games?search={q}&page_size=1")
        for hit in search.get("results") or []:
            bg = hit.get("background_image") or hit.get("background_image_additional")
            if bg:
                _cover_cache[key] = bg
                return bg

    _cover_cache[key] = None
    return None


async def get_media(slug: str) -> GameMediaDTO:
    if slug in _media_cache:
        return GameMediaDTO(**_media_cache[slug])
    if not _rawg_available():
        media = GameMediaDTO()
        _media_cache[slug] = media.model_dump()
        return media

    detail, shots = await asyncio.gather(
        _rawg_get(f"/games/{slug}"),
        _rawg_get(f"/games/{slug}/screenshots"),
    )
    trailer_url = _pick_trailer(detail)
    media = GameMediaDTO(
        background_image=detail.get("background_image"),
        description=detail.get("description_raw"),
        screenshots=[s["image"] for s in shots.get("results", [])[:6] if "image" in s],
        trailer_url=trailer_url,
    )
    _media_cache[slug] = media.model_dump()
    return media


def _pick_trailer(detail: dict) -> str | None:
    for movie in detail.get("movies") or []:
        data = movie.get("data") or {}
        for key in ("max", "480", "high"):
            url = data.get(key)
            if url:
                return url
    return None

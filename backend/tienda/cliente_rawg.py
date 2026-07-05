import asyncio
import os
import urllib.parse

import httpx
from dotenv import load_dotenv

from tienda.modelos_store import GameMediaDTO

load_dotenv()

RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
RAWG_BASE = "https://api.rawg.io/api"
_media_cache: dict[str, dict] = {}
_cover_cache: dict[str, str | None] = {}


async def _rawg_get(path: str) -> dict:
    if not RAWG_API_KEY:
        return {}
    url = f"{RAWG_BASE}{path}{'&' if '?' in path else '?'}key={RAWG_API_KEY}"
    async with httpx.AsyncClient(timeout=4.0) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            print(f"[RAWG] ERROR {path}: {exc}")
            return {}


async def get_cover_url(slug: str, name: str = "") -> str | None:
    """Portada vía RAWG: slug directo, luego búsqueda por nombre."""
    key = f"{slug}|{name}"
    if key in _cover_cache:
        return _cover_cache[key]

    media = await get_media(slug)
    if media.background_image:
        _cover_cache[key] = media.background_image
        return media.background_image

    if name and RAWG_API_KEY:
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

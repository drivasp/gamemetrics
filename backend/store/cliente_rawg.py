import asyncio
import os

import httpx
from dotenv import load_dotenv

from store.modelos_store import GameMediaDTO

load_dotenv()

RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
RAWG_BASE = "https://api.rawg.io/api"
_media_cache: dict[str, dict] = {}


async def _rawg_get(path: str) -> dict:
    if not RAWG_API_KEY:
        return {}
    url = f"{RAWG_BASE}{path}?key={RAWG_API_KEY}"
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            print(f"[RAWG] ERROR {path}: {exc}")
            return {}


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

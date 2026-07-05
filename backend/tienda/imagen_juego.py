"""Resolución de portadas: RAWG (gratis con API key) + placeholder SVG local."""
from __future__ import annotations

import urllib.parse

from tienda.cliente_rawg import get_cover_url

_cover_cache: dict[str, str] = {}


def placeholder_image(name: str, slug: str = "") -> str:
    """URL servida por el backend — no depende de servicios externos."""
    key = slug or name[:40]
    title = urllib.parse.quote(name[:40], safe="")
    return f"/store/cover-placeholder/{urllib.parse.quote(key, safe='')}?title={title}"


async def resolve_cover(slug: str, name: str) -> str:
    cache_key = slug or name
    if cache_key in _cover_cache:
        return _cover_cache[cache_key]

    url = await get_cover_url(slug, name)
    if not url:
        url = placeholder_image(name, slug)
    _cover_cache[cache_key] = url
    return url


def svg_placeholder(title: str) -> str:
    safe = (title or "Juego")[:36].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f3460"/>
      <stop offset="100%" stop-color="#1a1a2e"/>
    </linearGradient>
  </defs>
  <rect width="600" height="400" fill="url(#g)"/>
  <rect x="24" y="24" width="552" height="352" rx="12" fill="none" stroke="#e94560" stroke-width="2" opacity="0.35"/>
  <rect x="248" y="148" width="104" height="64" rx="10" fill="none" stroke="#e94560" stroke-width="2" opacity="0.85"/>
  <circle cx="278" cy="180" r="8" fill="#e94560"/>
  <circle cx="318" cy="172" r="6" fill="none" stroke="#66c0f4" stroke-width="2"/>
  <circle cx="332" cy="188" r="6" fill="none" stroke="#66c0f4" stroke-width="2"/>
  <text x="300" y="240" fill="#ffffff" font-family="Segoe UI,Arial,sans-serif" font-size="18" font-weight="600" text-anchor="middle">{safe}</text>
</svg>"""

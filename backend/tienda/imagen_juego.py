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


def cover_proxy_url(name: str, slug: str = "") -> str:
    """
    URL lazy: el navegador pide la portada; el backend consulta RAWG y redirige.
    Así el listado de tienda responde rápido y las imágenes llegan igual.
    """
    key = slug or name[:40]
    title = urllib.parse.quote(name[:40], safe="")
    return f"/store/cover/{urllib.parse.quote(key, safe='')}?title={title}"


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
    """Portada SVG local — se ve como cover de tienda, no como imagen rota."""
    raw = (title or "Juego").strip()[:42]
    safe = (
        raw.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    # Dos líneas si el nombre es largo
    if len(raw) > 22:
        cut = raw[:22].rsplit(" ", 1)[0] or raw[:22]
        line1 = cut.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rest = raw[len(cut):].strip()[:22]
        line2 = rest.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text_block = (
            f'<text x="300" y="195" fill="#ffffff" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="26" font-weight="700" text-anchor="middle">{line1}</text>'
            f'<text x="300" y="230" fill="#c7d5e0" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="22" font-weight="600" text-anchor="middle">{line2}</text>'
        )
    else:
        text_block = (
            f'<text x="300" y="210" fill="#ffffff" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="28" font-weight="700" text-anchor="middle">{safe}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1b2838"/>
      <stop offset="55%" stop-color="#2a475e"/>
      <stop offset="100%" stop-color="#171a21"/>
    </linearGradient>
  </defs>
  <rect width="600" height="400" fill="url(#bg)"/>
  <rect x="0" y="320" width="600" height="80" fill="#000000" opacity="0.35"/>
  <text x="24" y="36" fill="#66c0f4" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="700" letter-spacing="2">GAMEMETRICS</text>
  {text_block}
  <text x="300" y="360" fill="#8f98a0" font-family="Segoe UI,Arial,sans-serif" font-size="14" text-anchor="middle">Portada no disponible</text>
</svg>"""

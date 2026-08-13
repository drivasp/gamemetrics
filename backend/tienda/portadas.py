from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from tienda.imagen_juego import resolve_cover, svg_placeholder

router = APIRouter()


@router.get("/cover-placeholder/{slug}")
async def cover_placeholder(slug: str, title: str = "Juego"):
    svg = svg_placeholder(title or slug.replace("-", " "))
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/cover/{slug}")
async def cover_redirect(slug: str, title: str = ""):
    """
    Sirve portada RAWG (redirect) o SVG local (200 directo).
    Evita cadenas 302 lentas que el navegador cancela y muestran el icono rojo.
    """
    label = title or slug.replace("-", " ")
    url = await resolve_cover(slug, label)
    if url.startswith("http://") or url.startswith("https://"):
        return RedirectResponse(url, status_code=302)
    # Fallback local: devolver el SVG aquí (sin segundo hop).
    svg = svg_placeholder(label)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=300"},
    )

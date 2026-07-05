from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from tienda.imagen_juego import placeholder_image, resolve_cover, svg_placeholder

router = APIRouter()


@router.get("/cover-placeholder/{slug}")
async def cover_placeholder(slug: str, title: str = "Juego"):
    svg = svg_placeholder(title or slug.replace("-", " "))
    return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/cover/{slug}")
async def cover_redirect(slug: str, title: str = ""):
    url = await resolve_cover(slug, title or slug.replace("-", " "))
    if url.startswith("/"):
        return RedirectResponse(url, status_code=302)
    return RedirectResponse(url, status_code=302)

from fastapi import APIRouter

from tienda.filtros import router as filtros_router
from tienda.portadas import router as portadas_router
from tienda.juegos_destacados import router as destacados_router
from tienda.nuevos_lanzamientos import router as nuevos_router
from tienda.juegos_populares import router as populares_router
from tienda.juegos_gratis import router as gratis_router
from tienda.generos import router as generos_router
from tienda.listar_juegos import router as listar_router
from tienda.detalle_juego import router as detalle_router  # ⚠ generic /{slug} — must be last

router = APIRouter(prefix="/store", tags=["store"])

# Specific routes first — order matters to avoid /{slug} capturing them
router.include_router(filtros_router)
router.include_router(portadas_router)
router.include_router(destacados_router)
router.include_router(nuevos_router)
router.include_router(populares_router)
router.include_router(gratis_router)
router.include_router(generos_router)
router.include_router(listar_router)
router.include_router(detalle_router)

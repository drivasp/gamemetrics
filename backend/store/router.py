from fastapi import APIRouter

from store.filtros import router as filtros_router
from store.juegos_destacados import router as destacados_router
from store.nuevos_lanzamientos import router as nuevos_router
from store.juegos_populares import router as populares_router
from store.juegos_gratis import router as gratis_router
from store.generos import router as generos_router
from store.listar_juegos import router as listar_router
from store.detalle_juego import router as detalle_router  # ⚠ generic /{slug} — must be last

router = APIRouter(prefix="/store", tags=["store"])

# Specific routes first — order matters to avoid /{slug} capturing them
router.include_router(filtros_router)
router.include_router(destacados_router)
router.include_router(nuevos_router)
router.include_router(populares_router)
router.include_router(gratis_router)
router.include_router(generos_router)
router.include_router(listar_router)
router.include_router(detalle_router)

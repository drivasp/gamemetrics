from fastapi import APIRouter

from dimensiones.plataformas import router as plataformas_router
from dimensiones.generos import router as generos_router
from dimensiones.desarrolladores import router as desarrolladores_router
from dimensiones.publicadores import router as publicadores_router
from dimensiones.esrb import router as esrb_router

router = APIRouter(prefix="/api/dim", tags=["dimensiones"])

router.include_router(plataformas_router)
router.include_router(generos_router)
router.include_router(desarrolladores_router)
router.include_router(publicadores_router)
router.include_router(esrb_router)

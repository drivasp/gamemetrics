from fastapi import APIRouter

from dashboard.top_rated import router as top_rated_router
from dashboard.por_anio import router as por_anio_router
from dashboard.por_genero import router as por_genero_router
from dashboard.por_plataforma import router as por_plataforma_router
from dashboard.por_esrb import router as por_esrb_router

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

router.include_router(top_rated_router)
router.include_router(por_anio_router)
router.include_router(por_genero_router)
router.include_router(por_plataforma_router)
router.include_router(por_esrb_router)

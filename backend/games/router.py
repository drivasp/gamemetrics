from fastapi import APIRouter

from games.listar_juegos import router as listar_router
from games.contar_juegos import router as contar_router
from games.obtener_juego import router as obtener_router

router = APIRouter(prefix="/api/games", tags=["games"])

router.include_router(listar_router)
router.include_router(contar_router)   # /count debe ir antes que /{id}
router.include_router(obtener_router)

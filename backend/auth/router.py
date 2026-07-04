from fastapi import APIRouter

from auth.registro import router as registro_router
from auth.login import router as login_router
from auth.perfil import router as perfil_router
from auth.avatar import router as avatar_router

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(registro_router)
router.include_router(login_router)
router.include_router(perfil_router)
router.include_router(avatar_router)

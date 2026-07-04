from fastapi import APIRouter

from empresa.endpoints import router as endpoints_router

router = APIRouter(prefix="/empresa", tags=["empresa"])

router.include_router(endpoints_router)

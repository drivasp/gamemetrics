from fastapi import APIRouter

from community.forums import router as forums_router
from community.family import router as family_router
from community.apikeys import router as apikeys_router
from community.search_log import router as search_router

router = APIRouter()
router.include_router(forums_router)
router.include_router(family_router)
router.include_router(apikeys_router)
router.include_router(search_router)

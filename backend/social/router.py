from fastapi import APIRouter

from social.friends import router as friends_router
from social.notifications import router as notifications_router
from social.support import router as support_router
from social.partners import router as partners_router

router = APIRouter()
router.include_router(friends_router)
router.include_router(notifications_router)
router.include_router(support_router)
router.include_router(partners_router)

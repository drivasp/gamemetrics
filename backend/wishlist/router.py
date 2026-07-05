from fastapi import APIRouter

from wishlist.wishlist import router as wishlist_router

router = APIRouter(prefix="/user", tags=["user"])

router.include_router(wishlist_router)

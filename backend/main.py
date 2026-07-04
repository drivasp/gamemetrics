from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared.kafka_producer import start_producer, stop_producer
from games.router import router as games_router
from dashboard.router import router as dashboard_router
from dimensiones.router import router as dimensiones_router
from store.router import router as store_router
from auth.router import router as auth_router
from user.router import router as user_router
from empresa.router import router as empresa_router
from cart.router import router as cart_router
from checkout.router import router as checkout_router
from library.router import router as library_router
from reviews.router import router as reviews_router
from refunds.router import router as refunds_router
from wallet.router import router as wallet_router
from coupons.router import router as coupons_router
from gifts.router import router as gifts_router
from alerts.router import router as alerts_router
from events.router import router as events_router
from launcher.router import router as launcher_router
from social.router import router as social_router
from community.router import router as community_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()
    yield
    await stop_producer()


app = FastAPI(title="GameMetrics API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (avatars, etc.)
static_dir = Path("/app/static")
static_dir.mkdir(exist_ok=True)
(static_dir / "avatars").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

app.include_router(games_router)
app.include_router(dashboard_router)
app.include_router(dimensiones_router)
app.include_router(store_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(empresa_router)
app.include_router(cart_router)
app.include_router(checkout_router)
app.include_router(library_router)
app.include_router(reviews_router)
app.include_router(refunds_router)
app.include_router(wallet_router)
app.include_router(coupons_router)
app.include_router(gifts_router)
app.include_router(alerts_router)
app.include_router(events_router)
app.include_router(launcher_router)
app.include_router(social_router)
app.include_router(community_router)

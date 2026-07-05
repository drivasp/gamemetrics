from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared.kafka_producer import start_producer, stop_producer

from auth.router import router as auth_router
from tienda.router import router as tienda_router
from wishlist.router import router as wishlist_router
from carrito.router import router as carrito_router
from biblioteca.router import router as biblioteca_router
from resenas.router import router as resenas_router
from dimensiones.router import router as dimensiones_router
from empresa.router import router as empresa_router
from wallet.router import router as wallet_router
from checkout.router import router as checkout_router
from coupons.router import router as coupons_router
from refunds.router import router as refunds_router
from gifts.router import router as gifts_router
from launcher.router import router as launcher_router
from social.router import router as social_router
from community.router import router as community_router
from events.router import router as events_router
from alerts.router import router as alerts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()
    yield
    await stop_producer()


app = FastAPI(title="GameMetrics API — Operativo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)
(static_dir / "avatars").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(auth_router)
app.include_router(tienda_router)
app.include_router(wishlist_router)
app.include_router(carrito_router)
app.include_router(biblioteca_router)
app.include_router(resenas_router)
app.include_router(dimensiones_router)
app.include_router(empresa_router)
app.include_router(wallet_router)
app.include_router(checkout_router)
app.include_router(coupons_router)
app.include_router(refunds_router)
app.include_router(gifts_router)
app.include_router(launcher_router)
app.include_router(social_router)
app.include_router(community_router)
app.include_router(events_router)
app.include_router(alerts_router)

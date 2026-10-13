from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, queue, rooms, tracks
from app.config import settings
from app.core.clock import now_ms
from app.realtime import ticker
from app.realtime.hub import hub
from app.realtime.ws import router as ws_router
from app.services import rooms as rooms_service
from app.services import tracks as tracks_service

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s"
)
log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    tracks_service.load_catalog()
    task = ticker.start()
    log.info("Каталог: %d треков в %s", len(tracks_service.list_tracks()), settings.catalog_dir)
    log.info("Originы для cookie-сессии: %s", ", ".join(settings.cors_origins))
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


settings.catalog_dir.mkdir(parents=True, exist_ok=True)
settings.data_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Совместное прослушивание музыки: комнаты, очередь, синхронизация по WebSocket.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(tracks.router)
app.include_router(queue.router)
app.include_router(ws_router)

app.mount("/media", StaticFiles(directory=settings.catalog_dir), name="media")


@app.get("/health", tags=["service"])
async def health() -> dict:
    return {
        "status": "ok",
        "server_time": now_ms(),
        "tracks": len(tracks_service.list_tracks()),
        "sockets": hub.total(),
        **rooms_service.room_stats(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
    )
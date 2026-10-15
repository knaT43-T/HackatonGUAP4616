from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import auth, queue, rooms, tracks
from app.config import settings
from app.core import metrics
from app.core.clock import now_ms
from app.core.logging import resolve_level, setup_logging
from app.realtime import ticker
from app.realtime.hub import hub
from app.realtime.ws import router as ws_router
from app.services import rooms as rooms_service
from app.services import tracks as tracks_service

setup_logging()
log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    tracks_service.load_catalog()
    task = ticker.start()
    log.info("Каталог: %d треков в %s", len(tracks_service.list_tracks()), settings.catalog_dir)
    log.info("Originы для cookie-сессии: %s", ", ".join(settings.cors_origins))
    if not settings.access_log:
        log.info("Access-лог выключен (ACCESS_LOG=false)")
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
    version=__version__,
    description="Совместное прослушивание музыки: комнаты, очередь, синхронизация по WebSocket.",
    lifespan=lifespan,
)


def _route_template(request: Request) -> str:
    """Шаблон маршрута для метрик: /api/rooms/{room_id}, а не сырой URL."""

    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    """Считает запросы для /metrics и гарантированно отвечает на сбои.

    Это последний рубеж обработки ошибок: исключение логируется с
    трейсбеком, попадает в счётчик и превращается в JSON 500.
    """

    try:
        response = await call_next(request)
    except Exception as exc:  # последний рубеж: логируем и отвечаем 500
        metrics.observe_request(request.method, _route_template(request), 500)
        log.error("Необработанная ошибка: %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})

    metrics.observe_request(request.method, _route_template(request), response.status_code)
    return response


# CORS добавляется позже middleware выше, значит оказывается СНАРУЖИ:
# все ответы, включая наши 500, получают CORS-заголовки.
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
async def health(response: Response) -> dict:
    """Хелсчек для docker и мониторинга.

    Если рабочие каталоги пропали — отвечаем 503 (контейнер станет
    unhealthy, оркестратор перезапустит сервис).
    """

    checks = {
        "catalog_dir": settings.catalog_dir.is_dir(),
        "data_dir": settings.data_dir.is_dir(),
    }
    healthy = all(checks.values())
    if not healthy:
        response.status_code = 503
    return {
        "status": "ok" if healthy else "degraded",
        "version": __version__,
        "uptime_s": round(metrics.uptime_seconds()),
        "server_time": now_ms(),
        "checks": checks,
        "tracks": len(tracks_service.list_tracks()),
        "sockets": hub.total(),
        "errors_total": metrics.errors_total(),
        **rooms_service.room_stats(),
    }


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint() -> PlainTextResponse:
    """Метрики в формате Prometheus: запросы, ошибки, комнаты, сокеты."""

    stats = rooms_service.room_stats()
    gauges = {
        "app_ws_connections_active": float(hub.total()),
        "app_tracks": float(len(tracks_service.list_tracks())),
        "app_rooms_total": float(stats["rooms"]),
        "app_rooms_playing": float(stats["playing"]),
        "app_participants_connected": float(stats["connections"]),
    }
    return PlainTextResponse(
        metrics.render_prometheus(gauges),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def run() -> None:
    """Запуск одной командой: `python -m app.main` (см. Dockerfile).

    `log_config=None` — uvicorn не переопределяет наше логирование,
    access-лог управляется настройкой ACCESS_LOG.
    """

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_config=None,
        access_log=settings.access_log,
        log_level=resolve_level(settings.log_level).lower(),
    )


if __name__ == "__main__":
    run()

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.core import sessions
from app.realtime.events import queue_event, state_event
from app.realtime.hub import hub
from app.services import playback
from app.services import rooms as rooms_service

log = logging.getLogger("ticker")

SESSION_CLEANUP_EVERY = 60


async def tick_once() -> None:
    for room in rooms_service.all_rooms():
        if playback.tick(room):
            await hub.broadcast(room.id, state_event(room))
            await hub.broadcast(room.id, queue_event(room))

    for room_id in await rooms_service.cleanup_idle_rooms():
        log.info("Комната %s удалена по таймауту", room_id)
        await hub.drop_room(room_id)


async def _run() -> None:
    interval = max(0.1, settings.ticker_interval_ms / 1000)
    counter = 0
    while True:
        try:
            await asyncio.sleep(interval)
            await tick_once()
            counter += 1
            if counter % SESSION_CLEANUP_EVERY == 0:
                sessions.drop_stale_sessions()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Сбой в фоновой задаче")


def start() -> asyncio.Task[None]:
    return asyncio.create_task(_run(), name="room-ticker")
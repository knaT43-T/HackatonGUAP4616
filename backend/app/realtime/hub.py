from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from app.config import settings

log = logging.getLogger("hub")


class Hub:
    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self, room_id: str, participant_id: str, ws: WebSocket
    ) -> WebSocket | None:
        async with self._lock:
            peers = self._rooms.setdefault(room_id, {})
            stale = peers.get(participant_id)
            peers[participant_id] = ws
        return stale

    async def disconnect(self, room_id: str, participant_id: str, ws: WebSocket) -> None:
        async with self._lock:
            peers = self._rooms.get(room_id)
            if not peers:
                return
            if peers.get(participant_id) is ws:
                peers.pop(participant_id, None)
            if not peers:
                self._rooms.pop(room_id, None)

    async def drop_room(self, room_id: str) -> None:
        async with self._lock:
            self._rooms.pop(room_id, None)

    def socket_of(self, room_id: str, participant_id: str) -> WebSocket | None:
        return self._rooms.get(room_id, {}).get(participant_id)

    def count(self, room_id: str) -> int:
        return len(self._rooms.get(room_id, {}))

    def total(self) -> int:
        return sum(len(peers) for peers in self._rooms.values())

    async def send(self, ws: WebSocket, event: dict[str, Any]) -> bool:
        try:
            await asyncio.wait_for(
                ws.send_json(event), timeout=settings.broadcast_timeout_s
            )
            return True
        except Exception:
            return False

    async def broadcast(
        self, room_id: str, event: dict[str, Any], exclude: WebSocket | None = None
    ) -> None:
        targets = [
            (pid, ws)
            for pid, ws in self._rooms.get(room_id, {}).items()
            if ws is not exclude
        ]
        if not targets:
            return
        results = await asyncio.gather(*(self.send(ws, event) for _, ws in targets))
        dead = [(pid, ws) for (pid, ws), ok in zip(targets, results) if not ok]
        if not dead:
            return
        async with self._lock:
            peers = self._rooms.get(room_id)
            if not peers:
                return
            for pid, ws in dead:
                if peers.get(pid) is ws:
                    peers.pop(pid, None)
            if not peers:
                self._rooms.pop(room_id, None)


hub = Hub()
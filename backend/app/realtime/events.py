from __future__ import annotations

from typing import Any

from app.core.clock import now_ms
from app.core.models import Room


def _envelope(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": event_type, "server_time": now_ms(), **payload}


def snapshot_event(room: Room) -> dict[str, Any]:
    return _envelope("snapshot", {"data": room.snapshot_payload()})


def state_event(room: Room) -> dict[str, Any]:
    return _envelope("state", {"state": room.state_payload()})


def queue_event(room: Room) -> dict[str, Any]:
    return _envelope("queue_update", {"queue": room.queue_payload()})


def members_event(room: Room) -> dict[str, Any]:
    return _envelope("members_update", {"members": room.members_payload()})


def system_event(text: str, room: Room | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text}
    if room is not None:
        payload["host_id"] = room.host_id
    return _envelope("system", payload)


def error_event(code: str, message: str) -> dict[str, Any]:
    return _envelope("error", {"code": code, "message": message})


def pong_event(client_time: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if client_time is not None:
        payload["client_time"] = client_time
    return _envelope("pong", payload)


def joined_event(room: Room, participant_id: str, role: str) -> dict[str, Any]:
    return _envelope(
        "joined",
        {"room_id": room.id, "participant_id": participant_id, "role": role},
    )
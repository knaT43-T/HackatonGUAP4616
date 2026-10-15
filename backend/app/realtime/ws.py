from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.core import sessions
from app.core.models import Principal, Room
from app.realtime.events import (
    error_event,
    joined_event,
    members_event,
    pong_event,
    queue_event,
    snapshot_event,
    state_event,
    system_event,
)
from app.realtime.hub import hub
from app.services import playback
from app.services import queue as queue_service
from app.services import rooms as rooms_service

log = logging.getLogger("ws")

router = APIRouter()

WS_NOT_FOUND = 4401
WS_GONE = 4404
HOST_ONLY = "Управлять воспроизведением может только хост комнаты"
NOT_IN_ROOM = "Сначала отправь команду join с room_id"


class Connection:
    __slots__ = ("room",)

    def __init__(self) -> None:
        self.room: Room | None = None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    session_id = websocket.cookies.get(settings.cookie_name) or websocket.query_params.get("pid")
    session = sessions.get_session(session_id)

    await websocket.accept()

    if session is None:
        await websocket.send_json(
            error_event(
                "unauthorized",
                "Сессия не найдена. Сначала вызови POST /api/auth/guest, "
                "cookie придёт сама в браузере.",
            )
        )
        await websocket.close(code=WS_NOT_FOUND)
        return

    principal = sessions.to_principal(session)
    conn = Connection()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(error_event("bad_json", "Не удалось разобрать JSON"))
                continue
            if not isinstance(message, dict):
                await websocket.send_json(error_event("bad_request", "Ожидался JSON-объект"))
                continue
            await _dispatch(websocket, conn, principal, message)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("Необработанная ошибка в WebSocket")
    finally:
        await _leave(websocket, conn, principal, drop=False)


async def _dispatch(
    ws: WebSocket, conn: Connection, principal: Principal, message: dict
) -> None:
    command = str(message.get("type") or "").strip().lower()

    if command == "join":
        await _cmd_join(ws, conn, principal, message)
    elif command == "leave":
        await _cmd_leave(ws, conn, principal)
    elif command == "ping":
        await ws.send_json(pong_event(message.get("client_time")))
    elif command in ("play", "pause", "seek", "skip"):
        await _cmd_playback(ws, conn, principal, command, message)
    elif command == "track_loaded":
        await _cmd_track_loaded(ws, conn, principal, message)
    elif command == "queue_remove":
        await _cmd_queue_remove(ws, conn, principal, message)
    else:
        await ws.send_json(error_event("unknown_command", f"Неизвестная команда: {command!r}"))


async def _cmd_join(
    ws: WebSocket, conn: Connection, principal: Principal, message: dict
) -> None:
    room: Room | None = None
    room_id = message.get("room_id")
    invite_code = message.get("invite_code")
    if room_id:
        room = rooms_service.get_room(str(room_id))
    elif invite_code:
        room = rooms_service.get_room_by_code(str(invite_code))

    if room is None:
        await ws.send_json(error_event("room_not_found", "Комната не найдена"))
        return

    if conn.room is not None:
        await _leave(ws, conn, principal, drop=False)

    participant = rooms_service.attach(room, principal, connected=True)
    rooms_service.ensure_host(room)

    stale = await hub.connect(room.id, principal.id, ws)
    if stale is not None:
        try:
            await stale.close(code=WS_GONE)
        except Exception:
            pass

    conn.room = room
    await ws.send_json(joined_event(room, participant.id, participant.role.value))
    await ws.send_json(snapshot_event(room))
    await hub.broadcast(room.id, members_event(room), exclude=ws)


async def _cmd_leave(ws: WebSocket, conn: Connection, principal: Principal) -> None:
    if conn.room is None:
        await ws.send_json(error_event("not_in_room", NOT_IN_ROOM))
        return
    await _leave(ws, conn, principal, drop=True)
    await ws.send_json(system_event(f"{principal.nickname} вышел из комнаты"))


async def _cmd_playback(
    ws: WebSocket,
    conn: Connection,
    principal: Principal,
    command: str,
    message: dict,
) -> None:
    room = conn.room
    if room is None:
        await ws.send_json(error_event("not_in_room", NOT_IN_ROOM))
        return
    if not room.is_host(principal.id):
        await ws.send_json(error_event("forbidden", HOST_ONLY))
        return

    previous_item = room.current_item_id
    try:
        if command == "play":
            playback.play(room)
        elif command == "pause":
            playback.pause(room)
        elif command == "seek":
            playback.seek(room, int(message.get("position_ms") or 0))
        elif command == "skip":
            playback.skip(room)
    except playback.PlaybackError as exc:
        await ws.send_json(error_event(exc.code, exc.message))
        return

    await hub.broadcast(room.id, state_event(room))
    if room.current_item_id != previous_item:
        await hub.broadcast(room.id, queue_event(room))


async def _cmd_track_loaded(
    ws: WebSocket, conn: Connection, principal: Principal, message: dict
) -> None:
    room = conn.room
    if room is None:
        await ws.send_json(error_event("not_in_room", NOT_IN_ROOM))
        return
    item = room.current_item()
    item_id = str(message.get("item_id") or "")
    duration = message.get("duration_ms")
    if item is None or item.id != item_id or not duration:
        return
    try:
        playback.set_duration(room, item_id, int(duration))
    except playback.PlaybackError:
        return
    await hub.broadcast(room.id, state_event(room))


async def _cmd_queue_remove(
    ws: WebSocket, conn: Connection, principal: Principal, message: dict
) -> None:
    room = conn.room
    if room is None:
        await ws.send_json(error_event("not_in_room", NOT_IN_ROOM))
        return
    if not room.is_host(principal.id):
        await ws.send_json(error_event("forbidden", HOST_ONLY))
        return
    try:
        queue_service.remove_from_queue(room, str(message.get("item_id") or ""))
    except queue_service.QueueError as exc:
        await ws.send_json(error_event(exc.code, exc.message))
        return
    await hub.broadcast(room.id, queue_event(room))


async def _leave(
    ws: WebSocket, conn: Connection, principal: Principal, *, drop: bool
) -> None:
    room = conn.room
    if room is None:
        return
    conn.room = None

    await hub.disconnect(room.id, principal.id, ws)
    if drop:
        rooms_service.drop_participant(room, principal.id)
    else:
        rooms_service.detach(room, principal.id)

    promoted = rooms_service.ensure_host(room)
    await hub.broadcast(room.id, members_event(room))
    if promoted:
        new_host = room.participants.get(promoted)
        nickname = new_host.nickname if new_host else "участник"
        await hub.broadcast(room.id, system_event(f"Управление передано: {nickname}", room))
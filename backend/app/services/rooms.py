from __future__ import annotations

import asyncio

from app.config import settings
from app.core.clock import now_ms
from app.core.models import Participant, Principal, Role, Room, new_id, new_invite_code

_rooms: dict[str, Room] = {}
_rooms_by_code: dict[str, str] = {}
_lock = asyncio.Lock()


class RoomError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_room_name(raw: str | None) -> str:
    name = (raw or "").strip()
    if not name:
        raise RoomError("invalid_name", "Название комнаты не может быть пустым")
    if len(name) > settings.room_name_max_len:
        raise RoomError(
            "invalid_name", f"Название длиннее {settings.room_name_max_len} символов"
        )
    return name


def get_room(room_id: str) -> Room | None:
    return _rooms.get(room_id)


def get_room_by_code(code: str) -> Room | None:
    room_id = _rooms_by_code.get((code or "").strip().upper())
    return _rooms.get(room_id) if room_id else None


def all_rooms() -> list[Room]:
    return list(_rooms.values())


def room_stats() -> dict[str, int]:
    return {
        "rooms": len(_rooms),
        "playing": sum(1 for r in _rooms.values() if r.is_playing),
        "connections": sum(len(r.connected_participants()) for r in _rooms.values()),
    }


async def _unique_invite_code() -> str:
    for _ in range(50):
        code = new_invite_code()
        if code not in _rooms_by_code:
            return code
    raise RoomError("code_collision", "Не удалось выделить код комнаты, попробуй ещё раз")


async def create_room(name: str, principal: Principal) -> Room:
    async with _lock:
        room_id = new_id()
        code = await _unique_invite_code()
        room = Room(
            id=room_id,
            name=name,
            invite_code=code,
            creator_id=principal.id,
            host_id=principal.id,
        )
        room.participants[principal.id] = Participant(
            id=principal.id,
            nickname=principal.nickname,
            role=Role.HOST,
            joined_at=now_ms(),
        )
        _rooms[room_id] = room
        _rooms_by_code[code] = room_id
        return room


async def delete_room(room: Room) -> None:
    async with _lock:
        _rooms.pop(room.id, None)
        _rooms_by_code.pop(room.invite_code, None)


def attach(room: Room, principal: Principal, *, connected: bool = True) -> Participant:
    participant = room.participants.get(principal.id)
    if participant is None:
        participant = Participant(id=principal.id, nickname=principal.nickname)
        room.participants[principal.id] = participant
    else:
        participant.nickname = principal.nickname

    participant.connected = connected
    if principal.id == room.creator_id and connected:
        # Создатель вернулся с открытым сокетом — забирает права хоста
        # (API.md, «Хост вернулся»). Прежнего хоста понижаем, чтобы роль
        # host не висела одновременно на двух участниках.
        previous = room.participants.get(room.host_id)
        if previous is not None and previous.id != participant.id:
            previous.role = Role.LISTENER
        participant.role = Role.HOST
        room.host_id = participant.id
    elif room.is_host(participant.id):
        participant.role = Role.HOST
    else:
        participant.role = Role.LISTENER
    room.touch()
    return participant


def detach(room: Room, participant_id: str) -> None:
    participant = room.participants.get(participant_id)
    if participant is None:
        return
    participant.connected = False
    room.touch()


def drop_participant(room: Room, participant_id: str) -> bool:
    """Убирает участника из комнаты. Создателя тоже: комната живёт до
    idle-очистки, а вернувшись сокетом, он снова получит права хоста."""
    removed = room.participants.pop(participant_id, None) is not None
    if removed:
        room.touch()
    return removed


def ensure_host(room: Room) -> str | None:
    host = room.participants.get(room.host_id) if room.host_id else None
    if host is not None and host.connected:
        return None

    if host is not None:
        host.role = Role.LISTENER

    candidates = sorted(room.connected_participants(), key=lambda p: (p.joined_at, p.id))
    if not candidates:
        room.host_id = ""
        return None

    new_host = candidates[0]
    new_host.role = Role.HOST
    room.host_id = new_host.id
    room.touch()
    return new_host.id


async def cleanup_idle_rooms() -> list[str]:
    ttl_ms = settings.room_idle_ttl_min * 60 * 1000
    now = now_ms()
    removed: list[str] = []
    for room in list(_rooms.values()):
        if room.connected_participants():
            continue
        if now - room.last_active_at < ttl_ms:
            continue
        await delete_room(room)
        removed.append(room.id)
    return removed
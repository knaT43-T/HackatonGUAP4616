from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.core import sessions
from app.core.models import Principal, Room
from app.services import rooms as rooms_service


def get_principal(request: Request) -> Principal:
    session = sessions.get_session(request.cookies.get(settings.cookie_name))
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия не найдена. Вызови POST /api/auth/guest — cookie придёт сама.",
        )
    return sessions.to_principal(session)


def get_room_or_404(room_id: str) -> Room:
    room = rooms_service.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    return room


def require_member(room: Room, principal: Principal) -> None:
    if not room.is_member(principal.id):
        raise HTTPException(status_code=403, detail="Ты не участник этой комнаты")


def require_host(room: Room, principal: Principal) -> None:
    require_member(room, principal)
    if not room.is_host(principal.id):
        raise HTTPException(
            status_code=403, detail="Управлять воспроизведением может только создатель комнаты"
        )
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_principal, get_room_or_404, require_member
from app.core.models import Principal
from app.realtime.events import members_event, system_event
from app.realtime.hub import hub
from app.schemas import CreateRoomRequest, JoinRoomRequest
from app.services import rooms as rooms_service

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.post("")
async def create_room(
    payload: CreateRoomRequest, principal: Principal = Depends(get_principal)
) -> dict:
    try:
        name = rooms_service.normalize_room_name(payload.name)
    except rooms_service.RoomError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    room = await rooms_service.create_room(name, principal)
    return room.snapshot_payload()


@router.post("/join")
async def join_room(
    payload: JoinRoomRequest, principal: Principal = Depends(get_principal)
) -> dict:
    room = rooms_service.get_room_by_code(payload.invite_code)
    if room is None:
        raise HTTPException(status_code=404, detail="Комната не найдена: проверь код в ссылке")
    rooms_service.attach(room, principal, connected=False)
    return room.snapshot_payload()


@router.get("/{room_id}")
async def get_room(
    room_id: str, principal: Principal = Depends(get_principal)
) -> dict:
    room = get_room_or_404(room_id)
    require_member(room, principal)
    return room.snapshot_payload()


@router.get("/{room_id}/members")
async def list_members(
    room_id: str, principal: Principal = Depends(get_principal)
) -> dict:
    room = get_room_or_404(room_id)
    require_member(room, principal)
    return {"members": room.members_payload()}


@router.get("/{room_id}/snapshot")
async def get_snapshot(
    room_id: str, principal: Principal = Depends(get_principal)
) -> dict:
    room = get_room_or_404(room_id)
    require_member(room, principal)
    return room.snapshot_payload()


@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str, principal: Principal = Depends(get_principal)
) -> dict:
    room = get_room_or_404(room_id)
    require_member(room, principal)
    removed = rooms_service.drop_participant(room, principal.id)
    promoted = rooms_service.ensure_host(room)

    if removed:
        await hub.broadcast(room.id, members_event(room))
    if promoted:
        new_host = room.participants.get(promoted)
        nickname = new_host.nickname if new_host else "участник"
        await hub.broadcast(room.id, system_event(f"Управление передано: {nickname}", room))

    payload: dict = {"left": True}
    if promoted:
        payload["new_host_id"] = promoted
    return payload

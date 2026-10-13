from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_principal, get_room_or_404, require_host, require_member
from app.core.models import Principal
from app.realtime.events import queue_event
from app.realtime.hub import hub
from app.schemas import AddToQueueRequest
from app.services import queue as queue_service
from app.services import tracks as tracks_service

router = APIRouter(prefix="/api/rooms", tags=["queue"])


@router.get("/{room_id}/queue")
async def get_queue(
    room_id: str, principal: Principal = Depends(get_principal)
) -> dict:
    room = get_room_or_404(room_id)
    require_member(room, principal)
    return {"queue": room.queue_payload()}


@router.post("/{room_id}/queue", status_code=status.HTTP_201_CREATED)
async def add_to_queue(
    room_id: str,
    payload: AddToQueueRequest,
    principal: Principal = Depends(get_principal),
) -> dict:
    room = get_room_or_404(room_id)
    require_member(room, principal)

    track = tracks_service.get_track(payload.track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Трек не найден")

    item = queue_service.add_to_queue(room, track, principal)
    await hub.broadcast(room.id, queue_event(room))
    return item.to_dict()


@router.delete("/{room_id}/queue/{item_id}")
async def remove_from_queue(
    room_id: str,
    item_id: str,
    principal: Principal = Depends(get_principal),
) -> dict:
    room = get_room_or_404(room_id)
    require_host(room, principal)
    try:
        queue_service.remove_from_queue(room, item_id)
    except queue_service.QueueError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    await hub.broadcast(room.id, queue_event(room))
    return {"removed": item_id}
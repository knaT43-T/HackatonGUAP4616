from __future__ import annotations

from typing import Any

from app.core.models import ItemStatus, Principal, QueueItem, Room, new_id

MAX_QUEUE_HISTORY = 50


class QueueError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def add_to_queue(room: Room, track: dict[str, Any], principal: Principal) -> QueueItem:
    item = QueueItem(
        id=new_id(),
        track_id=track["id"],
        track=track,
        added_by_id=principal.id,
        added_by_name=principal.nickname,
        position=len(room.queue),
        status=ItemStatus.QUEUED,
    )
    room.queue.append(item)
    prune(room)
    room.touch()
    return item


def remove_from_queue(room: Room, item_id: str) -> QueueItem:
    item = next((i for i in room.queue if i.id == item_id), None)
    if item is None:
        raise QueueError("not_found", "Трек не найден в очереди")
    if item.id == room.current_item_id:
        raise QueueError(
            "is_playing", "Сейчас играющий трек нельзя удалить из очереди — используй «Следующий»"
        )
    room.queue.remove(item)
    room.touch()
    return item


def prune(room: Room) -> None:
    if len(room.queue) <= MAX_QUEUE_HISTORY:
        return
    finished = [
        i for i in room.queue if i.status in (ItemStatus.PLAYED, ItemStatus.SKIPPED)
    ]
    finished.sort(key=lambda i: i.position)
    for item in finished[: len(room.queue) - MAX_QUEUE_HISTORY]:
        room.queue.remove(item)
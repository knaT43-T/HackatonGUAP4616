from __future__ import annotations

from app.core.models import ItemStatus, QueueItem, Room


class PlaybackError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _select(room: Room, item: QueueItem) -> None:
    room.current_item_id = item.id
    item.status = ItemStatus.PLAYING
    room.position_ms = 0
    room.bump()


def _stop(room: Room) -> None:
    room.current_item_id = None
    room.is_playing = False
    room.position_ms = 0
    room.bump()


def play(room: Room) -> None:
    if room.is_playing and room.current_item() is not None:
        return
    item = room.current_item()
    if item is None:
        item = room.next_queued()
        if item is None:
            raise PlaybackError("queue_empty", "Очередь пуста — нечего играть")
        room.is_playing = True
        _select(room, item)
        return
    item.status = ItemStatus.PLAYING
    room.is_playing = True
    room.bump()


def pause(room: Room) -> None:
    if not room.is_playing:
        return
    room.position_ms = room.position_now_ms()
    room.is_playing = False
    room.bump()


def seek(room: Room, position_ms: int) -> None:
    item = room.current_item()
    if item is None:
        raise PlaybackError("nothing_playing", "Сейчас ничего не играет")
    target = max(0, int(position_ms))
    if item.duration_ms:
        target = min(target, item.duration_ms)
    room.position_ms = target
    room.bump()


def skip(room: Room) -> None:
    item = room.current_item()
    if item is None:
        raise PlaybackError("nothing_playing", "Сейчас ничего не играет")
    item.status = ItemStatus.SKIPPED
    _advance(room)


def _advance(room: Room) -> None:
    nxt = room.next_queued()
    if nxt is None:
        _stop(room)
        return
    room.is_playing = True
    _select(room, nxt)


def set_duration(room: Room, item_id: str, duration_ms: int) -> QueueItem:
    item = next((i for i in room.queue if i.id == item_id), None)
    if item is None:
        raise PlaybackError("not_found", "Трек не найден в очереди")
    if duration_ms and duration_ms > 0:
        item.duration_ms = int(duration_ms)
    room.touch()
    return item


def tick(room: Room) -> bool:
    if not room.is_playing:
        return False
    item = room.current_item()
    if item is None or not item.duration_ms:
        return False
    if room.position_now_ms() < item.duration_ms:
        return False
    item.status = ItemStatus.PLAYED
    _advance(room)
    return True
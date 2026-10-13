from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.clock import effective_position_ms, now_ms

INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
INVITE_LENGTH = 8


def new_id() -> str:
    return secrets.token_hex(8)


def new_invite_code() -> str:
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_LENGTH))


class Role(str, Enum):
    HOST = "host"
    LISTENER = "listener"


class ItemStatus(str, Enum):
    QUEUED = "queued"
    PLAYING = "playing"
    PLAYED = "played"
    SKIPPED = "skipped"


@dataclass
class Principal:
    id: str
    nickname: str


@dataclass
class Participant:
    id: str
    nickname: str
    role: Role = Role.LISTENER
    connected: bool = False
    joined_at: int = field(default_factory=now_ms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nickname": self.nickname,
            "role": self.role.value,
            "connected": self.connected,
            "joined_at": self.joined_at,
        }


@dataclass
class QueueItem:
    id: str
    track_id: str
    track: dict[str, Any]
    added_by_id: str
    added_by_name: str
    position: int
    status: ItemStatus = ItemStatus.QUEUED
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "track_id": self.track_id,
            "track": self.track,
            "added_by_id": self.added_by_id,
            "added_by_name": self.added_by_name,
            "position": self.position,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
        }


@dataclass
class Room:
    id: str
    name: str
    invite_code: str
    creator_id: str
    host_id: str
    queue: list[QueueItem] = field(default_factory=list)
    current_item_id: str | None = None
    is_playing: bool = False
    position_ms: int = 0
    position_updated_at: int = field(default_factory=now_ms)
    version: int = 0
    participants: dict[str, Participant] = field(default_factory=dict)
    created_at: int = field(default_factory=now_ms)
    last_active_at: int = field(default_factory=now_ms)

    def current_item(self) -> QueueItem | None:
        for item in self.queue:
            if item.id == self.current_item_id:
                return item
        return None

    def next_queued(self) -> QueueItem | None:
        return next((i for i in self.queue if i.status is ItemStatus.QUEUED), None)

    def is_host(self, participant_id: str) -> bool:
        return self.host_id == participant_id

    def is_member(self, participant_id: str) -> bool:
        return participant_id in self.participants

    def connected_participants(self) -> list[Participant]:
        return [p for p in self.participants.values() if p.connected]

    def position_now_ms(self) -> int:
        return effective_position_ms(
            self.position_ms, self.position_updated_at, self.is_playing
        )

    def touch(self) -> None:
        self.last_active_at = now_ms()

    def bump(self) -> None:
        self.version += 1
        self.position_updated_at = now_ms()
        self.last_active_at = now_ms()

    def state_payload(self) -> dict[str, Any]:
        item = self.current_item()
        return {
            "room_id": self.id,
            "item_id": self.current_item_id,
            "track_id": item.track_id if item else None,
            "track": item.track if item else None,
            "is_playing": self.is_playing,
            "position_ms": self.position_ms,
            "updated_at": self.position_updated_at,
            "duration_ms": item.duration_ms if item else None,
            "version": self.version,
            "host_id": self.host_id,
        }

    def queue_payload(self) -> list[dict[str, Any]]:
        return [i.to_dict() for i in sorted(self.queue, key=lambda i: i.position)]

    def members_payload(self) -> list[dict[str, Any]]:
        return [
            p.to_dict()
            for p in sorted(self.participants.values(), key=lambda p: p.joined_at)
        ]

    def snapshot_payload(self) -> dict[str, Any]:
        return {
            "room": {
                "id": self.id,
                "name": self.name,
                "invite_code": self.invite_code,
                "creator_id": self.creator_id,
                "host_id": self.host_id,
                "created_at": self.created_at,
            },
            "state": self.state_payload(),
            "queue": self.queue_payload(),
            "members": self.members_payload(),
        }
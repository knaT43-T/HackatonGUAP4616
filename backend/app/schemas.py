from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import settings


class GuestRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=settings.nickname_max_len)


class CreateRoomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=settings.room_name_max_len)


class JoinRoomRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=16)


class AddToQueueRequest(BaseModel):
    track_id: str = Field(min_length=1)

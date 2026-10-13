from __future__ import annotations

from pydantic import BaseModel, Field


class GuestRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=64)


class CreateRoomRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class JoinRoomRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=16)


class AddToQueueRequest(BaseModel):
    track_id: str = Field(min_length=1)
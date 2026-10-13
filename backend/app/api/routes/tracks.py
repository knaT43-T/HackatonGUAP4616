from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_principal
from app.config import settings
from app.core.models import Principal
from app.services import tracks as tracks_service

router = APIRouter(prefix="/api/tracks", tags=["tracks"])

CHUNK_SIZE = 1024 * 1024


@router.post("/upload")
async def upload_track(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    artist: str | None = Form(default=None),
    principal: Principal = Depends(get_principal),
) -> dict:
    buffer = bytearray()
    limit = settings.upload_max_bytes
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        if len(buffer) + len(chunk) > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Файл больше {settings.upload_max_mb} МБ",
            )
        buffer.extend(chunk)

    resolved_title = (title or "").strip() or Path(file.filename or "").stem or "Без названия"
    resolved_artist = (artist or "").strip()

    try:
        return await tracks_service.save_upload(
            original_name=file.filename or "",
            content_type=file.content_type,
            data=bytes(buffer),
            title=resolved_title,
            artist=resolved_artist,
            uploaded_by=principal.nickname,
        )
    except tracks_service.TrackError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc


@router.get("")
async def list_tracks() -> dict:
    return {"tracks": tracks_service.list_tracks()}


@router.get("/{track_id}")
async def get_track(track_id: str) -> dict:
    track = tracks_service.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Трек не найден")
    return track
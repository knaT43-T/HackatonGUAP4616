from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.clock import now_ms
from app.core.models import new_id

_catalog: dict[str, dict[str, Any]] = {}
_lock = asyncio.Lock()


class TrackError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def load_catalog() -> None:
    global _catalog
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.catalog_dir.mkdir(parents=True, exist_ok=True)
    if not settings.tracks_file.exists():
        _catalog = {}
        return
    try:
        raw = json.loads(settings.tracks_file.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        raw = {}
    _catalog = {t["id"]: t for t in raw.get("tracks", []) if t.get("id")}


def _write_sync() -> None:
    payload = {"tracks": sorted(_catalog.values(), key=lambda t: t["created_at"])}
    tmp = settings.data_dir / "tracks.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    os.replace(tmp, settings.tracks_file)


async def _persist() -> None:
    await asyncio.to_thread(_write_sync)


def list_tracks() -> list[dict[str, Any]]:
    return sorted(_catalog.values(), key=lambda t: t["created_at"], reverse=True)


def get_track(track_id: str) -> dict[str, Any] | None:
    return _catalog.get(track_id)


async def delete_track(track_id: str) -> bool:
    track = _catalog.get(track_id)
    if track is None:
        return False
    async with _lock:
        _catalog.pop(track_id, None)
        await _persist()
    path = settings.catalog_dir / track["filename"]
    if path.exists():
        await asyncio.to_thread(path.unlink)
    return True


def _validate(filename: str, content_type: str | None, size: int) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in settings.allowed_audio_ext:
        allowed = ", ".join(sorted(settings.allowed_audio_ext))
        raise TrackError(
            "unsupported_format", f"Неподдерживаемый формат {ext or 'без расширения'}. Разрешено: {allowed}"
        )
    if size > settings.upload_max_bytes:
        raise TrackError(
            "too_large", f"Файл больше {settings.upload_max_mb} МБ"
        )
    if content_type and not (
        content_type.startswith("audio/")
        or content_type == "application/octet-stream"
    ):
        raise TrackError("unsupported_format", f"Это не аудиофайл ({content_type})")
    return ext


async def save_upload(
    *,
    original_name: str,
    content_type: str | None,
    data: bytes,
    title: str,
    artist: str,
    uploaded_by: str,
) -> dict[str, Any]:
    ext = _validate(original_name, content_type, len(data))
    if not data:
        raise TrackError("empty_file", "Файл пустой")

    track_id = new_id()
    stored_name = f"{track_id}{ext}"
    target = settings.catalog_dir / stored_name

    def _write() -> None:
        target.write_bytes(data)

    try:
        await asyncio.to_thread(_write)
    except OSError as exc:
        raise TrackError("write_failed", f"Не удалось сохранить файл: {exc}") from exc

    record: dict[str, Any] = {
        "id": track_id,
        "title": title,
        "artist": artist,
        "filename": stored_name,
        "original_name": original_name,
        "mime": content_type or f"audio/{ext.lstrip('.')}",
        "size": len(data),
        "uploaded_by": uploaded_by,
        "created_at": now_ms(),
        "url": f"/media/{stored_name}",
    }

    async with _lock:
        _catalog[track_id] = record
        await _persist()
    return record
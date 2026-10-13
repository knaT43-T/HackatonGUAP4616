from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Слушаем вместе"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    cookie_name: str = "pid"
    session_ttl_days: int = 30
    nickname_max_len: int = 32

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    catalog_dir: Path = Path("catalog")
    data_dir: Path = Path("data")
    upload_max_mb: int = 50
    allowed_audio_ext: set[str] = {
        ".mp3",
        ".wav",
        ".ogg",
        ".oga",
        ".opus",
        ".m4a",
        ".aac",
        ".flac",
        ".webm",
        ".aiff",
    }

    room_idle_ttl_min: int = 30
    ticker_interval_ms: int = 1000
    broadcast_timeout_s: float = 5.0

    @property
    def tracks_file(self) -> Path:
        return self.data_dir / "tracks.json"

    @property
    def upload_max_bytes(self) -> int:
        return self.upload_max_mb * 1024 * 1024

    def model_post_init(self, context: object) -> None:
        for name in ("catalog_dir", "data_dir"):
            path = getattr(self, name)
            if not path.is_absolute():
                setattr(self, name, (BASE_DIR / path).resolve())


settings = Settings()
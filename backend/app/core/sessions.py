from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.core.clock import now_ms
from app.core.models import Principal, new_id


@dataclass
class Session:
    id: str
    nickname: str
    created_at: int
    last_seen_at: int


_sessions: dict[str, Session] = {}


def normalize_nickname(raw: str | None) -> str:
    nickname = (raw or "").strip()
    if not nickname:
        raise ValueError("Ник не может быть пустым")
    if len(nickname) > settings.nickname_max_len:
        raise ValueError(f"Ник длиннее {settings.nickname_max_len} символов")
    return nickname


def create_session(nickname: str) -> Session:
    session = Session(
        id=new_id(),
        nickname=nickname,
        created_at=now_ms(),
        last_seen_at=now_ms(),
    )
    _sessions[session.id] = session
    return session


def get_session(session_id: str | None) -> Session | None:
    if not session_id:
        return None
    session = _sessions.get(session_id)
    if session is not None:
        session.last_seen_at = now_ms()
    return session


def rename_session(session: Session, nickname: str) -> None:
    session.nickname = nickname


def to_principal(session: Session) -> Principal:
    return Principal(id=session.id, nickname=session.nickname)


def drop_stale_sessions() -> int:
    ttl_ms = settings.session_ttl_days * 24 * 60 * 60 * 1000
    cutoff = now_ms() - ttl_ms
    stale = [sid for sid, s in _sessions.items() if s.last_seen_at < cutoff]
    for sid in stale:
        _sessions.pop(sid, None)
    return len(stale)
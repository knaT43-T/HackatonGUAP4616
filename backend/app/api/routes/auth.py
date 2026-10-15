from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_principal
from app.config import settings
from app.core import sessions
from app.core.models import Principal
from app.schemas import GuestRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/guest")
async def enter_as_guest(payload: GuestRequest, response: Response) -> dict:
    try:
        nickname = sessions.normalize_nickname(payload.nickname)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session = sessions.create_session(nickname)
    response.set_cookie(
        key=settings.cookie_name,
        value=session.id,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return {"participant_id": session.id, "nickname": session.nickname}


@router.get("/me")
async def whoami(principal: Principal = Depends(get_principal)) -> dict:
    return {"participant_id": principal.id, "nickname": principal.nickname}

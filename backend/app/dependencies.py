from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.database import utc_now
from app.models import SessionRecord, User
from app.security import hash_session_token
from app.services.storage import SupabaseStorageService


@dataclass(slots=True)
class AuthContext:
    session: SessionRecord
    user: User


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request):
    session_factory = request.app.state.session_factory
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_storage_service(request: Request) -> SupabaseStorageService:
    return request.app.state.storage_service


def get_optional_auth_context(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthContext | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None

    token_hash = hash_session_token(token)
    session = db.scalar(
        select(SessionRecord)
        .options(joinedload(SessionRecord.user))
        .where(SessionRecord.session_token_hash == token_hash)
        .where(SessionRecord.revoked_at.is_(None))
        .where(SessionRecord.expires_at > utc_now())
    )
    if session is None:
        return None
    return AuthContext(session=session, user=session.user)


def require_auth_context(
    auth_context: AuthContext | None = Depends(get_optional_auth_context),
) -> AuthContext:
    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return auth_context


from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import utc_now
from app.dependencies import AuthContext, get_db, get_optional_auth_context, get_settings, require_auth_context
from app.enums import LoginMethod
from app.ids import create_public_id
from app.models import SessionRecord, User
from app.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordResetRequest,
    ForgotPasswordStartRequest,
    ForgotPasswordStartResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    SessionStateResponse,
)
from app.security import (
    generate_session_token,
    hash_password,
    hash_security_answer,
    hash_session_token,
    verify_password,
    verify_security_answer,
)
from app.serializers import serialize_private_profile
from app.stats import get_private_profile_counts
from app.validation import validate_account_id, validate_username

router = APIRouter(tags=["auth"])


def _set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.secure_cookies or settings.is_production,
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        expires=settings.session_max_age_seconds,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/", samesite="lax")


def _build_auth_response(message: str, user: User, db: Session) -> AuthResponse:
    posts_count, favorites_count, likes_count = get_private_profile_counts(db, user.id)
    return AuthResponse(
        message=message,
        user=serialize_private_profile(
            user,
            posts_count=posts_count,
            favorites_count=favorites_count,
            likes_count=likes_count,
        ),
    )


@router.post("/auth/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    if db.scalar(select(User.id).where(User.account_id == payload.account_id)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account ID already exists.")
    if db.scalar(select(User.id).where(User.username == payload.username)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    user = User(
        id=create_public_id("u"),
        account_id=payload.account_id,
        username=payload.username,
        password_hash=hash_password(payload.password),
        security_question=payload.security_question,
        security_answer_hash=hash_security_answer(payload.security_answer),
    )
    db.add(user)
    db.commit()
    return MessageResponse(message="Registration successful.")


@router.post("/auth/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    if payload.login_method == LoginMethod.ACCOUNT_ID:
        identifier = validate_account_id(payload.identifier)
        user = db.scalar(select(User).where(User.account_id == identifier))
    else:
        identifier = validate_username(payload.identifier)
        user = db.scalar(select(User).where(User.username == identifier))

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password or identifier.")

    session_token = generate_session_token()
    session = SessionRecord(
        id=str(uuid4()),
        user_id=user.id,
        session_token_hash=hash_session_token(session_token),
        expires_at=utc_now() + timedelta(seconds=settings.session_max_age_seconds),
    )
    db.add(session)
    db.commit()

    _set_session_cookie(response, settings, session_token)
    return _build_auth_response("Login successful.", user, db)


@router.post("/auth/logout", response_model=MessageResponse)
def logout(
    response: Response,
    auth_context: AuthContext | None = Depends(get_optional_auth_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    if auth_context is not None and auth_context.session.revoked_at is None:
        auth_context.session.revoked_at = utc_now()
        db.add(auth_context.session)
        db.commit()

    _clear_session_cookie(response, settings)
    return MessageResponse(message="Logout successful.")


@router.get("/auth/me", response_model=SessionStateResponse)
def auth_me(
    auth_context: AuthContext | None = Depends(get_optional_auth_context),
    db: Session = Depends(get_db),
) -> SessionStateResponse:
    if auth_context is None:
        return SessionStateResponse(authenticated=False, user=None)

    posts_count, favorites_count, likes_count = get_private_profile_counts(db, auth_context.user.id)
    return SessionStateResponse(
        authenticated=True,
        user=serialize_private_profile(
            auth_context.user,
            posts_count=posts_count,
            favorites_count=favorites_count,
            likes_count=likes_count,
        ),
    )


@router.post("/auth/forgot-password/start", response_model=ForgotPasswordStartResponse)
def forgot_password_start(
    payload: ForgotPasswordStartRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordStartResponse:
    account_id = validate_account_id(payload.account_id)
    user = db.scalar(select(User).where(User.account_id == account_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account ID not found.")
    return ForgotPasswordStartResponse(security_question=user.security_question)


@router.post("/auth/forgot-password/reset", response_model=MessageResponse)
def forgot_password_reset(
    payload: ForgotPasswordResetRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = db.scalar(select(User).where(User.account_id == payload.account_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account ID not found.")
    if not verify_security_answer(payload.security_answer, user.security_answer_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Security answer is incorrect.")

    user.password_hash = hash_password(payload.new_password)
    user.updated_at = utc_now()
    db.add(user)
    db.commit()
    return MessageResponse(message="Password reset successful.")


@router.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> MessageResponse:
    if not verify_password(payload.old_password, auth_context.user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Old password is incorrect.")

    auth_context.user.password_hash = hash_password(payload.new_password)
    auth_context.user.updated_at = utc_now()
    db.add(auth_context.user)
    db.commit()
    return MessageResponse(message="Password changed successfully.")

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import utc_now
from app.dependencies import AuthContext, get_db, get_storage_service, require_auth_context
from app.models import Favorite, Like, Post, User
from app.schemas import MessageResponse, PaginatedPosts, PrivateProfile, PublicAuthorProfile, UpdateProfileRequest
from app.serializers import serialize_post_summary, serialize_private_profile, serialize_user_summary
from app.services.storage import StorageServiceError, SupabaseStorageService
from app.stats import get_private_profile_counts, get_total_likes_received
from app.validation import validate_avatar_upload

router = APIRouter(tags=["users"])


def _pagination(page: int, page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 24)
    return page, page_size


def _post_loader_options():
    return (
        selectinload(Post.author),
        selectinload(Post.media),
        selectinload(Post.likes),
        selectinload(Post.favorites),
    )


def _load_post_page(
    db: Session,
    base_query,
    count_query,
    *,
    page: int,
    page_size: int,
) -> PaginatedPosts:
    page, page_size = _pagination(page, page_size)
    total = int(db.scalar(count_query) or 0)
    posts = list(
        db.scalars(
            base_query.offset((page - 1) * page_size).limit(page_size)
        ).all()
    )
    return PaginatedPosts(
        items=[serialize_post_summary(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=PublicAuthorProfile)
def get_public_user(
    user_id: str,
    db: Session = Depends(get_db),
) -> PublicAuthorProfile:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    posts_count = int(db.scalar(select(func.count(Post.id)).where(Post.author_id == user_id)) or 0)
    total_likes_received = get_total_likes_received(db, user_id)
    return PublicAuthorProfile(
        user=serialize_user_summary(user),
        posts_count=posts_count,
        total_likes_received=total_likes_received,
    )


@router.get("/users/{user_id}/posts", response_model=PaginatedPosts)
def get_public_user_posts(
    user_id: str,
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
) -> PaginatedPosts:
    if db.scalar(select(User.id).where(User.id == user_id)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    base_query = (
        select(Post)
        .where(Post.author_id == user_id)
        .order_by(Post.published_at.desc())
        .options(*_post_loader_options())
    )
    count_query = select(func.count(Post.id)).where(Post.author_id == user_id)
    return _load_post_page(db, base_query, count_query, page=page, page_size=page_size)


@router.get("/me", response_model=PrivateProfile)
def get_me(
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> PrivateProfile:
    posts_count, favorites_count, likes_count = get_private_profile_counts(db, auth_context.user.id)
    return serialize_private_profile(
        auth_context.user,
        posts_count=posts_count,
        favorites_count=favorites_count,
        likes_count=likes_count,
    )


@router.patch("/me/profile", response_model=PrivateProfile)
def update_profile(
    payload: UpdateProfileRequest,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> PrivateProfile:
    existing = db.scalar(select(User).where(User.username == payload.username))
    if existing is not None and existing.id != auth_context.user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    auth_context.user.username = payload.username
    auth_context.user.bio = payload.bio
    auth_context.user.updated_at = utc_now()
    db.add(auth_context.user)
    db.commit()
    db.refresh(auth_context.user)

    posts_count, favorites_count, likes_count = get_private_profile_counts(db, auth_context.user.id)
    return serialize_private_profile(
        auth_context.user,
        posts_count=posts_count,
        favorites_count=favorites_count,
        likes_count=likes_count,
    )


@router.post("/me/avatar", response_model=PrivateProfile)
def upload_avatar(
    avatar: UploadFile = File(...),
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
    storage_service: SupabaseStorageService = Depends(get_storage_service),
) -> PrivateProfile:
    validate_avatar_upload(avatar)

    try:
        if auth_context.user.avatar_storage_path:
            storage_service.remove_object(storage_service.settings.storage_avatars_bucket, auth_context.user.avatar_storage_path)

        extension = Path(avatar.filename or "avatar.jpg").suffix.lower()
        storage_path = f"users/{auth_context.user.id}/avatar-{uuid4().hex}{extension}"
        stored = storage_service.upload_upload_file(storage_service.settings.storage_avatars_bucket, storage_path, avatar)
    except StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    auth_context.user.avatar_url = stored.public_url
    auth_context.user.avatar_storage_path = stored.storage_path
    auth_context.user.updated_at = utc_now()
    db.add(auth_context.user)
    db.commit()
    db.refresh(auth_context.user)

    posts_count, favorites_count, likes_count = get_private_profile_counts(db, auth_context.user.id)
    return serialize_private_profile(
        auth_context.user,
        posts_count=posts_count,
        favorites_count=favorites_count,
        likes_count=likes_count,
    )


@router.delete("/me/avatar", response_model=MessageResponse)
def delete_avatar(
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
    storage_service: SupabaseStorageService = Depends(get_storage_service),
) -> MessageResponse:
    try:
        if auth_context.user.avatar_storage_path:
            storage_service.remove_object(storage_service.settings.storage_avatars_bucket, auth_context.user.avatar_storage_path)
    except StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    auth_context.user.avatar_url = None
    auth_context.user.avatar_storage_path = None
    auth_context.user.updated_at = utc_now()
    db.add(auth_context.user)
    db.commit()
    return MessageResponse(message="Avatar removed.")


@router.get("/me/posts", response_model=PaginatedPosts)
def get_my_posts(
    page: int = 1,
    page_size: int = 12,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> PaginatedPosts:
    base_query = (
        select(Post)
        .where(Post.author_id == auth_context.user.id)
        .order_by(Post.published_at.desc())
        .options(*_post_loader_options())
    )
    count_query = select(func.count(Post.id)).where(Post.author_id == auth_context.user.id)
    return _load_post_page(db, base_query, count_query, page=page, page_size=page_size)


@router.get("/me/favorites", response_model=PaginatedPosts)
def get_my_favorites(
    page: int = 1,
    page_size: int = 12,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> PaginatedPosts:
    page, page_size = _pagination(page, page_size)
    total = int(db.scalar(select(func.count(Favorite.id)).where(Favorite.user_id == auth_context.user.id)) or 0)
    posts = list(
        db.scalars(
            select(Post)
            .join(Favorite, Favorite.post_id == Post.id)
            .where(Favorite.user_id == auth_context.user.id)
            .order_by(Favorite.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(*_post_loader_options())
        ).all()
    )
    return PaginatedPosts(
        items=[serialize_post_summary(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/me/likes", response_model=PaginatedPosts)
def get_my_likes(
    page: int = 1,
    page_size: int = 12,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> PaginatedPosts:
    page, page_size = _pagination(page, page_size)
    total = int(db.scalar(select(func.count(Like.id)).where(Like.user_id == auth_context.user.id)) or 0)
    posts = list(
        db.scalars(
            select(Post)
            .join(Like, Like.post_id == Post.id)
            .where(Like.user_id == auth_context.user.id)
            .order_by(Like.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(*_post_loader_options())
        ).all()
    )
    return PaginatedPosts(
        items=[serialize_post_summary(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
    )

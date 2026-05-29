from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import utc_now
from app.dependencies import AuthContext, get_db, get_optional_auth_context, get_storage_service, require_auth_context
from app.enums import MediaType, PostCategory
from app.ids import create_public_id
from app.models import Comment, Favorite, Like, Post, PostMedia, User
from app.schemas import CommentCreateRequest, CommentsResponse, InteractionState, MessageResponse, PaginatedPosts, PostDetail
from app.serializers import serialize_comment, serialize_post_detail, serialize_post_summary
from app.services.media import extract_video_thumbnail_bytes
from app.services.storage import StorageServiceError, SupabaseStorageService
from app.stats import get_post_comment_count
from app.validation import (
    MAX_TOTAL_POST_MEDIA_BYTES,
    clean_text,
    get_upload_size,
    parse_category,
    parse_json_array,
    validate_image_upload,
    validate_video_upload,
)

router = APIRouter(tags=["posts"])


def _post_loader_options():
    return (
        selectinload(Post.author),
        selectinload(Post.media),
        selectinload(Post.likes),
        selectinload(Post.favorites),
    )


def _pagination(page: int, page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 24)
    return page, page_size


def _require_post(
    db: Session,
    post_id: str,
) -> Post:
    post = db.scalar(select(Post).where(Post.id == post_id).options(*_post_loader_options()))
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    return post


def _ensure_owner(auth_context: AuthContext, post: Post) -> None:
    if post.author_id != auth_context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized action.")


def _normalize_upload_list(images: list[UploadFile] | None) -> list[UploadFile]:
    return [image for image in (images or []) if image and image.filename]


def _normalize_video(video: UploadFile | None) -> UploadFile | None:
    if video is None or not video.filename:
        return None
    return video


def _validate_textual_fields(title: str, body: str | None, category: str) -> tuple[str, str | None, PostCategory]:
    title = title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Title is required.")
    body = clean_text(body)
    parsed_category = parse_category(category)
    return title, body, parsed_category


def _recalculate_cover(post: Post, default_cover_url: str) -> None:
    images = sorted((media for media in post.media if media.type == MediaType.IMAGE), key=lambda item: item.sort_order)
    if images:
        post.cover_url = images[0].url
        post.cover_source = "image"
        return

    video = next((media for media in post.media if media.type == MediaType.VIDEO), None)
    if video and video.thumbnail_url:
        post.cover_url = video.thumbnail_url
        post.cover_source = "video"
        return

    post.cover_url = default_cover_url
    post.cover_source = "default"


def _delete_storage_object(
    storage_service: SupabaseStorageService,
    bucket: str,
    path: str | None,
) -> None:
    if path:
        storage_service.remove_object(bucket, path)


def _delete_post_media_storage(storage_service: SupabaseStorageService, media: PostMedia) -> None:
    bucket = storage_service.settings.storage_posts_bucket
    _delete_storage_object(storage_service, bucket, media.storage_path)
    if media.thumbnail_storage_path:
        _delete_storage_object(storage_service, bucket, media.thumbnail_storage_path)


def _try_upload_video_thumbnail(
    storage_service: SupabaseStorageService,
    upload: UploadFile,
    storage_path: str,
) -> tuple[str | None, str | None]:
    try:
        thumbnail_bytes = extract_video_thumbnail_bytes(
            upload,
            ffmpeg_path=storage_service.settings.ffmpeg_path,
            ffprobe_path=storage_service.settings.ffprobe_path,
        )
        stored_thumbnail = storage_service.upload_bytes(
            storage_service.settings.storage_posts_bucket,
            storage_path,
            thumbnail_bytes,
            content_type="image/jpeg",
        )
    except Exception:
        return None, None

    return stored_thumbnail.public_url, stored_thumbnail.storage_path


def _build_interaction_state(db: Session, model, post_id: str, active: bool) -> InteractionState:
    count = int(db.scalar(select(func.count(model.id)).where(model.post_id == post_id)) or 0)
    return InteractionState(active=active, count=count)


@router.get("/posts", response_model=PaginatedPosts)
def list_posts(
    q: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
) -> PaginatedPosts:
    page, page_size = _pagination(page, page_size)

    query = select(Post).options(*_post_loader_options()).join(User, Post.author_id == User.id)
    count_query = select(func.count(Post.id)).join(User, Post.author_id == User.id)

    if q:
        term = f"%{q.strip()}%"
        condition = or_(Post.title.ilike(term), Post.body.ilike(term), User.username.ilike(term))
        query = query.where(condition)
        count_query = count_query.where(condition)

    if category:
        query = query.where(Post.category == parse_category(category))
        count_query = count_query.where(Post.category == parse_category(category))

    query = query.order_by(Post.published_at.desc()).offset((page - 1) * page_size).limit(page_size)
    total = int(db.scalar(count_query) or 0)
    posts = list(db.scalars(query).all())

    return PaginatedPosts(
        items=[serialize_post_summary(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/posts/{post_id}", response_model=PostDetail)
def get_post_detail(
    post_id: str,
    auth_context: AuthContext | None = Depends(get_optional_auth_context),
    db: Session = Depends(get_db),
) -> PostDetail:
    post = _require_post(db, post_id)
    comment_count = get_post_comment_count(db, post.id)
    return serialize_post_detail(
        post,
        current_user_id=auth_context.user.id if auth_context else None,
        comment_count=comment_count,
    )


@router.post("/posts", response_model=PostDetail, status_code=status.HTTP_201_CREATED)
def create_post(
    title: str = Form(...),
    category: str = Form(...),
    body: str | None = Form(default=None),
    images: list[UploadFile] | None = File(default=None),
    video: UploadFile | None = File(default=None),
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
    storage_service: SupabaseStorageService = Depends(get_storage_service),
) -> PostDetail:
    title, body, parsed_category = _validate_textual_fields(title, body, category)
    normalized_images = _normalize_upload_list(images)
    normalized_video = _normalize_video(video)

    image_sizes = [validate_image_upload(image) for image in normalized_images]
    video_size = validate_video_upload(normalized_video) if normalized_video else 0
    total_media_size = sum(image_sizes) + video_size
    if total_media_size > MAX_TOTAL_POST_MEDIA_BYTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Total post media is too large.")
    if not body and not normalized_images and not normalized_video:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Post body, images, or video is required.",
        )

    post = Post(
        id=create_public_id("p"),
        author_id=auth_context.user.id,
        title=title,
        body=body,
        category=parsed_category,
    )
    _recalculate_cover(post, storage_service.settings.default_cover_url)
    db.add(post)

    created_objects: list[str] = []
    try:
        if normalized_images or normalized_video:
            if not storage_service.settings.storage_enabled:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Media storage is not configured.",
                )

        for index, image in enumerate(normalized_images):
            extension = Path(image.filename or "image.jpg").suffix.lower()
            storage_path = f"posts/{post.id}/images/{index + 1}-{uuid4().hex}{extension}"
            stored = storage_service.upload_upload_file(storage_service.settings.storage_posts_bucket, storage_path, image)
            created_objects.append(storage_path)
            post.media.append(
                PostMedia(
                    id=create_public_id("m"),
                    type=MediaType.IMAGE,
                    url=stored.public_url,
                    storage_path=stored.storage_path,
                    mime_type=image.content_type or "application/octet-stream",
                    size_bytes=image_sizes[index],
                    sort_order=index,
                )
            )

        if normalized_video:
            video_extension = Path(normalized_video.filename or "video.mp4").suffix.lower()
            video_storage_path = f"posts/{post.id}/video/{uuid4().hex}{video_extension}"
            thumbnail_storage_path = f"posts/{post.id}/thumbnails/{uuid4().hex}.jpg"
            stored_video = storage_service.upload_upload_file(
                storage_service.settings.storage_posts_bucket,
                video_storage_path,
                normalized_video,
            )
            created_objects.append(video_storage_path)
            thumbnail_url, stored_thumbnail_path = _try_upload_video_thumbnail(
                storage_service,
                normalized_video,
                thumbnail_storage_path,
            )
            if stored_thumbnail_path:
                created_objects.append(stored_thumbnail_path)
            post.media.append(
                PostMedia(
                    id=create_public_id("m"),
                    type=MediaType.VIDEO,
                    url=stored_video.public_url,
                    storage_path=stored_video.storage_path,
                    thumbnail_url=thumbnail_url,
                    thumbnail_storage_path=stored_thumbnail_path,
                    mime_type=normalized_video.content_type or "application/octet-stream",
                    size_bytes=video_size,
                    sort_order=len(normalized_images),
                )
            )
    except StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception:
        for path in created_objects:
            try:
                storage_service.remove_object(storage_service.settings.storage_posts_bucket, path)
            except Exception:
                pass
        raise

    _recalculate_cover(post, storage_service.settings.default_cover_url)
    db.add(post)
    db.commit()
    db.refresh(post)
    post = _require_post(db, post.id)
    return serialize_post_detail(post, current_user_id=auth_context.user.id, comment_count=0)


@router.patch("/posts/{post_id}", response_model=PostDetail)
def update_post(
    post_id: str,
    title: str = Form(...),
    category: str = Form(...),
    body: str | None = Form(default=None),
    existing_image_ids: str | None = Form(default=None),
    remove_video: bool = Form(default=False),
    images: list[UploadFile] | None = File(default=None),
    video: UploadFile | None = File(default=None),
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
    storage_service: SupabaseStorageService = Depends(get_storage_service),
) -> PostDetail:
    post = _require_post(db, post_id)
    _ensure_owner(auth_context, post)

    title, body, parsed_category = _validate_textual_fields(title, body, category)
    normalized_images = _normalize_upload_list(images)
    normalized_video = _normalize_video(video)

    current_images = [media for media in post.media if media.type == MediaType.IMAGE]
    current_video = next((media for media in post.media if media.type == MediaType.VIDEO), None)

    requested_image_ids = parse_json_array(existing_image_ids)
    if requested_image_ids is None:
        kept_images = sorted(current_images, key=lambda item: item.sort_order)
    else:
        if len(requested_image_ids) != len(set(requested_image_ids)):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Duplicate image IDs are not allowed.")
        image_map = {media.id: media for media in current_images}
        missing_ids = [media_id for media_id in requested_image_ids if media_id not in image_map]
        if missing_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown image ID in existing_image_ids.")
        kept_images = [image_map[media_id] for media_id in requested_image_ids]

    removed_images = [media for media in current_images if media not in kept_images]
    keeping_video = current_video if current_video and not remove_video and normalized_video is None else None
    removed_video = current_video if current_video and (remove_video or normalized_video is not None) else None

    new_image_sizes = [validate_image_upload(image) for image in normalized_images]
    new_video_size = validate_video_upload(normalized_video) if normalized_video else 0
    final_media_size = (
        sum(media.size_bytes for media in kept_images)
        + (keeping_video.size_bytes if keeping_video else 0)
        + sum(new_image_sizes)
        + new_video_size
    )
    if final_media_size > MAX_TOTAL_POST_MEDIA_BYTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Total post media is too large.")
    if not body and not kept_images and not keeping_video and not normalized_images and not normalized_video:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Post body, images, or video is required.",
        )

    new_media: list[PostMedia] = []
    created_paths: list[str] = []
    try:
        if normalized_images or normalized_video:
            if not storage_service.settings.storage_enabled:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Media storage is not configured.",
                )

        base_sort_order = len(kept_images)
        for index, image in enumerate(normalized_images):
            extension = Path(image.filename or "image.jpg").suffix.lower()
            storage_path = f"posts/{post.id}/images/{base_sort_order + index + 1}-{uuid4().hex}{extension}"
            stored = storage_service.upload_upload_file(storage_service.settings.storage_posts_bucket, storage_path, image)
            created_paths.append(storage_path)
            new_media.append(
                PostMedia(
                    id=create_public_id("m"),
                    post_id=post.id,
                    type=MediaType.IMAGE,
                    url=stored.public_url,
                    storage_path=stored.storage_path,
                    mime_type=image.content_type or "application/octet-stream",
                    size_bytes=new_image_sizes[index],
                    sort_order=base_sort_order + index,
                )
            )

        replacement_video: PostMedia | None = None
        if normalized_video:
            video_extension = Path(normalized_video.filename or "video.mp4").suffix.lower()
            video_storage_path = f"posts/{post.id}/video/{uuid4().hex}{video_extension}"
            thumbnail_storage_path = f"posts/{post.id}/thumbnails/{uuid4().hex}.jpg"
            stored_video = storage_service.upload_upload_file(
                storage_service.settings.storage_posts_bucket,
                video_storage_path,
                normalized_video,
            )
            created_paths.append(video_storage_path)
            thumbnail_url, stored_thumbnail_path = _try_upload_video_thumbnail(
                storage_service,
                normalized_video,
                thumbnail_storage_path,
            )
            if stored_thumbnail_path:
                created_paths.append(stored_thumbnail_path)
            replacement_video = PostMedia(
                id=create_public_id("m"),
                post_id=post.id,
                type=MediaType.VIDEO,
                url=stored_video.public_url,
                storage_path=stored_video.storage_path,
                thumbnail_url=thumbnail_url,
                thumbnail_storage_path=stored_thumbnail_path,
                mime_type=normalized_video.content_type or "application/octet-stream",
                size_bytes=new_video_size,
                sort_order=len(kept_images) + len(new_media),
            )
    except StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception:
        for path in created_paths:
            try:
                storage_service.remove_object(storage_service.settings.storage_posts_bucket, path)
            except Exception:
                pass
        raise

    try:
        if removed_video:
            _delete_post_media_storage(storage_service, removed_video)
            db.delete(removed_video)
        for removed in removed_images:
            _delete_post_media_storage(storage_service, removed)
            db.delete(removed)
    except StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    post.title = title
    post.body = body
    post.category = parsed_category
    post.updated_at = utc_now()

    for sort_order, media in enumerate(kept_images):
        media.sort_order = sort_order
        db.add(media)

    for index, media in enumerate(new_media, start=len(kept_images)):
        media.sort_order = index
        post.media.append(media)

    if normalized_video and replacement_video:
        replacement_video.sort_order = len(kept_images) + len(new_media)
        post.media.append(replacement_video)

    _recalculate_cover(post, storage_service.settings.default_cover_url)
    db.add(post)
    db.commit()
    db.refresh(post)
    post = _require_post(db, post.id)
    return serialize_post_detail(
        post,
        current_user_id=auth_context.user.id,
        comment_count=get_post_comment_count(db, post.id),
    )


@router.delete("/posts/{post_id}", response_model=MessageResponse)
def delete_post(
    post_id: str,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
    storage_service: SupabaseStorageService = Depends(get_storage_service),
) -> MessageResponse:
    post = _require_post(db, post_id)
    _ensure_owner(auth_context, post)

    try:
        for media in list(post.media):
            _delete_post_media_storage(storage_service, media)
    except StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    db.delete(post)
    db.commit()
    return MessageResponse(message="Post deleted.")


@router.post("/posts/{post_id}/like", response_model=InteractionState)
def like_post(
    post_id: str,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> InteractionState:
    post = _require_post(db, post_id)
    existing = db.scalar(select(Like).where(Like.post_id == post.id, Like.user_id == auth_context.user.id))
    if existing is None:
        db.add(Like(id=create_public_id("l"), post_id=post.id, user_id=auth_context.user.id))
        db.commit()
    return _build_interaction_state(db, Like, post.id, True)


@router.delete("/posts/{post_id}/like", response_model=InteractionState)
def unlike_post(
    post_id: str,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> InteractionState:
    post = _require_post(db, post_id)
    existing = db.scalar(select(Like).where(Like.post_id == post.id, Like.user_id == auth_context.user.id))
    if existing is not None:
        db.delete(existing)
        db.commit()
    return _build_interaction_state(db, Like, post.id, False)


@router.post("/posts/{post_id}/favorite", response_model=InteractionState)
def favorite_post(
    post_id: str,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> InteractionState:
    post = _require_post(db, post_id)
    existing = db.scalar(select(Favorite).where(Favorite.post_id == post.id, Favorite.user_id == auth_context.user.id))
    if existing is None:
        db.add(Favorite(id=create_public_id("f"), post_id=post.id, user_id=auth_context.user.id))
        db.commit()
    return _build_interaction_state(db, Favorite, post.id, True)


@router.delete("/posts/{post_id}/favorite", response_model=InteractionState)
def unfavorite_post(
    post_id: str,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> InteractionState:
    post = _require_post(db, post_id)
    existing = db.scalar(select(Favorite).where(Favorite.post_id == post.id, Favorite.user_id == auth_context.user.id))
    if existing is not None:
        db.delete(existing)
        db.commit()
    return _build_interaction_state(db, Favorite, post.id, False)


@router.get("/posts/{post_id}/comments", response_model=CommentsResponse)
def get_comments(
    post_id: str,
    db: Session = Depends(get_db),
) -> CommentsResponse:
    if db.scalar(select(Post.id).where(Post.id == post_id)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    comments = list(
        db.scalars(
            select(Comment)
            .where(Comment.post_id == post_id, Comment.parent_id.is_(None))
            .order_by(Comment.created_at.asc())
            .options(
                selectinload(Comment.author),
                selectinload(Comment.replies).selectinload(Comment.author),
            )
        ).all()
    )
    return CommentsResponse(items=[serialize_comment(comment) for comment in comments])


@router.post("/posts/{post_id}/comments", response_model=CommentsResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: str,
    payload: CommentCreateRequest,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> CommentsResponse:
    if db.scalar(select(Post.id).where(Post.id == post_id)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    comment = Comment(
        id=create_public_id("c"),
        post_id=post_id,
        author_id=auth_context.user.id,
        body=payload.body,
    )
    db.add(comment)
    db.commit()
    return get_comments(post_id, db)


@router.post("/comments/{comment_id}/replies", response_model=CommentsResponse, status_code=status.HTTP_201_CREATED)
def create_reply(
    comment_id: str,
    payload: CommentCreateRequest,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> CommentsResponse:
    parent = db.scalar(select(Comment).where(Comment.id == comment_id))
    if parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    if parent.parent_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Replies can only target main comments.",
        )

    reply = Comment(
        id=create_public_id("c"),
        post_id=parent.post_id,
        author_id=auth_context.user.id,
        parent_id=parent.id,
        body=payload.body,
    )
    db.add(reply)
    db.commit()
    return get_comments(parent.post_id, db)


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
def delete_comment(
    comment_id: str,
    auth_context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
) -> MessageResponse:
    comment = db.scalar(select(Comment).where(Comment.id == comment_id))
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    if comment.author_id != auth_context.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized action.")

    comment.is_deleted = True
    comment.deleted_at = utc_now()
    db.add(comment)
    db.commit()
    return MessageResponse(message="Comment deleted.")

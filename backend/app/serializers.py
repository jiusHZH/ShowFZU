from __future__ import annotations

from app.models import Comment, Favorite, Like, Post, PostMedia, User
from app.schemas import CommentNode, PostDetail, PostMediaItem, PostSummary, PrivateProfile, UserSummary


def serialize_user_summary(user: User) -> UserSummary:
    return UserSummary(
        id=user.id,
        username=user.username,
        avatar_url=user.avatar_url,
        bio=user.bio,
    )


def serialize_private_profile(
    user: User,
    *,
    posts_count: int,
    favorites_count: int,
    likes_count: int,
) -> PrivateProfile:
    return PrivateProfile(
        id=user.id,
        account_id=user.account_id,
        username=user.username,
        avatar_url=user.avatar_url,
        bio=user.bio,
        posts_count=posts_count,
        favorites_count=favorites_count,
        likes_count=likes_count,
    )


def serialize_post_media(media: PostMedia) -> PostMediaItem:
    return PostMediaItem(
        id=media.id,
        type=media.type,
        url=media.url,
        thumbnail_url=media.thumbnail_url,
        mime_type=media.mime_type,
        size_bytes=media.size_bytes,
        sort_order=media.sort_order,
    )


def serialize_post_summary(post: Post) -> PostSummary:
    image_count = sum(1 for media in post.media if media.type.value == "image")
    has_video = any(media.type.value == "video" for media in post.media)
    excerpt = post.body[:180].strip() if post.body else None
    return PostSummary(
        id=post.id,
        title=post.title,
        body_excerpt=excerpt,
        category=post.category,
        cover_url=post.cover_url,
        cover_source=post.cover_source,
        published_at=post.published_at,
        updated_at=post.updated_at,
        author=serialize_user_summary(post.author),
        like_count=len(post.likes),
        favorite_count=len(post.favorites),
        has_video=has_video,
        image_count=image_count,
    )


def serialize_post_detail(
    post: Post,
    *,
    current_user_id: str | None,
    comment_count: int,
) -> PostDetail:
    summary = serialize_post_summary(post)
    liked_user_ids = {like.user_id for like in post.likes}
    favorited_user_ids = {favorite.user_id for favorite in post.favorites}
    return PostDetail(
        **summary.model_dump(),
        body=post.body,
        media=[serialize_post_media(media) for media in post.media],
        comment_count=comment_count,
        is_liked=current_user_id in liked_user_ids if current_user_id else False,
        is_favorited=current_user_id in favorited_user_ids if current_user_id else False,
        can_edit=current_user_id == post.author_id if current_user_id else False,
    )


def serialize_comment(comment: Comment) -> CommentNode:
    body = "This comment has been deleted." if comment.is_deleted else comment.body
    replies = sorted(comment.replies, key=lambda item: item.created_at)
    return CommentNode(
        id=comment.id,
        body=body,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        author=serialize_user_summary(comment.author),
        replies=[serialize_comment(reply) for reply in replies],
    )


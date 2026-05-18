from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Comment, Favorite, Like, Post


def get_private_profile_counts(db: Session, user_id: str) -> tuple[int, int, int]:
    posts_count = db.scalar(select(func.count(Post.id)).where(Post.author_id == user_id)) or 0
    favorites_count = db.scalar(select(func.count(Favorite.id)).where(Favorite.user_id == user_id)) or 0
    likes_count = db.scalar(select(func.count(Like.id)).where(Like.user_id == user_id)) or 0
    return int(posts_count), int(favorites_count), int(likes_count)


def get_total_likes_received(db: Session, user_id: str) -> int:
    total = db.scalar(
        select(func.count(Like.id)).join(Post, Like.post_id == Post.id).where(Post.author_id == user_id)
    )
    return int(total or 0)


def get_post_comment_count(db: Session, post_id: str) -> int:
    total = db.scalar(select(func.count(Comment.id)).where(Comment.post_id == post_id))
    return int(total or 0)

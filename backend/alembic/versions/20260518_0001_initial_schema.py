"""Initial ShowFZU schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260518_0001"
down_revision = None
branch_labels = None
depends_on = None


post_category = sa.Enum(
    "Campus Landmark",
    "Study Space",
    "Student Life",
    "Food and Cafe",
    "Sports and Leisure",
    "Digital Memory",
    name="post_category",
    native_enum=False,
)

media_type = sa.Enum("image", "video", name="media_type", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=24), primary_key=True),
        sa.Column("account_id", sa.String(length=12), nullable=False),
        sa.Column("username", sa.String(length=30), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("security_question", sa.String(length=255), nullable=False),
        sa.Column("security_answer_hash", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("avatar_storage_path", sa.String(length=500), nullable=True),
        sa.Column("bio", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(account_id) between 8 and 12", name="ck_users_account_id_length"),
        sa.CheckConstraint("length(username) between 2 and 30", name="ck_users_username_length"),
        sa.CheckConstraint("bio is null or length(bio) <= 160", name="ck_users_bio_length"),
        sa.UniqueConstraint("account_id", name="uq_users_account_id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_account_id", "users", ["account_id"])
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=24), nullable=False),
        sa.Column("session_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_token_hash", name="uq_sessions_session_token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_session_token_hash", "sessions", ["session_token_hash"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])

    op.create_table(
        "posts",
        sa.Column("id", sa.String(length=24), primary_key=True),
        sa.Column("author_id", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("category", post_category, nullable=False),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("cover_source", sa.String(length=20), nullable=False, server_default="default"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("length(title) > 0", name="ck_posts_title_required"),
    )
    op.create_index("ix_posts_author_id", "posts", ["author_id"])
    op.create_index("ix_posts_category", "posts", ["category"])
    op.create_index("ix_posts_published_at", "posts", ["published_at"])

    op.create_table(
        "post_media",
        sa.Column("id", sa.String(length=24), primary_key=True),
        sa.Column("post_id", sa.String(length=24), nullable=False),
        sa.Column("type", media_type, nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_storage_path", sa.String(length=500), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_post_media_post_id", "post_media", ["post_id"])
    op.create_index("ix_post_media_type", "post_media", ["type"])

    op.create_table(
        "comments",
        sa.Column("id", sa.String(length=24), primary_key=True),
        sa.Column("post_id", sa.String(length=24), nullable=False),
        sa.Column("author_id", sa.String(length=24), nullable=False),
        sa.Column("parent_id", sa.String(length=24), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_comments_post_id", "comments", ["post_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])

    op.create_table(
        "likes",
        sa.Column("id", sa.String(length=24), primary_key=True),
        sa.Column("post_id", sa.String(length=24), nullable=False),
        sa.Column("user_id", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_likes_post_user"),
    )
    op.create_index("ix_likes_post_id", "likes", ["post_id"])
    op.create_index("ix_likes_user_id", "likes", ["user_id"])

    op.create_table(
        "favorites",
        sa.Column("id", sa.String(length=24), primary_key=True),
        sa.Column("post_id", sa.String(length=24), nullable=False),
        sa.Column("user_id", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_favorites_post_user"),
    )
    op.create_index("ix_favorites_post_id", "favorites", ["post_id"])
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])

    for table_name in ("users", "sessions", "posts", "post_media", "comments", "likes", "favorites"):
        op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_index("ix_favorites_post_id", table_name="favorites")
    op.drop_table("favorites")

    op.drop_index("ix_likes_user_id", table_name="likes")
    op.drop_index("ix_likes_post_id", table_name="likes")
    op.drop_table("likes")

    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_index("ix_comments_author_id", table_name="comments")
    op.drop_index("ix_comments_post_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_post_media_type", table_name="post_media")
    op.drop_index("ix_post_media_post_id", table_name="post_media")
    op.drop_table("post_media")

    op.drop_index("ix_posts_published_at", table_name="posts")
    op.drop_index("ix_posts_category", table_name="posts")
    op.drop_index("ix_posts_author_id", table_name="posts")
    op.drop_table("posts")

    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_session_token_hash", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_account_id", table_name="users")
    op.drop_table("users")

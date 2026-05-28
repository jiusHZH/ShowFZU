from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.config import Settings
from app.database import Base, build_engine, normalize_database_url
from app.enums import PostCategory
from app.models import Post, User
from app.security import hash_password, hash_security_answer
from app.services.storage import SupabaseStorageService
from app.validation import MAX_VIDEO_SIZE_BYTES


def register_user(client, *, account_id: str, username: str, password: str = "Password123") -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "account_id": account_id,
            "username": username,
            "password": password,
            "confirm_password": password,
            "security_question": "Favorite place?",
            "security_answer": "Library",
        },
    )
    assert response.status_code == 201, response.text


def login_user(client, *, method: str, identifier: str, password: str = "Password123"):
    response = client.post(
        "/api/auth/login",
        json={
            "login_method": method,
            "identifier": identifier,
            "password": password,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_production_rejects_sqlite_database_url() -> None:
    with pytest.raises(ValidationError, match="Supabase Postgres"):
        Settings(
            env="production",
            database_url="sqlite:///prod.db",
            session_secret="strong-test-secret",
            supabase_url="https://example.supabase.co",
            supabase_service_key="test-service-key",
        )


def test_production_storage_does_not_resolve_local_demo_paths() -> None:
    settings = Settings(
        env="production",
        database_url="postgresql+psycopg://user:password@example.test:5432/postgres",
        session_secret="strong-test-secret",
        supabase_url="https://example.supabase.co",
        supabase_service_key="test-service-key",
    )
    service = object.__new__(SupabaseStorageService)
    service.settings = settings

    assert service._resolve_local_demo_path("local-demo/demo-posts/example.jpg") is None


def test_normalizes_supabase_postgres_url_to_psycopg_driver() -> None:
    assert (
        normalize_database_url("postgresql://user:password@example.test:5432/postgres")
        == "postgresql+psycopg://user:password@example.test:5432/postgres"
    )


def test_post_category_is_stored_as_public_value(tmp_path) -> None:
    database_path = tmp_path / "enum-storage.db"
    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            User.__table__.insert(),
            {
                "id": "u_enum_probe",
                "account_id": "34567890",
                "username": "Enum Probe",
                "password_hash": hash_password("Password123"),
                "security_question": "Question?",
                "security_answer_hash": hash_security_answer("Answer"),
            },
        )
        connection.execute(
            Post.__table__.insert(),
            {
                "id": "p_enum_probe",
                "author_id": "u_enum_probe",
                "title": "Enum storage probe",
                "body": "Probe body",
                "category": PostCategory.DIGITAL_MEMORY,
            },
        )
        stored_category = connection.execute(
            text("select category from posts where id = :post_id"),
            {"post_id": "p_enum_probe"},
        ).scalar_one()

    assert stored_category == "Digital Memory"


def test_explicit_login_method_allows_numeric_username(client) -> None:
    register_user(client, account_id="87654321", username="12345678")

    username_login = login_user(client, method="username", identifier="12345678")
    assert username_login["user"]["username"] == "12345678"
    assert username_login["user"]["account_id"] == "87654321"

    client.post("/api/auth/logout")

    account_login = login_user(client, method="account_id", identifier="87654321")
    assert account_login["user"]["account_id"] == "87654321"


def test_authenticated_content_flow(client, sample_image_bytes: bytes) -> None:
    register_user(client, account_id="12345678", username="Campus Storyteller")
    login_user(client, method="username", identifier="Campus Storyteller")

    create_response = client.post(
        "/api/posts",
        data={
            "title": "Fuyou Pavilion in the afternoon",
            "category": "Study Space",
            "body": "The lake breeze made the whole place feel slower and calmer today.",
        },
        files={
            "images": ("pavilion.png", sample_image_bytes, "image/png"),
        },
    )
    assert create_response.status_code == 201, create_response.text
    post = create_response.json()
    assert post["title"] == "Fuyou Pavilion in the afternoon"
    assert post["image_count"] == 1
    assert post["can_edit"] is True

    post_id = post["id"]

    feed_response = client.get("/api/posts")
    assert feed_response.status_code == 200, feed_response.text
    assert feed_response.json()["total"] == 1

    like_response = client.post(f"/api/posts/{post_id}/like")
    assert like_response.status_code == 200, like_response.text
    assert like_response.json() == {"active": True, "count": 1}

    favorite_response = client.post(f"/api/posts/{post_id}/favorite")
    assert favorite_response.status_code == 200, favorite_response.text
    assert favorite_response.json() == {"active": True, "count": 1}

    comment_response = client.post(
        f"/api/posts/{post_id}/comments",
        json={"body": "This feels like the best reading corner on campus."},
    )
    assert comment_response.status_code == 201, comment_response.text
    comments = comment_response.json()["items"]
    assert len(comments) == 1
    comment_id = comments[0]["id"]

    reply_response = client.post(
        f"/api/comments/{comment_id}/replies",
        json={"body": "The second floor view is even better near sunset."},
    )
    assert reply_response.status_code == 201, reply_response.text
    replied_comments = reply_response.json()["items"]
    assert len(replied_comments[0]["replies"]) == 1

    delete_comment_response = client.delete(f"/api/comments/{comment_id}")
    assert delete_comment_response.status_code == 200, delete_comment_response.text

    comments_after_delete = client.get(f"/api/posts/{post_id}/comments")
    assert comments_after_delete.status_code == 200, comments_after_delete.text
    comment_tree = comments_after_delete.json()["items"][0]
    assert comment_tree["body"] == "This comment has been deleted."
    assert len(comment_tree["replies"]) == 1

    me_response = client.get("/api/me")
    assert me_response.status_code == 200, me_response.text
    me_payload = me_response.json()
    assert me_payload["posts_count"] == 1
    assert me_payload["favorites_count"] == 1
    assert me_payload["likes_count"] == 1

    my_posts = client.get("/api/me/posts")
    assert my_posts.status_code == 200, my_posts.text
    assert my_posts.json()["total"] == 1

    my_favorites = client.get("/api/me/favorites")
    assert my_favorites.status_code == 200, my_favorites.text
    assert my_favorites.json()["total"] == 1

    my_likes = client.get("/api/me/likes")
    assert my_likes.status_code == 200, my_likes.text
    assert my_likes.json()["total"] == 1

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200, logout_response.text

    blocked_like = client.post(f"/api/posts/{post_id}/like")
    assert blocked_like.status_code == 401


def test_rejects_video_over_50_mb_before_upload(client) -> None:
    assert MAX_VIDEO_SIZE_BYTES == 50 * 1024 * 1024
    register_user(client, account_id="23456789", username="Video Tester")
    login_user(client, method="username", identifier="Video Tester")

    response = client.post(
        "/api/posts",
        data={
            "title": "Oversized video",
            "category": "Digital Memory",
            "body": "",
        },
        files={
            "video": ("large.mp4", b"0" * (MAX_VIDEO_SIZE_BYTES + 1), "video/mp4"),
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "Video file is too large."

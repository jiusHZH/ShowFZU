from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
FRONTEND_PUBLIC_DIR = ROOT / "frontend" / "public"
sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: F401
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.database import build_engine, build_session_factory
from app.enums import MediaType, PostCategory
from app.models import Comment, Favorite, Like, Post, PostMedia, User
from app.services.storage import SupabaseStorageService
from app.validation import MAX_TOTAL_POST_MEDIA_BYTES, MAX_VIDEO_SIZE_BYTES

BATCH_ID = "showfzu-prod-seed-v1"
STORAGE_PREFIX = f"seed-batches/{BATCH_ID}"
USER_MARKER_PREFIX = f"{STORAGE_PREFIX}/users"
CACHE_DIR = BACKEND_ROOT / ".production-seed-cache"
DEFAULT_SOURCE_DB = BACKEND_ROOT / "showfzu.dev.db"
LOCAL_DEMO_PREFIX = "local-demo/"
VIDEO_TARGET_BYTES = 48 * 1024 * 1024
TARGET_TOTAL_BYTES = 100 * 1024 * 1024


@dataclass(slots=True)
class MediaFile:
    source_path: Path
    storage_path: str
    public_url: str
    size_bytes: int
    mime_type: str


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def choose_env_file(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    for candidate in (
        BACKEND_ROOT / ".env.production.local",
        BACKEND_ROOT / ".env.render.local",
        BACKEND_ROOT / ".env",
    ):
        if candidate.exists():
            return candidate
    return BACKEND_ROOT / ".env.render.local"


def load_target_settings(env_file: Path) -> Settings:
    load_env_file(env_file)
    settings = Settings(_env_file=env_file)
    if not settings.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Production seed requires SHOWFZU_DATABASE_URL to be a Supabase Postgres URL.")
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("Production seed requires SHOWFZU_SUPABASE_URL and SHOWFZU_SUPABASE_SERVICE_KEY.")
    return settings


def connect_source(source_db: Path) -> sqlite3.Connection:
    if not source_db.exists():
        raise RuntimeError(f"Source SQLite database not found: {source_db}")
    conn = sqlite3.connect(source_db)
    conn.row_factory = sqlite3.Row
    return conn


def dict_rows(conn: sqlite3.Connection, query: str, params: tuple[object, ...] = ()) -> list[dict[str, object]]:
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_category(value: object) -> PostCategory:
    text = str(value)
    if text in PostCategory.__members__:
        return PostCategory[text]
    return PostCategory(text)


def parse_media_type(value: object) -> MediaType:
    text = str(value)
    if text in MediaType.__members__:
        return MediaType[text]
    return MediaType(text)


def local_demo_file(storage_path: object) -> Path | None:
    if not storage_path:
        return None
    path = str(storage_path)
    if not path.startswith(LOCAL_DEMO_PREFIX):
        return None
    return FRONTEND_PUBLIC_DIR / path.removeprefix(LOCAL_DEMO_PREFIX)


def source_seed_post_ids(conn: sqlite3.Connection) -> list[str]:
    rows = dict_rows(
        conn,
        """
        select distinct p.id
        from posts p
        join post_media m on m.post_id = p.id
        where m.storage_path like 'local-demo/%'
           or m.thumbnail_storage_path like 'local-demo/%'
        order by p.published_at asc, p.id asc
        """,
    )
    return [str(row["id"]) for row in rows]


def placeholders(values: list[str]) -> str:
    return ",".join("?" for _ in values)


def load_source_batch(conn: sqlite3.Connection) -> dict[str, list[dict[str, object]]]:
    post_ids = source_seed_post_ids(conn)
    if not post_ids:
        raise RuntimeError("No local-demo posts found in the source SQLite database.")
    post_placeholders = placeholders(post_ids)

    posts = dict_rows(conn, f"select * from posts where id in ({post_placeholders})", tuple(post_ids))
    media = dict_rows(
        conn,
        f"select * from post_media where post_id in ({post_placeholders}) order by post_id, sort_order",
        tuple(post_ids),
    )
    author_rows = dict_rows(
        conn,
        f"select distinct author_id from posts where id in ({post_placeholders}) order by author_id",
        tuple(post_ids),
    )
    source_user_ids = [str(row["author_id"]) for row in author_rows]
    user_placeholders = placeholders(source_user_ids)

    comments = dict_rows(
        conn,
        f"""
        select *
        from comments
        where post_id in ({post_placeholders})
          and author_id in ({user_placeholders})
        order by created_at, id
        """,
        tuple([*post_ids, *source_user_ids]),
    )
    likes = dict_rows(
        conn,
        f"""
        select *
        from likes
        where post_id in ({post_placeholders})
          and user_id in ({user_placeholders})
        """,
        tuple([*post_ids, *source_user_ids]),
    )
    favorites = dict_rows(
        conn,
        f"""
        select *
        from favorites
        where post_id in ({post_placeholders})
          and user_id in ({user_placeholders})
        """,
        tuple([*post_ids, *source_user_ids]),
    )
    users = dict_rows(conn, f"select * from users where id in ({user_placeholders})", tuple(source_user_ids))

    return {
        "users": users,
        "posts": posts,
        "post_media": media,
        "comments": comments,
        "likes": likes,
        "favorites": favorites,
    }


def storage_path_for_local(local_storage_path: str) -> str:
    return f"{STORAGE_PREFIX}/{local_storage_path.removeprefix(LOCAL_DEMO_PREFIX)}"


def public_url(settings: Settings, storage_path: str) -> str:
    return (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/"
        f"{settings.storage_posts_bucket}/{storage_path}"
    )


def probe_video_duration_seconds(source: Path, ffprobe_path: str) -> float:
    result = subprocess.run(
        [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float((result.stdout or "0").strip() or "0")


def compress_video_to_limit(source: Path, *, settings: Settings) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output = CACHE_DIR / f"{source.stem}-{BATCH_ID}-under-50mb.mp4"
    duration_seconds = probe_video_duration_seconds(source, settings.ffprobe_path)
    audio_bitrate = 96_000
    total_bitrate = max(int((VIDEO_TARGET_BYTES * 8 * 0.94) / max(duration_seconds, 1)), 256_000)
    video_bitrate = max(total_bitrate - audio_bitrate, 160_000)
    subprocess.run(
        [
            settings.ffmpeg_path,
            "-y",
            "-i",
            str(source),
            "-vf",
            "scale=1280:-2:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-b:v",
            str(video_bitrate),
            "-maxrate",
            str(int(video_bitrate * 1.15)),
            "-bufsize",
            str(int(video_bitrate * 2)),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    if output.stat().st_size > MAX_VIDEO_SIZE_BYTES:
        raise RuntimeError(f"Compressed video still exceeds 50MB: {source.name}")
    return output


def prepare_media_file(row: dict[str, object], key: str, *, settings: Settings) -> MediaFile | None:
    local_path = local_demo_file(row.get(key))
    if local_path is None:
        return None
    if not local_path.exists():
        raise RuntimeError(f"Missing local demo media file: {local_path}")

    source_path = local_path
    media_type = parse_media_type(row["type"])
    if media_type == MediaType.VIDEO and local_path.stat().st_size > MAX_VIDEO_SIZE_BYTES:
        source_path = compress_video_to_limit(local_path, settings=settings)

    size_bytes = source_path.stat().st_size
    if media_type == MediaType.VIDEO and size_bytes > MAX_VIDEO_SIZE_BYTES:
        raise RuntimeError(f"Video exceeds 50MB after preparation: {local_path.name}")

    storage_path = storage_path_for_local(str(row[key]))
    if source_path != local_path:
        storage_path = str(Path(storage_path).with_suffix(".mp4")).replace("\\", "/")
    mime_type = mimetypes.guess_type(source_path.name)[0] or str(row.get("mime_type") or "application/octet-stream")
    return MediaFile(
        source_path=source_path,
        storage_path=storage_path,
        public_url=public_url(settings, storage_path),
        size_bytes=size_bytes,
        mime_type=mime_type,
    )


def inspect_source(batch: dict[str, list[dict[str, object]]], *, settings: Settings | None = None) -> dict[str, object]:
    total_bytes = 0
    oversized_videos: list[dict[str, object]] = []
    missing_files: list[str] = []
    for row in batch["post_media"]:
        for key in ("storage_path", "thumbnail_storage_path"):
            local_path = local_demo_file(row.get(key))
            if local_path is None:
                continue
            if not local_path.exists():
                missing_files.append(str(local_path.relative_to(ROOT)))
                continue
            size = local_path.stat().st_size
            total_bytes += size
            if key == "storage_path" and parse_media_type(row["type"]) == MediaType.VIDEO and size > MAX_VIDEO_SIZE_BYTES:
                oversized_videos.append(
                    {
                        "path": str(local_path.relative_to(ROOT)),
                        "size_mb": round(size / 1024 / 1024, 2),
                        "target_mb": round(VIDEO_TARGET_BYTES / 1024 / 1024, 2),
                    }
                )
    return {
        "batch_id": BATCH_ID,
        "users": len(batch["users"]),
        "posts": len(batch["posts"]),
        "post_media": len(batch["post_media"]),
        "comments": len(batch["comments"]),
        "likes": len(batch["likes"]),
        "favorites": len(batch["favorites"]),
        "total_media_mb": round(total_bytes / 1024 / 1024, 2),
        "target_total_media_mb": round(TARGET_TOTAL_BYTES / 1024 / 1024, 2),
        "missing_files": missing_files,
        "oversized_videos": oversized_videos,
        "needs_compression": bool(oversized_videos),
        "within_suggested_total": total_bytes <= TARGET_TOTAL_BYTES,
    }


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def list_storage_paths(storage: SupabaseStorageService, bucket: str, prefix: str) -> list[str]:
    client = storage._require_client()
    paths: list[str] = []

    def walk(path: str) -> None:
        try:
            entries = client.storage.from_(bucket).list(path)
        except Exception:
            return
        for entry in entries:
            name = entry.get("name")
            if not name:
                continue
            child = f"{path.rstrip('/')}/{name}".strip("/")
            metadata = entry.get("metadata")
            entry_id = entry.get("id")
            if metadata is None and entry_id is None:
                walk(child)
            else:
                paths.append(child)

    walk(prefix)
    return paths


def remove_storage_paths(storage: SupabaseStorageService, bucket: str, paths: list[str]) -> None:
    unique_paths = sorted(set(path for path in paths if path))
    if not unique_paths:
        return
    client = storage._require_client()
    for batch in chunked(unique_paths, 100):
        client.storage.from_(bucket).remove(batch)


def cleanup_target(settings: Settings) -> dict[str, int]:
    storage = SupabaseStorageService(settings)
    session_factory = build_session_factory(settings.database_url)
    removed_paths: list[str] = []
    counts = {"posts": 0, "users": 0, "storage_objects": 0}

    with session_factory() as db:
        marked_users = list(db.scalars(select(User).where(User.avatar_storage_path.like(f"{USER_MARKER_PREFIX}/%"))))
        marked_user_ids = [user.id for user in marked_users]
        media_posts = list(
            db.scalars(
                select(Post)
                .join(PostMedia, PostMedia.post_id == Post.id)
                .where(PostMedia.storage_path.like(f"{STORAGE_PREFIX}/%"))
                .options(selectinload(Post.media))
            )
            .unique()
            .all()
        )
        user_posts = (
            list(
                db.scalars(select(Post).where(Post.author_id.in_(marked_user_ids)).options(selectinload(Post.media)))
                .unique()
                .all()
            )
            if marked_user_ids
            else []
        )
        posts_by_id = {post.id: post for post in [*media_posts, *user_posts]}
        for post in posts_by_id.values():
            for media in post.media:
                if media.storage_path:
                    removed_paths.append(media.storage_path)
                if media.thumbnail_storage_path:
                    removed_paths.append(media.thumbnail_storage_path)
            db.delete(post)
        counts["posts"] = len(posts_by_id)

        for user in marked_users:
            db.delete(user)
        counts["users"] = len(marked_users)
        db.commit()

    removed_paths.extend(list_storage_paths(storage, settings.storage_posts_bucket, STORAGE_PREFIX))
    remove_storage_paths(storage, settings.storage_posts_bucket, removed_paths)
    counts["storage_objects"] = len(set(removed_paths))
    return counts


def assert_no_conflicts(db: Session, batch: dict[str, list[dict[str, object]]]) -> None:
    user_ids = [str(user["id"]) for user in batch["users"]]
    account_ids = [str(user["account_id"]) for user in batch["users"]]
    usernames = [str(user["username"]) for user in batch["users"]]
    post_ids = [str(post["id"]) for post in batch["posts"]]
    existing_users = list(
        db.scalars(
            select(User).where(
                (User.id.in_(user_ids))
                | (User.account_id.in_(account_ids))
                | (User.username.in_(usernames))
            )
        )
    )
    unsafe_users = [user for user in existing_users if not (user.avatar_storage_path or "").startswith(USER_MARKER_PREFIX)]
    if unsafe_users:
        raise RuntimeError("Target database has non-seed users conflicting with source seed users.")
    existing_posts = list(db.scalars(select(Post).where(Post.id.in_(post_ids))))
    if existing_posts:
        raise RuntimeError("Target database has posts with source seed IDs. Run cleanup or inspect conflicts first.")


def seed_target(source_batch: dict[str, list[dict[str, object]]], settings: Settings, *, dry_run: bool) -> dict[str, object]:
    plan = inspect_source(source_batch, settings=settings)
    if plan["missing_files"]:
        raise RuntimeError("Source demo media files are missing.")
    if not plan["within_suggested_total"]:
        raise RuntimeError("Source demo media exceeds the suggested 100MB total.")
    if dry_run:
        return {"dry_run": True, **plan}

    cleanup_counts = cleanup_target(settings)
    storage = SupabaseStorageService(settings)
    session_factory = build_session_factory(settings.database_url)
    uploaded_paths: list[str] = []
    media_files: dict[tuple[str, str], MediaFile] = {}

    try:
        for row in source_batch["post_media"]:
            for key in ("storage_path", "thumbnail_storage_path"):
                prepared = prepare_media_file(row, key, settings=settings)
                if prepared is None:
                    continue
                media_files[(str(row["id"]), key)] = prepared
                storage.upload_bytes(
                    settings.storage_posts_bucket,
                    prepared.storage_path,
                    prepared.source_path.read_bytes(),
                    content_type=prepared.mime_type,
                )
                uploaded_paths.append(prepared.storage_path)

        with session_factory() as db:
            assert_no_conflicts(db, source_batch)
            for row in source_batch["users"]:
                db.add(
                    User(
                        id=str(row["id"]),
                        account_id=str(row["account_id"]),
                        username=str(row["username"]),
                        password_hash=str(row["password_hash"]),
                        security_question=str(row["security_question"]),
                        security_answer_hash=str(row["security_answer_hash"]),
                        avatar_url=row.get("avatar_url"),
                        avatar_storage_path=f"{USER_MARKER_PREFIX}/{row['id']}",
                        bio=row.get("bio"),
                        created_at=parse_datetime(row["created_at"]),
                        updated_at=parse_datetime(row["updated_at"]),
                    )
                )
            db.flush()

            media_by_post: dict[str, list[PostMedia]] = {}
            for row in source_batch["post_media"]:
                media_file = media_files.get((str(row["id"]), "storage_path"))
                if media_file is None:
                    raise RuntimeError(f"Missing prepared media for {row['id']}")
                thumbnail = media_files.get((str(row["id"]), "thumbnail_storage_path"))
                media = PostMedia(
                    id=str(row["id"]),
                    post_id=str(row["post_id"]),
                    type=parse_media_type(row["type"]),
                    url=media_file.public_url,
                    storage_path=media_file.storage_path,
                    thumbnail_url=thumbnail.public_url if thumbnail else None,
                    thumbnail_storage_path=thumbnail.storage_path if thumbnail else None,
                    mime_type=media_file.mime_type,
                    size_bytes=media_file.size_bytes,
                    sort_order=int(row["sort_order"]),
                    created_at=parse_datetime(row["created_at"]),
                )
                media_by_post.setdefault(media.post_id, []).append(media)

            for row in source_batch["posts"]:
                post_media = sorted(media_by_post.get(str(row["id"]), []), key=lambda item: item.sort_order)
                first_image = next((item for item in post_media if item.type == MediaType.IMAGE), None)
                first_video = next((item for item in post_media if item.type == MediaType.VIDEO), None)
                if first_image is not None:
                    cover_url = first_image.url
                    cover_source = "image"
                elif first_video is not None:
                    cover_url = first_video.thumbnail_url
                    cover_source = "video"
                else:
                    cover_url = settings.default_cover_url
                    cover_source = "default"
                db.add(
                    Post(
                        id=str(row["id"]),
                        author_id=str(row["author_id"]),
                        title=str(row["title"]),
                        body=row.get("body"),
                        category=parse_category(row["category"]),
                        cover_url=cover_url,
                        cover_source=cover_source,
                        published_at=parse_datetime(row["published_at"]),
                        updated_at=parse_datetime(row["updated_at"]),
                    )
                )
            db.flush()

            for media_items in media_by_post.values():
                for media in media_items:
                    db.add(media)

            for row in source_batch["comments"]:
                db.add(
                    Comment(
                        id=str(row["id"]),
                        post_id=str(row["post_id"]),
                        author_id=str(row["author_id"]),
                        parent_id=row.get("parent_id"),
                        body=str(row["body"]),
                        is_deleted=bool(row["is_deleted"]),
                        created_at=parse_datetime(row["created_at"]),
                        deleted_at=parse_datetime(row["deleted_at"]) if row.get("deleted_at") else None,
                    )
                )
            for row in source_batch["likes"]:
                db.add(
                    Like(
                        id=str(row["id"]),
                        post_id=str(row["post_id"]),
                        user_id=str(row["user_id"]),
                        created_at=parse_datetime(row["created_at"]),
                    )
                )
            for row in source_batch["favorites"]:
                db.add(
                    Favorite(
                        id=str(row["id"]),
                        post_id=str(row["post_id"]),
                        user_id=str(row["user_id"]),
                        created_at=parse_datetime(row["created_at"]),
                    )
                )
            db.commit()
    except (IntegrityError, Exception):
        remove_storage_paths(storage, settings.storage_posts_bucket, uploaded_paths)
        raise

    return {
        "dry_run": False,
        "cleanup_before_seed": cleanup_counts,
        "uploaded_storage_objects": len(uploaded_paths),
        **inspect_source(source_batch, settings=settings),
    }


def verify_target(settings: Settings) -> dict[str, int]:
    session_factory = build_session_factory(settings.database_url)
    with session_factory() as db:
        users = list(db.scalars(select(User).where(User.avatar_storage_path.like(f"{USER_MARKER_PREFIX}/%"))))
        user_ids = [user.id for user in users]
        posts = list(db.scalars(select(Post).where(Post.author_id.in_(user_ids)))) if user_ids else []
        post_ids = [post.id for post in posts]
        media_count = (
            int(db.scalar(select(PostMedia).where(PostMedia.post_id.in_(post_ids)).count()) or 0)
            if False
            else 0
        )
        if post_ids:
            media_count = len(list(db.scalars(select(PostMedia).where(PostMedia.post_id.in_(post_ids)))))
            comments_count = len(list(db.scalars(select(Comment).where(Comment.post_id.in_(post_ids)))))
            likes_count = len(list(db.scalars(select(Like).where(Like.post_id.in_(post_ids)))))
            favorites_count = len(list(db.scalars(select(Favorite).where(Favorite.post_id.in_(post_ids)))))
        else:
            comments_count = likes_count = favorites_count = 0
        return {
            "users": len(users),
            "posts": len(posts),
            "post_media": media_count,
            "comments": comments_count,
            "likes": likes_count,
            "favorites": favorites_count,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed production Supabase from the local ShowFZU SQLite demo data.")
    parser.add_argument("command", choices=["plan", "seed", "cleanup", "verify"])
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--yes", action="store_true", help="Required for seed and cleanup.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare a seed summary without writing.")
    args = parser.parse_args()

    with connect_source(args.source_db) as source_conn:
        batch = load_source_batch(source_conn)

    if args.command == "plan":
        print(json.dumps(inspect_source(batch), ensure_ascii=False, indent=2))
        return

    env_file = choose_env_file(args.env_file)
    settings = load_target_settings(env_file)

    if args.command == "seed":
        if not args.yes and not args.dry_run:
            raise RuntimeError("Use --yes to seed production, or --dry-run to preview.")
        print(json.dumps(seed_target(batch, settings, dry_run=args.dry_run), ensure_ascii=False, indent=2))
        return

    if args.command == "cleanup":
        if not args.yes:
            raise RuntimeError("Use --yes to clean production seed data.")
        print(json.dumps(cleanup_target(settings), ensure_ascii=False, indent=2))
        return

    if args.command == "verify":
        print(json.dumps(verify_target(settings), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import mimetypes
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
RESOURCE_DIR = ROOT / "resource"
FRONTEND_PUBLIC_DIR = ROOT / "frontend" / "public"
DEMO_MEDIA_DIR = FRONTEND_PUBLIC_DIR / "demo-posts"
IMAGE_OUTPUT_DIR = DEMO_MEDIA_DIR / "images"
VIDEO_OUTPUT_DIR = DEMO_MEDIA_DIR / "videos"
THUMBNAIL_OUTPUT_DIR = DEMO_MEDIA_DIR / "thumbnails"

sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: F401
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.database import Base, build_engine, build_session_factory, utc_now
from app.enums import MediaType, PostCategory
from app.ids import create_public_id
from app.models import Favorite, Like, Post, PostMedia, User
from app.security import hash_password, hash_security_answer
from app.validation import MAX_IMAGE_SIZE_BYTES, MAX_TOTAL_POST_MEDIA_BYTES, MAX_VIDEO_SIZE_BYTES

POST_EXAMPLES_DOC = RESOURCE_DIR / "发帖（学习空间，美食，校园记忆）.docx"
LANDMARKS_DOC = RESOURCE_DIR / "地标，日常，运动，课余（改3）.docx"

POST_EXAMPLES_DOC_GLOB = "*校园记忆*.docx"
LANDMARKS_DOC_GLOB = "*课余*改3*.docx"

VIDEO_SOURCE_BY_NAME = {
    "Study_Center.mp4": RESOURCE_DIR / "Study_ Center.mp4",
    "Food_Diary.mp4": RESOURCE_DIR / "Food_ Diary.mp4",
}

LOCAL_DEMO_PREFIX = "local-demo/"
VIDEO_TARGET_BYTES = 23 * 1024 * 1024
PASSWORD = "CampusDemo123"
SECURITY_QUESTION = "Favorite place on campus?"
SECURITY_ANSWER = "Library"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


@dataclass(slots=True)
class ParagraphEntry:
    text: str
    images: list[str]


@dataclass(slots=True)
class AccountSeed:
    account_id: str
    username: str
    bio: str


@dataclass(slots=True)
class PostSeed:
    source_doc: Path
    title: str
    body: str
    category: PostCategory
    image_members: list[str] = field(default_factory=list)
    video_source: Path | None = None
    seed_key: str = ""


ACCOUNT_BY_CATEGORY: dict[PostCategory, AccountSeed] = {
    PostCategory.STUDY_SPACE: AccountSeed(
        account_id="10010001",
        username="Maya Lin",
        bio="Always collecting quiet corners, reading light, and focused campus afternoons.",
    ),
    PostCategory.FOOD_AND_CAFE: AccountSeed(
        account_id="10010002",
        username="Ethan Qiu",
        bio="Campus food scout with a soft spot for canteens, coffee counters, and late-night snacks.",
    ),
    PostCategory.DIGITAL_MEMORY: AccountSeed(
        account_id="10010003",
        username="Luna He",
        bio="Saving seasonal light, graduation feelings, and the small images that stay after a day ends.",
    ),
    PostCategory.CAMPUS_LANDMARK: AccountSeed(
        account_id="10010004",
        username="Daniel Cai",
        bio="Walking campus landmarks with a camera and stopping for every skyline, pond, and pavilion.",
    ),
    PostCategory.STUDENT_LIFE: AccountSeed(
        account_id="10010005",
        username="Iris Zheng",
        bio="Posting the social tempo of campus life, from routines and events to the energy between classes.",
    ),
    PostCategory.SPORTS_AND_LEISURE: AccountSeed(
        account_id="10010006",
        username="Leo Tang",
        bio="Looking for the spaces where campus movement, fresh air, and time off all feel easy.",
    ),
}

CATEGORY_ALIASES = {
    "campus landmark": PostCategory.CAMPUS_LANDMARK,
    "campus landmarks": PostCategory.CAMPUS_LANDMARK,
    "study space": PostCategory.STUDY_SPACE,
    "library": PostCategory.STUDY_SPACE,
    "student life": PostCategory.STUDENT_LIFE,
    "daily life": PostCategory.STUDENT_LIFE,
    "food and cafe": PostCategory.FOOD_AND_CAFE,
    "food & cafe": PostCategory.FOOD_AND_CAFE,
    "sports and leisure": PostCategory.SPORTS_AND_LEISURE,
    "sports & leisure": PostCategory.SPORTS_AND_LEISURE,
    "digital memory": PostCategory.DIGITAL_MEMORY,
}


def normalize_video_name(value: str) -> str:
    return re.sub(r"[\s_]+", "", value).lower()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def public_url(settings: Settings, relative_path: Path) -> str:
    return f"{settings.public_base_url.rstrip('/')}/{relative_path.as_posix()}"


def local_storage_path(relative_path: Path) -> str:
    return f"{LOCAL_DEMO_PREFIX}{relative_path.as_posix()}"


def find_single_resource(pattern: str) -> Path:
    matches = sorted(RESOURCE_DIR.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one resource matching {pattern!r}, found {len(matches)}.")
    return matches[0]


def normalize_category(value: str) -> PostCategory:
    normalized = " ".join(value.split()).strip().lower()
    category = CATEGORY_ALIASES.get(normalized)
    if category is None:
        raise RuntimeError(f"Unsupported category value in demo content: {value!r}")
    return category


def read_docx_paragraph_entries(docx: Path) -> list[ParagraphEntry]:
    with ZipFile(docx) as archive:
        document_root = ET.fromstring(archive.read("word/document.xml"))
        rels_root = ET.fromstring(archive.read("word/_rels/document.xml.rels"))

    rels = {}
    for rel in rels_root:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            rels[rid] = target

    body = document_root.find("w:body", NS)
    entries: list[ParagraphEntry] = []
    for child in (list(body) if body is not None else []):
        if child.tag != f"{{{NS['w']}}}p":
            continue
        texts = [node.text for node in child.findall(".//w:t", NS) if node.text]
        text = "".join(texts).strip()
        images: list[str] = []
        for blip in child.findall(".//a:blip", NS):
            rid = blip.attrib.get(f"{{{NS['r']}}}embed")
            if rid and rid in rels:
                images.append(rels[rid])
        if text or images:
            entries.append(ParagraphEntry(text=text, images=images))
    return entries


def parse_post_examples_doc(docx: Path) -> list[PostSeed]:
    entries = read_docx_paragraph_entries(docx)
    posts: list[PostSeed] = []
    index = 0
    title_marker = re.compile(r"^\d+\.Post title")
    while index < len(entries):
        entry = entries[index]
        if not title_marker.match(entry.text):
            index += 1
            continue

        title = entries[index + 1].text
        index += 3  # skip title + "Post body"
        body_parts: list[str] = []
        while index < len(entries) and not entries[index].text.startswith("Post category"):
            if entries[index].text:
                body_parts.append(entries[index].text)
            index += 1

        category_text = entries[index + 1].text
        category = normalize_category(category_text)
        index += 3  # skip "Post category", category value, "Upload images/videos"

        image_members: list[str] = []
        video_source: Path | None = None
        while index < len(entries) and not title_marker.match(entries[index].text):
            current = entries[index]
            image_members.extend(current.images)
            if current.text.endswith(".mp4"):
                normalized_name = normalize_video_name(current.text)
                for lookup_name, source_path in VIDEO_SOURCE_BY_NAME.items():
                    if normalize_video_name(lookup_name) == normalized_name:
                        video_source = source_path
                        break
            index += 1

        posts.append(
            PostSeed(
                source_doc=docx,
                title=title,
                body=" ".join(body_parts).strip(),
                category=category,
                image_members=image_members,
                video_source=video_source,
            )
        )

    return posts


def parse_landmark_doc(docx: Path) -> list[PostSeed]:
    entries = read_docx_paragraph_entries(docx)
    posts: list[PostSeed] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        if not entry.text.startswith("Title:"):
            index += 1
            continue

        title = entry.text.removeprefix("Title:").strip()
        index += 1

        tag_line = entries[index].text
        if not tag_line.startswith("Tag:"):
            raise RuntimeError(f"Expected Tag line after title {title!r}")
        category_text = tag_line.removeprefix("Tag:").strip()
        if not category_text:
            index += 1
            category_text = entries[index].text.strip()
        category = normalize_category(category_text)

        while index < len(entries) and entries[index].text != "Content:":
            index += 1
        index += 1

        body_parts: list[str] = []
        image_members: list[str] = []
        while index < len(entries) and not entries[index].text.startswith("Title:"):
            current = entries[index]
            if current.text:
                body_parts.append(current.text)
            image_members.extend(current.images)
            index += 1

        posts.append(
            PostSeed(
                source_doc=docx,
                title=title,
                body=" ".join(body_parts).strip(),
                category=category,
                image_members=image_members,
            )
        )

    return posts


def extract_docx_media_bytes(docx: Path, media_member: str) -> bytes:
    with ZipFile(docx) as archive:
        return archive.read(f"word/{media_member}")


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


def ensure_demo_media_dirs() -> None:
    IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAIL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_demo_image_asset(
    settings: Settings,
    docx: Path,
    media_member: str,
    *,
    seed_key: str,
    image_index: int,
) -> tuple[str, str, int, str]:
    source_suffix = Path(media_member).suffix.lower()
    output_relative = Path("demo-posts") / "images" / f"{seed_key}-{image_index}{source_suffix}"
    output_path = FRONTEND_PUBLIC_DIR / output_relative
    data = extract_docx_media_bytes(docx, media_member)
    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise RuntimeError(f"Embedded image exceeds the 10MB limit: {media_member}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    mime_type = mimetypes.guess_type(output_path.name)[0] or "application/octet-stream"
    return (
        public_url(settings, output_relative),
        local_storage_path(output_relative),
        len(data),
        mime_type,
    )


def build_demo_video_asset(
    settings: Settings,
    source: Path,
    *,
    seed_key: str,
) -> tuple[tuple[str, str, int, str], tuple[str, str]]:
    output_relative = Path("demo-posts") / "videos" / f"{seed_key}.mp4"
    output_path = FRONTEND_PUBLIC_DIR / output_relative
    thumbnail_relative = Path("demo-posts") / "thumbnails" / f"{seed_key}.jpg"
    thumbnail_path = FRONTEND_PUBLIC_DIR / thumbnail_relative

    output_path.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

    duration_seconds = probe_video_duration_seconds(source, settings.ffprobe_path)
    audio_bitrate = 96_000
    total_bitrate = max(int((VIDEO_TARGET_BYTES * 8 * 0.94) / max(duration_seconds, 1)), 256_000)
    video_bitrate = max(total_bitrate - audio_bitrate, 160_000)
    maxrate = int(video_bitrate * 1.15)
    bufsize = int(video_bitrate * 2)

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
            str(maxrate),
            "-bufsize",
            str(bufsize),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )

    final_size = output_path.stat().st_size
    if final_size > MAX_VIDEO_SIZE_BYTES:
        raise RuntimeError(f"Compressed video still exceeds limit: {output_path.name}")

    capture_time = max(duration_seconds / 2, 0.1)
    subprocess.run(
        [
            settings.ffmpeg_path,
            "-y",
            "-ss",
            f"{capture_time:.3f}",
            "-i",
            str(output_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(thumbnail_path),
        ],
        check=True,
        capture_output=True,
    )

    return (
        (
            public_url(settings, output_relative),
            local_storage_path(output_relative),
            final_size,
            "video/mp4",
        ),
        (
            public_url(settings, thumbnail_relative),
            local_storage_path(thumbnail_relative),
        ),
    )


def delete_local_demo_asset(storage_path: str | None) -> None:
    if not storage_path or not storage_path.startswith(LOCAL_DEMO_PREFIX):
        return
    relative = storage_path.removeprefix(LOCAL_DEMO_PREFIX)
    asset_path = FRONTEND_PUBLIC_DIR / relative
    if asset_path.exists():
        asset_path.unlink()


def load_post_seeds() -> list[PostSeed]:
    post_examples_doc = find_single_resource(POST_EXAMPLES_DOC_GLOB)
    landmarks_doc = find_single_resource(LANDMARKS_DOC_GLOB)
    posts = parse_post_examples_doc(post_examples_doc) + parse_landmark_doc(landmarks_doc)
    for index, post in enumerate(posts, start=1):
        doc_key = "post-examples" if post.source_doc == post_examples_doc else "landmarks-daily"
        post.seed_key = f"{doc_key}-{index:02d}-{slugify(post.title)[:48]}"
    return posts


def ensure_demo_accounts(db: Session) -> dict[PostCategory, User]:
    seeded_users: dict[PostCategory, User] = {}
    for category, seed in ACCOUNT_BY_CATEGORY.items():
        conflicting_user = db.scalar(
            select(User).where(User.username == seed.username, User.account_id != seed.account_id)
        )
        if conflicting_user is not None:
            raise RuntimeError(f"Username {seed.username!r} is already used by another account.")

        user = db.scalar(select(User).where(User.account_id == seed.account_id))
        if user is None:
            user = User(
                id=create_public_id("u"),
                account_id=seed.account_id,
                username=seed.username,
                password_hash=hash_password(PASSWORD),
                security_question=SECURITY_QUESTION,
                security_answer_hash=hash_security_answer(SECURITY_ANSWER),
                bio=seed.bio,
            )
            db.add(user)
        else:
            user.username = seed.username
            user.bio = seed.bio
            user.password_hash = hash_password(PASSWORD)
            user.security_question = SECURITY_QUESTION
            user.security_answer_hash = hash_security_answer(SECURITY_ANSWER)
        db.flush()
        seeded_users[category] = user

    db.commit()
    return seeded_users


def clear_existing_demo_posts(db: Session, demo_users: dict[PostCategory, User]) -> None:
    demo_user_ids = [user.id for user in demo_users.values()]
    existing_posts = list(
        db.scalars(
            select(Post)
            .where(Post.author_id.in_(demo_user_ids))
            .options(selectinload(Post.media), selectinload(Post.likes), selectinload(Post.favorites))
        ).all()
    )
    for post in existing_posts:
        for media in post.media:
            delete_local_demo_asset(media.storage_path)
            delete_local_demo_asset(media.thumbnail_storage_path)
        db.delete(post)
    db.commit()


def create_demo_posts(db: Session, settings: Settings, demo_users: dict[PostCategory, User], post_seeds: list[PostSeed]) -> list[Post]:
    created_posts: list[Post] = []
    base_time = utc_now() - timedelta(days=len(post_seeds) // 2)
    for index, seed in enumerate(post_seeds):
        author = demo_users[seed.category]
        published_at = base_time + timedelta(hours=index * 4)
        post = Post(
            id=create_public_id("p"),
            author_id=author.id,
            title=seed.title,
            body=seed.body,
            category=seed.category,
            published_at=published_at,
            updated_at=published_at,
        )
        db.add(post)
        db.flush()

        total_media_bytes = 0
        media_items: list[PostMedia] = []

        for image_index, media_member in enumerate(seed.image_members, start=1):
            url, storage_path, size_bytes, mime_type = build_demo_image_asset(
                settings,
                seed.source_doc,
                media_member,
                seed_key=seed.seed_key,
                image_index=image_index,
            )
            total_media_bytes += size_bytes
            media_items.append(
                PostMedia(
                    id=create_public_id("m"),
                    post_id=post.id,
                    type=MediaType.IMAGE,
                    url=url,
                    storage_path=storage_path,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    sort_order=len(media_items),
                )
            )

        if seed.video_source is not None:
            (video_url, video_storage_path, video_size, video_mime), (
                thumbnail_url,
                thumbnail_storage_path,
            ) = build_demo_video_asset(settings, seed.video_source, seed_key=seed.seed_key)
            total_media_bytes += video_size
            media_items.append(
                PostMedia(
                    id=create_public_id("m"),
                    post_id=post.id,
                    type=MediaType.VIDEO,
                    url=video_url,
                    storage_path=video_storage_path,
                    thumbnail_url=thumbnail_url,
                    thumbnail_storage_path=thumbnail_storage_path,
                    mime_type=video_mime,
                    size_bytes=video_size,
                    sort_order=len(media_items),
                )
            )

        if total_media_bytes > MAX_TOTAL_POST_MEDIA_BYTES:
            raise RuntimeError(f"Demo post {seed.title!r} exceeds the total media limit.")

        if media_items:
            first_image = next((item for item in media_items if item.type == MediaType.IMAGE), None)
            if first_image is not None:
                post.cover_url = first_image.url
                post.cover_source = "image"
            else:
                video_item = media_items[0]
                post.cover_url = video_item.thumbnail_url
                post.cover_source = "video"
        else:
            post.cover_url = settings.default_cover_url
            post.cover_source = "default"

        post.media.extend(media_items)
        db.add(post)
        created_posts.append(post)

    db.commit()
    return created_posts


def seed_interactions(db: Session, demo_users: dict[PostCategory, User], posts: list[Post]) -> None:
    user_list = list(demo_users.values())
    for index, post in enumerate(posts):
        eligible_users = [user for user in user_list if user.id != post.author_id]
        if not eligible_users:
            continue

        like_total = 2 if len(eligible_users) >= 2 else 1
        for offset in range(like_total):
            liker = eligible_users[(index + offset) % len(eligible_users)]
            db.add(Like(id=create_public_id("l"), post_id=post.id, user_id=liker.id))

        if index % 2 == 0:
            favoriter = eligible_users[(index + 2) % len(eligible_users)]
            db.add(Favorite(id=create_public_id("f"), post_id=post.id, user_id=favoriter.id))

    db.commit()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ensure_demo_media_dirs()

    settings = Settings(_env_file=BACKEND_ROOT / ".env")
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(settings.database_url)

    post_seeds = load_post_seeds()
    with session_factory() as db:
        demo_users = ensure_demo_accounts(db)
        clear_existing_demo_posts(db, demo_users)
        created_posts = create_demo_posts(db, settings, demo_users, post_seeds)
        seed_interactions(db, demo_users, created_posts)

    summary = {
        "accounts": [
            {
                "account_id": seed.account_id,
                "username": seed.username,
                "password": PASSWORD,
            }
            for seed in ACCOUNT_BY_CATEGORY.values()
        ],
        "posts_seeded": len(post_seeds),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

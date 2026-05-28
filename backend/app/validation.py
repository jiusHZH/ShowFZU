from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.enums import PostCategory

ACCOUNT_ID_PATTERN = re.compile(r"^\d{8,12}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9 ]{2,30}$")
PASSWORD_HAS_LETTER = re.compile(r"[A-Za-z]")
PASSWORD_HAS_NUMBER = re.compile(r"\d")

ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_AVATAR_MIME_TYPES = {"image/jpeg", "image/png"}

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/gif"}

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov"}
ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/webm",
    "video/ogg",
    "video/quicktime",
}

MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024
MAX_TOTAL_POST_MEDIA_BYTES = 200 * 1024 * 1024


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_security_answer(value: str) -> str:
    return " ".join(value.strip().lower().split())


def validate_account_id(value: str) -> str:
    value = value.strip()
    if not ACCOUNT_ID_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Account ID must be 8 to 12 digits.",
        )
    return value


def validate_username(value: str) -> str:
    value = value.strip()
    if not USERNAME_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Username must be 2 to 30 characters and use only letters, numbers, or spaces.",
        )
    return value


def validate_password(value: str) -> str:
    if len(value) < 8 or not PASSWORD_HAS_LETTER.search(value) or not PASSWORD_HAS_NUMBER.search(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Password must be at least 8 characters and include letters and numbers.",
        )
    return value


def validate_bio(value: str | None) -> str | None:
    value = clean_text(value)
    if value and len(value) > 160:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Bio must be 160 characters or fewer.",
        )
    return value


def parse_category(value: str) -> PostCategory:
    try:
        return PostCategory(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid category.",
        ) from exc


def parse_json_array(value: str | None) -> list[str] | None:
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid JSON array field.",
        ) from exc
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Expected a JSON array of strings.",
        )
    return parsed


def get_upload_size(upload: UploadFile) -> int:
    original = upload.file.tell()
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(original)
    return size


def _validate_upload(
    upload: UploadFile,
    *,
    allowed_extensions: set[str],
    allowed_mime_types: set[str],
    max_size_bytes: int,
    label: str,
) -> int:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{label} filename is required.",
        )
    extension = Path(upload.filename).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid {label} file type.",
        )
    if (upload.content_type or "").lower() not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid {label} MIME type.",
        )
    size = get_upload_size(upload)
    if size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{label.capitalize()} file is too large.",
        )
    return size


def validate_avatar_upload(upload: UploadFile) -> int:
    return _validate_upload(
        upload,
        allowed_extensions=ALLOWED_AVATAR_EXTENSIONS,
        allowed_mime_types=ALLOWED_AVATAR_MIME_TYPES,
        max_size_bytes=MAX_AVATAR_SIZE_BYTES,
        label="avatar",
    )


def validate_image_upload(upload: UploadFile) -> int:
    return _validate_upload(
        upload,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        allowed_mime_types=ALLOWED_IMAGE_MIME_TYPES,
        max_size_bytes=MAX_IMAGE_SIZE_BYTES,
        label="image",
    )


def validate_video_upload(upload: UploadFile) -> int:
    return _validate_upload(
        upload,
        allowed_extensions=ALLOWED_VIDEO_EXTENSIONS,
        allowed_mime_types=ALLOWED_VIDEO_MIME_TYPES,
        max_size_bytes=MAX_VIDEO_SIZE_BYTES,
        label="video",
    )

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.database import Base, build_engine
from app.main import create_app
from app.services.storage import StoredObject


class FakeStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.objects: dict[str, bytes] = {}

    def upload_upload_file(self, bucket: str, storage_path: str, upload):
        upload.file.seek(0)
        self.objects[f"{bucket}/{storage_path}"] = upload.file.read()
        upload.file.seek(0)
        return StoredObject(
            public_url=f"https://example.test/{bucket}/{storage_path}",
            storage_path=storage_path,
        )

    def upload_bytes(self, bucket: str, storage_path: str, data: bytes, *, content_type: str):
        self.objects[f"{bucket}/{storage_path}"] = data
        return StoredObject(
            public_url=f"https://example.test/{bucket}/{storage_path}",
            storage_path=storage_path,
        )

    def remove_object(self, bucket: str, storage_path: str | None) -> None:
        if storage_path:
            self.objects.pop(f"{bucket}/{storage_path}", None)


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    database_path = tmp_path / "test.db"
    settings = Settings(
        env="test",
        database_url=f"sqlite:///{database_path.as_posix()}",
        session_secret="test-secret",
        public_base_url="http://localhost:5173",
        cors_origins=["http://localhost:5173"],
        supabase_url="https://example.supabase.co",
        supabase_service_key="test-service-key",
    )
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)

    app = create_app(settings=settings, storage_service=FakeStorageService(settings))
    return TestClient(app)


@pytest.fixture
def sample_image_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), color=(28, 84, 132))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

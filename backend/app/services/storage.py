from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from supabase import Client, create_client

from app.config import Settings


class StorageServiceError(RuntimeError):
    pass


@dataclass(slots=True)
class StoredObject:
    public_url: str
    storage_path: str


class SupabaseStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: Client | None = None
        if settings.storage_enabled:
            self.client = create_client(settings.supabase_url, settings.supabase_service_key)

    def _resolve_local_demo_path(self, storage_path: str | None) -> Path | None:
        if not storage_path or not storage_path.startswith("local-demo/"):
            return None
        relative_path = storage_path.removeprefix("local-demo/")
        return Path(__file__).resolve().parents[3] / "frontend" / "public" / relative_path

    def _require_client(self) -> Client:
        if self.client is None:
            raise StorageServiceError("Media storage is not configured.")
        return self.client

    def build_public_url(self, bucket: str, storage_path: str) -> str:
        return f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{storage_path}"

    def upload_upload_file(self, bucket: str, storage_path: str, upload: UploadFile) -> StoredObject:
        client = self._require_client()
        upload.file.seek(0)
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=upload.file,
            file_options={
                "content-type": upload.content_type or "application/octet-stream",
                "upsert": "false",
            },
        )
        return StoredObject(
            public_url=self.build_public_url(bucket, storage_path),
            storage_path=storage_path,
        )

    def upload_bytes(
        self,
        bucket: str,
        storage_path: str,
        data: bytes,
        *,
        content_type: str,
    ) -> StoredObject:
        client = self._require_client()
        temp_path: str | None = None
        try:
            suffix = Path(storage_path).suffix or ".bin"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(data)
                temp_path = temp_file.name
            with open(temp_path, "rb") as handle:
                client.storage.from_(bucket).upload(
                    path=storage_path,
                    file=handle,
                    file_options={"content-type": content_type, "upsert": "false"},
                )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

        return StoredObject(
            public_url=self.build_public_url(bucket, storage_path),
            storage_path=storage_path,
        )

    def remove_object(self, bucket: str, storage_path: str | None) -> None:
        if not storage_path:
            return
        local_demo_path = self._resolve_local_demo_path(storage_path)
        if local_demo_path is not None:
            if local_demo_path.exists():
                local_demo_path.unlink()
            return
        client = self._require_client()
        client.storage.from_(bucket).remove([storage_path])

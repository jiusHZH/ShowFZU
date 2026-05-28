from __future__ import annotations

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
        if self.settings.is_production:
            return None
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

    def _upload(self, bucket: str, storage_path: str, data: bytes, *, content_type: str) -> StoredObject:
        client = self._require_client()
        try:
            client.storage.from_(bucket).upload(
                path=storage_path,
                file=data,
                file_options={
                    "content-type": content_type,
                    "upsert": "false",
                },
            )
        except Exception as exc:
            raise StorageServiceError("Media storage upload failed.") from exc
        return StoredObject(
            public_url=self.build_public_url(bucket, storage_path),
            storage_path=storage_path,
        )

    def upload_upload_file(self, bucket: str, storage_path: str, upload: UploadFile) -> StoredObject:
        upload.file.seek(0)
        data = upload.file.read()
        upload.file.seek(0)
        return self._upload(
            bucket,
            storage_path,
            data,
            content_type=upload.content_type or "application/octet-stream",
        )

    def upload_bytes(
        self,
        bucket: str,
        storage_path: str,
        data: bytes,
        *,
        content_type: str,
    ) -> StoredObject:
        return self._upload(bucket, storage_path, data, content_type=content_type)

    def remove_object(self, bucket: str, storage_path: str | None) -> None:
        if not storage_path:
            return
        local_demo_path = self._resolve_local_demo_path(storage_path)
        if local_demo_path is not None:
            if local_demo_path.exists():
                local_demo_path.unlink()
            return
        client = self._require_client()
        try:
            client.storage.from_(bucket).remove([storage_path])
        except Exception as exc:
            raise StorageServiceError("Media storage deletion failed.") from exc

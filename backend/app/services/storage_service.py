"""Supabase Storage service for RAG reference documents.

Provides backend-only management of the private `knowledge-base` bucket:
- Source of truth for reference PDFs
- Uses SUPABASE_SERVICE_ROLE_KEY (backend only; never exposed to frontend)
- Automatic private bucket initialization
- Idempotent upload, download, and verification
"""

from __future__ import annotations

import mimetypes

from supabase import Client, create_client

from app.core.config import get_settings
from app.core.exceptions import StorageOperationError
from app.core.logging import get_logger

logger = get_logger("pharmaone.storage")

DEFAULT_KNOWLEDGE_BUCKET = "knowledge-base"
REFERENCE_DOCS_PREFIX = "reference-documents"


class StorageService:
    """Service wrapping Supabase Storage operations with service role authentication."""

    def __init__(
        self,
        supabase_url: str | None = None,
        service_role_key: str | None = None,
        client: Client | None = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            settings = get_settings()
            url = supabase_url or settings.SUPABASE_URL
            key = service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY
            if not url or not key:
                raise StorageOperationError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Storage operations.")
            self._client = create_client(url, key)

    @property
    def client(self) -> Client:
        return self._client

    def ensure_bucket(self, bucket_name: str = DEFAULT_KNOWLEDGE_BUCKET) -> bool:
        """Ensure the specified private bucket exists. Creates it if missing."""
        try:
            buckets = self._client.storage.list_buckets()
            existing_names = [b.name for b in buckets]
            if bucket_name not in existing_names:
                logger.info("Creating private Supabase storage bucket '%s'...", bucket_name)
                self._client.storage.create_bucket(bucket_name, options={"public": False})
                logger.info("Private bucket '%s' created successfully.", bucket_name)
            return True
        except Exception as exc:
            logger.error("Failed to verify/create storage bucket '%s': %s", bucket_name, exc)
            raise StorageOperationError(f"Failed to ensure storage bucket '{bucket_name}': {exc}") from exc

    def upload_file(
        self,
        bucket_name: str,
        path: str,
        data: bytes,
        content_type: str | None = None,
        upsert: bool = True,
    ) -> str:
        """Upload binary file content to Supabase Storage."""
        if not data:
            raise StorageOperationError(f"Cannot upload empty file to '{path}'.")

        mime = content_type or mimetypes.guess_type(path)[0] or "application/pdf"
        try:
            self.ensure_bucket(bucket_name)
            logger.info("Uploading %d bytes to %s/%s (content-type: %s)", len(data), bucket_name, path, mime)
            resp = self._client.storage.from_(bucket_name).upload(
                path=path,
                file=data,
                file_options={"content-type": mime, "upsert": str(upsert).lower()},
            )
            logger.info("Upload completed for %s/%s: %s", bucket_name, path, resp)
            return path
        except Exception as exc:
            logger.error("Failed to upload to %s/%s: %s", bucket_name, path, exc)
            raise StorageOperationError(f"Failed to upload '{path}' to bucket '{bucket_name}': {exc}") from exc

    def download_file(self, bucket_name: str, path: str) -> bytes:
        """Download file bytes from Supabase Storage."""
        try:
            logger.info("Downloading %s/%s...", bucket_name, path)
            data = self._client.storage.from_(bucket_name).download(path)
            if not data:
                raise StorageOperationError(f"Downloaded empty file from '{bucket_name}/{path}'.")
            return data
        except Exception as exc:
            logger.error("Failed to download %s/%s: %s", bucket_name, path, exc)
            raise StorageOperationError(f"Failed to download '{path}' from bucket '{bucket_name}': {exc}") from exc

    def list_files(self, bucket_name: str, prefix: str = REFERENCE_DOCS_PREFIX) -> list[str]:
        """List file paths in the bucket under the specified prefix."""
        try:
            items = self._client.storage.from_(bucket_name).list(prefix)
            file_names = []
            for item in items:
                name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
                if name and not name.startswith("."):
                    file_names.append(name)
            return file_names
        except Exception as exc:
            logger.error("Failed to list files in %s/%s: %s", bucket_name, prefix, exc)
            raise StorageOperationError(f"Failed to list files in '{bucket_name}/{prefix}': {exc}") from exc

    def file_exists(self, bucket_name: str, path: str) -> bool:
        """Check whether a file exists in the specified bucket path."""
        try:
            dir_name = "/".join(path.split("/")[:-1])
            file_name = path.split("/")[-1]
            items = self._client.storage.from_(bucket_name).list(dir_name)
            for item in items:
                item_name = item.get("name") if isinstance(item, dict) else getattr(item, "name", None)
                if item_name == file_name:
                    return True
            return False
        except Exception as exc:
            logger.warning("Error checking if file exists in %s/%s: %s", bucket_name, path, exc)
            return False

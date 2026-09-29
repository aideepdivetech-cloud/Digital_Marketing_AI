"""
MinIO file storage service — S3-compatible object storage for artifacts.
"""

from __future__ import annotations

import io
from typing import Optional
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from app.config import get_settings
from app.observability.logger import get_logger

logger = get_logger("app.services.file_service")


class FileService:
    """Manages file uploads, downloads, and bucket operations with MinIO."""

    def __init__(self):
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        """Lazy-initialize MinIO client."""
        if self._client is None:
            settings = get_settings()
            self._client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_root_user,
                secret_key=settings.minio_root_password,
                secure=settings.minio_secure,
            )
        return self._client

    async def ensure_buckets(self) -> None:
        """Create default buckets if they don't exist."""
        settings = get_settings()
        buckets = [settings.minio_default_bucket, "uploads", "backups"]

        for bucket_name in buckets:
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info("bucket_created", bucket=bucket_name)
            except S3Error as e:
                logger.error("bucket_create_failed", bucket=bucket_name, error=str(e))

    async def upload_file(
        self,
        bucket: str,
        file_path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file to MinIO. Returns the object path."""
        try:
            data_stream = io.BytesIO(data)
            self.client.put_object(
                bucket,
                file_path,
                data_stream,
                length=len(data),
                content_type=content_type,
            )
            logger.info("file_uploaded", bucket=bucket, path=file_path, size=len(data))
            return f"{bucket}/{file_path}"
        except S3Error as e:
            logger.error("file_upload_failed", bucket=bucket, path=file_path, error=str(e))
            raise

    async def upload_text(
        self,
        bucket: str,
        file_path: str,
        text: str,
        content_type: str = "text/plain",
    ) -> str:
        """Upload text content to MinIO."""
        return await self.upload_file(bucket, file_path, text.encode("utf-8"), content_type)

    async def download_file(self, bucket: str, file_path: str) -> bytes:
        """Download a file from MinIO. Returns raw bytes."""
        try:
            response = self.client.get_object(bucket, file_path)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error("file_download_failed", bucket=bucket, path=file_path, error=str(e))
            raise

    async def download_text(self, bucket: str, file_path: str) -> str:
        """Download a text file from MinIO."""
        data = await self.download_file(bucket, file_path)
        return data.decode("utf-8")

    async def delete_file(self, bucket: str, file_path: str) -> None:
        """Delete a file from MinIO."""
        try:
            self.client.remove_object(bucket, file_path)
            logger.info("file_deleted", bucket=bucket, path=file_path)
        except S3Error as e:
            logger.error("file_delete_failed", bucket=bucket, path=file_path, error=str(e))
            raise

    async def file_exists(self, bucket: str, file_path: str) -> bool:
        """Check if a file exists in MinIO."""
        try:
            self.client.stat_object(bucket, file_path)
            return True
        except S3Error:
            return False

    def generate_artifact_path(
        self,
        tenant_id: str,
        task_id: str,
        filename: str,
    ) -> str:
        """Generate a structured storage path for an artifact."""
        unique_id = uuid4().hex[:8]
        return f"tenants/{tenant_id}/tasks/{task_id}/{unique_id}_{filename}"

    async def get_presigned_url(
        self,
        bucket: str,
        file_path: str,
        expires_hours: int = 1,
    ) -> str:
        """Generate a pre-signed URL for temporary file access."""
        from datetime import timedelta
        try:
            url = self.client.presigned_get_object(
                bucket,
                file_path,
                expires=timedelta(hours=expires_hours),
            )
            return url
        except S3Error as e:
            logger.error("presigned_url_failed", bucket=bucket, path=file_path, error=str(e))
            raise


# Singleton instance
file_service = FileService()

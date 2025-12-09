from pathlib import Path
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class MinIOClient:
    def __init__(self) -> None:
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._ensure_buckets()

    def _ensure_buckets(self) -> None:
        """Ensure required buckets exist and have public read policy."""
        buckets = [
            getattr(settings, "MINIO_BUCKET_VIDEOS", None),
            getattr(settings, "MINIO_BUCKET_MARKERS", None),
            getattr(settings, "MINIO_BUCKET_THUMBNAILS", None),
        ]
        # Fallback to single bucket if separate buckets are not set
        fallback_bucket = getattr(settings, "MINIO_BUCKET_NAME", None)

        for bucket in [b for b in buckets if b] or ([fallback_bucket] if fallback_bucket else []):
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info("minio_bucket_created", bucket=bucket)
                else:
                    logger.info("minio_bucket_already_exists", bucket=bucket)
                
                # Set public read policy
                policy = (
                    "{"
                    '"Version": "2012-10-17",'
                    '"Statement": [{' 
                    '"Effect": "Allow",'
                    '"Principal": "*",'
                    '"Action": "s3:GetObject",'
                    f'"Resource": "arn:aws:s3:::{bucket}/*"'
                    '}]'
                    "}"
                )
                self.client.set_bucket_policy(bucket, policy)
                logger.info("minio_bucket_policy_set", bucket=bucket)
            except S3Error as e:
                if e.code == "BucketAlreadyOwnedByYou":
                    logger.info("minio_bucket_already_owned", bucket=bucket)
                    # Still try to set policy
                    try:
                        policy = (
                            "{"
                            '"Version": "2012-10-17",'
                            '"Statement": [{' 
                            '"Effect": "Allow",'
                            '"Principal": "*",'
                            '"Action": "s3:GetObject",'
                            f'"Resource": "arn:aws:s3:::{bucket}/*"'
                            '}]'
                            "}"
                        )
                        self.client.set_bucket_policy(bucket, policy)
                        logger.info("minio_bucket_policy_updated", bucket=bucket)
                    except S3Error as policy_error:
                        logger.error("minio_bucket_policy_failed", bucket=bucket, error=str(policy_error))
                else:
                    logger.error("minio_bucket_creation_failed", bucket=bucket, error=str(e))
                    raise RuntimeError(f"MinIO bucket setup failed: {e}")

    def upload_file(
        self,
        file_path: str,
        bucket: str,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a local file to MinIO and return public URL."""
        try:
            self.client.fput_object(
                bucket,
                object_name,
                file_path,
                content_type=content_type,
            )
            # Public URL (assuming Nginx serves MinIO or direct access)
            return f"http://{settings.MINIO_ENDPOINT}/{bucket}/{object_name}"
        except S3Error as e:
            logger.error("minio_upload_failed", file_path=file_path, bucket=bucket, object_name=object_name, error=str(e))
            raise RuntimeError(f"MinIO upload failed: {e}")

    def get_presigned_url(self, bucket: str, object_name: str, expires_hours: int = 1) -> str:
        """Get a presigned GET URL for an object."""
        try:
            return self.client.presigned_get_object(bucket, object_name, expires=timedelta(hours=expires_hours))
        except S3Error as e:
            logger.error("minio_presigned_url_failed", bucket=bucket, object_name=object_name, error=str(e))
            raise RuntimeError(f"MinIO presigned URL failed: {e}")


# Singleton instance
minio_client = MinIOClient()
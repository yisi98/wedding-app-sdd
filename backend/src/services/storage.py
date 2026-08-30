"""Object-storage abstraction (ADR-003).

Two interchangeable backends behind one interface:
- `S3Storage`  — S3-compatible (MinIO in dev, AliCloud OSS in prod) via boto3, with
  presigned-PUT direct upload.
- `LocalStorage` — filesystem backend for dev/test with no external infra. Its
  "presigned" URL points at a local dev upload endpoint that stands in for the direct
  client→OSS PUT.

`get_storage()` picks the backend from settings and is cached per process.
"""

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from ..config import get_settings


class Storage(Protocol):
    def presigned_put_url(self, key: str, content_type: str) -> str: ...
    # Signed read URL for private buckets; None when the backend can't presign
    # (LocalStorage — the caller then serves the bytes itself).
    def presigned_get_url(self, key: str, expires: int = 3600) -> str | None: ...
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    """Filesystem-backed storage rooted at ``base_dir``."""

    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = self.base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def presigned_put_url(self, key: str, content_type: str) -> str:
        # Dev stand-in for a real presigned OSS URL; the client PUTs bytes here.
        return f"/api/v1/media/upload/raw?key={key}"

    def presigned_get_url(self, key: str, expires: int = 3600) -> str | None:
        return None

    def put(self, key: str, data: bytes) -> None:
        self._path(key).write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return (self.base / key).exists()

    def delete(self, key: str) -> None:
        (self.base / key).unlink(missing_ok=True)


class S3Storage:
    """S3-compatible backend (MinIO / AliCloud OSS)."""

    def __init__(
        self,
        endpoint: str | None,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str | None = None,
    ) -> None:
        import boto3  # imported lazily so local/dev needs no boto3
        from botocore.config import Config

        self.bucket = bucket
        # AliCloud OSS signs with SigV4, which requires a region (e.g. cn-beijing for
        # oss-cn-beijing); without it presigning raises NoRegionError. MinIO accepts any.
        # OSS also rejects path-style URLs (SecondLevelDomainForbidden), so requests
        # must address the bucket as a virtual host: bucket.oss-cn-beijing.aliyuncs.com.
        # MinIO (dev) has no MINIO_DOMAIN, so it needs path-style — pick per endpoint.
        is_oss = endpoint is not None and "aliyuncs.com" in endpoint
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                signature_version="s3v4",
                # boto3 >= 1.36 adds flexible checksums to streaming uploads by default,
                # encoding the body as STREAMING-UNSIGNED-PAYLOAD-TRAILER — OSS rejects
                # that with NotImplemented. "when_required" restores the classic
                # behavior (checksum only when the operation demands one).
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                s3={"addressing_style": "virtual" if is_oss else "path"},
            ),
        )

    def presigned_put_url(self, key: str, content_type: str) -> str:
        # Content-Type must be part of the signature: the client PUTs with it, and OSS
        # (unlike MinIO) rejects the request with SignatureDoesNotMatch otherwise.
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=3600,
        )

    def presigned_get_url(self, key: str, expires: int = 3600) -> str | None:
        # Signed GET for a private bucket. OSS/S3 serve HTTP Range requests natively,
        # which <video> seeking (iOS Safari requires 206 responses) needs, and this
        # keeps large media bytes out of the backend process entirely.
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                # Content is immutable (keys embed the file hash), so the object may be
                # cached hard even though the signed URL itself is short-lived.
                "ResponseCacheControl": "public, max-age=31536000, immutable",
            },
            ExpiresIn=expires,
        )

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    if s.storage_access_key and s.storage_secret_key:
        return S3Storage(
            s.storage_endpoint,
            s.storage_access_key,
            s.storage_secret_key,
            s.storage_bucket,
            s.storage_region,
        )
    return LocalStorage(s.storage_dir)

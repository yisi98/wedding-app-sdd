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
    def presigned_put_url(self, key: str) -> str: ...
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

    def presigned_put_url(self, key: str) -> str:
        # Dev stand-in for a real presigned OSS URL; the client PUTs bytes here.
        return f"/api/v1/media/upload/raw?key={key}"

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

    def __init__(self, endpoint: str | None, access_key: str, secret_key: str, bucket: str) -> None:
        import boto3  # imported lazily so local/dev needs no boto3

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def presigned_put_url(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "put_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=3600
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
        return S3Storage(s.storage_endpoint, s.storage_access_key, s.storage_secret_key, s.storage_bucket)
    return LocalStorage(s.storage_dir)

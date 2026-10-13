"""Where uploaded originals live: S3 when S3_BUCKET_NAME is set, else a local directory."""

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from botocore.exceptions import BotoCoreError, ClientError

from src.core.aws import s3_client
from src.core.database import settings
from src.core.logging import logger


class StorageError(Exception):
    """The original could not be stored or read; the message is safe to show the user."""


class FileStore(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class LocalFileStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"invalid storage key: {key}")
        return path

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3FileStore:
    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        self.client = client or s3_client()

    async def _call(self, action: str, fn, **kwargs):
        try:
            return await asyncio.to_thread(fn, Bucket=self.bucket, **kwargs)
        except (BotoCoreError, ClientError) as e:
            logger.error(f"S3 {action} failed for {kwargs.get('Key')}: {e!r}")
            raise StorageError(f"Could not {action} the file in S3 storage.") from e

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await self._call(
            "store", self.client.put_object, Key=key, Body=data, ContentType=content_type
        )

    async def get(self, key: str) -> bytes:
        obj = await self._call("read", self.client.get_object, Key=key)
        return await asyncio.to_thread(obj["Body"].read)

    async def delete(self, key: str) -> None:
        await self._call("delete", self.client.delete_object, Key=key)


@lru_cache
def get_file_store() -> FileStore:
    if settings.S3_BUCKET_NAME:
        return S3FileStore(settings.S3_BUCKET_NAME)
    return LocalFileStore(settings.UPLOAD_DIR)


def storage_key(user_id, document_id) -> str:
    return f"documents/{user_id}/{document_id}"

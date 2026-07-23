"""T19 S3兼容对象存储适配器；业务层不拼厂商URL或访问密钥。"""

from __future__ import annotations

import hashlib
import re
from typing import Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError


_SAFE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,511}$")


class StorageError(RuntimeError):
    """对象存储稳定错误；禁止携带endpoint、bucket、对象正文或凭证。"""


class StorageAdapter(Protocol):
    def put(self, *, object_key: str, body: bytes, mime_type: str, sha256: str) -> None: ...
    def get(self, object_key: str, *, expected_size: int) -> bytes: ...
    def delete(self, object_key: str) -> None: ...
    def check(self) -> bool: ...


class S3StorageAdapter:
    """封装MinIO、S3兼容网关等厂商差异，并在写读边界校验内容哈希。"""

    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        connect_timeout_seconds: int = 3,
        read_timeout_seconds: int = 30,
        max_attempts: int = 3,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=connect_timeout_seconds,
                read_timeout=read_timeout_seconds,
                retries={"max_attempts": max_attempts, "mode": "standard"},
            ),
        )

    def put(self, *, object_key: str, body: bytes, mime_type: str, sha256: str) -> None:
        self._validate_key(object_key)
        if hashlib.sha256(body).hexdigest() != sha256:
            raise ValueError("对象哈希不匹配")
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=object_key,
                Body=body,
                ContentType=mime_type,
                Metadata={"sha256": sha256},
            )
            head = self._client.head_object(Bucket=self._bucket, Key=object_key)
        except (BotoCoreError, ClientError):
            raise StorageError("对象存储暂时不可用") from None
        if head.get("ContentLength") != len(body) or head.get("Metadata", {}).get("sha256") != sha256:
            raise StorageError("对象存储写入校验失败")

    def get(self, object_key: str, *, expected_size: int) -> bytes:
        self._validate_key(object_key)
        if expected_size <= 0:
            raise ValueError("对象大小无效")
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=object_key)
            if response.get("ContentLength") != expected_size:
                raise StorageError("对象存储内容校验失败")
            # 最多读取索引声明大小加1字节，防止被篡改对象造成无界内存读取。
            body = response["Body"].read(expected_size + 1)
            expected = response.get("Metadata", {}).get("sha256")
        except (BotoCoreError, ClientError, KeyError, OSError):
            raise StorageError("对象存储暂时不可用") from None
        if len(body) != expected_size or not expected or hashlib.sha256(body).hexdigest() != expected:
            raise StorageError("对象存储内容校验失败")
        return body

    def delete(self, object_key: str) -> None:
        self._validate_key(object_key)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=object_key)
        except (BotoCoreError, ClientError):
            raise StorageError("对象存储暂时不可用") from None

    def exists(self, object_key: str) -> bool:
        """只用于运维验证存在性；404与平台故障必须严格区分。"""
        self._validate_key(object_key)
        try:
            self._client.head_object(Bucket=self._bucket, Key=object_key)
            return True
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise StorageError("对象存储暂时不可用") from None

    def check(self) -> bool:
        """只读bucket就绪探测，不创建对象且不暴露厂商异常。"""
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return True
        except (BotoCoreError, ClientError):
            raise StorageError("对象存储暂时不可用") from None

    @staticmethod
    def _validate_key(object_key: str) -> None:
        if (
            not isinstance(object_key, str)
            or not _SAFE_KEY.fullmatch(object_key)
            or object_key.startswith("/")
            or ".." in object_key.split("/")
            or "//" in object_key
        ):
            raise ValueError("对象键无效")


__all__ = ["S3StorageAdapter", "StorageAdapter", "StorageError"]

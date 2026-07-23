"""T20 PPTX归档与短期下载地址服务。"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote
from uuid import uuid4

from ..models.domain import PresentationExport
from ..repositories.exports import ExportConflict, ExportNotFound, ExportRepository, ExportWithFile
from .files import FileService, FileServiceError


_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class ExportServiceError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code, self.retryable = code, message, status_code, retryable


@dataclass(frozen=True)
class ArchivedExport:
    record: ExportWithFile
    download_url: str
    reused: bool = False


class ExportService:
    def __init__(
        self, *, repository: ExportRepository, file_service: FileService,
        download_signing_secret: str, download_url_ttl_seconds: int = 300,
        id_factory=lambda: uuid4().hex, now_factory=datetime.utcnow,
    ) -> None:
        if len(download_signing_secret) < 32 or not 30 <= download_url_ttl_seconds <= 3600:
            raise ValueError("下载签名配置无效")
        self.repository = repository
        self.file_service = file_service
        self.secret = download_signing_secret.encode("utf-8")
        self.ttl = download_url_ttl_seconds
        self.id_factory = id_factory
        self.now_factory = now_factory

    def archive(self, owner: int, presentation_id: str, version: int, request_id: str, expected_sha: str, body: bytes) -> ArchivedExport:
        if not _SAFE_ID.fullmatch(request_id) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise ExportServiceError("EXPORT_REQUEST_INVALID", "导出请求无效", 400)
        actual = hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(actual, expected_sha):
            raise ExportServiceError("EXPORT_HASH_MISMATCH", "导出文件摘要不匹配", 400)
        existing = self.repository.get_request(owner, request_id)
        if existing:
            if (existing.export.presentation_id, existing.export.presentation_version, existing.file.sha256) != (presentation_id, version, actual):
                raise ExportServiceError("EXPORT_IDEMPOTENCY_CONFLICT", "幂等键已用于其他导出", 409)
            return self._archived(owner, existing, True)
        file = None
        try:
            file = self.file_service.store(owner, presentation_id, purpose="pptx", mime_type=PPTX_MIME, body=body)
            row, reused = self.repository.create(PresentationExport(
                id=self.id_factory(), owner_user_id=owner, request_id=request_id,
                presentation_id=presentation_id, presentation_version=version,
                file_id=file.id, export_format="pptx", created_at=self.now_factory(),
            ))
        except ExportConflict:
            if file is not None:
                self.file_service.delete_unreferenced(owner, file.id, purpose="pptx")
            raise ExportServiceError("EXPORT_VERSION_CONFLICT", "作品版本已变化", 409) from None
        except ExportNotFound:
            if file is not None:
                self.file_service.delete_unreferenced(owner, file.id, purpose="pptx")
            raise ExportServiceError("EXPORT_NOT_FOUND", "作品不存在", 404) from None
        except FileServiceError as exc:
            status = 413 if exc.code == "FILE_TOO_LARGE" else 404 if exc.code == "FILE_OWNER_NOT_FOUND" else 503
            raise ExportServiceError(exc.code, exc.message, status, retryable=exc.retryable) from None
        except Exception:
            if file is not None:
                self.file_service.delete_unreferenced(owner, file.id, purpose="pptx")
            raise
        if reused and (
            row.export.presentation_id,
            row.export.presentation_version,
            row.file.sha256,
        ) != (presentation_id, version, actual):
            # 唯一约束输给另一并发请求时，清理本请求尚未被引用的文件。
            self.file_service.delete_unreferenced(owner, file.id, purpose="pptx")
            raise ExportServiceError("EXPORT_IDEMPOTENCY_CONFLICT", "幂等键已用于其他导出", 409)
        return self._archived(owner, row, reused)

    def list(self, owner: int, presentation_id: str) -> tuple[ArchivedExport, ...]:
        try:
            return tuple(self._archived(owner, row) for row in self.repository.list(owner, presentation_id))
        except ExportNotFound:
            raise ExportServiceError("EXPORT_NOT_FOUND", "作品不存在", 404) from None

    def store_thumbnail(self, owner: int, presentation_id: str, expected_sha: str, body: bytes) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha) or not hmac.compare_digest(hashlib.sha256(body).hexdigest(), expected_sha):
            raise ExportServiceError("EXPORT_HASH_MISMATCH", "缩略图摘要不匹配", 400)
        file = None
        try:
            file = self.file_service.store(owner, presentation_id, purpose="thumbnail", mime_type="image/png", body=body)
            previous = self.repository.set_thumbnail(owner, presentation_id, file.id)
            if previous and previous != file.id:
                self.file_service.delete_unreferenced(owner, previous, purpose="thumbnail")
            return file.id
        except ExportNotFound:
            if file is not None:
                self.file_service.delete_unreferenced(owner, file.id, purpose="thumbnail")
            raise ExportServiceError("EXPORT_NOT_FOUND", "作品不存在", 404) from None
        except FileServiceError as exc:
            raise ExportServiceError(exc.code, exc.message, 400 if exc.code.startswith("FILE_") else 503, retryable=exc.retryable) from None
        except Exception:
            if file is not None:
                self.file_service.delete_unreferenced(owner, file.id, purpose="thumbnail")
            raise

    def download(self, owner: int, file_id: str, expires: int, signature: str) -> tuple[bytes, ExportWithFile]:
        if expires < int(self.now_factory().timestamp()):
            raise ExportServiceError("DOWNLOAD_URL_EXPIRED", "下载地址已过期", 410)
        if expires > int(self.now_factory().timestamp()) + self.ttl + 5:
            raise ExportServiceError("DOWNLOAD_URL_INVALID", "下载地址无效", 400)
        expected = self._signature(owner, file_id, expires)
        if not hmac.compare_digest(expected, signature):
            # owner也参与签名；签名不匹配统一伪装成不存在，避免枚举其他用户文件。
            raise ExportServiceError("EXPORT_NOT_FOUND", "文件不存在", 404)
        row = self.repository.downloadable(owner, file_id)
        if row is None:
            raise ExportServiceError("EXPORT_NOT_FOUND", "文件不存在", 404)
        try:
            return self.file_service.read(owner, file_id), row
        except FileServiceError as exc:
            raise ExportServiceError(exc.code, exc.message, 404 if exc.code == "FILE_NOT_FOUND" else 503, retryable=exc.retryable) from None

    def _archived(self, owner: int, row: ExportWithFile, reused: bool = False) -> ArchivedExport:
        expires = int(self.now_factory().timestamp()) + self.ttl
        signature = self._signature(owner, row.file.id, expires)
        url = f"/api/files/{quote(row.file.id)}/download?expires={expires}&signature={signature}"
        return ArchivedExport(row, url, reused)

    def _signature(self, owner: int, file_id: str, expires: int) -> str:
        payload = f"{owner}:{file_id}:{expires}".encode("utf-8")
        return hmac.new(self.secret, payload, hashlib.sha256).hexdigest()

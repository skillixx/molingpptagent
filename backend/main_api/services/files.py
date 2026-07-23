"""T19 文件写读服务：签名校验、服务端对象键、配额和失败补偿。"""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from zipfile import BadZipFile, ZipFile
from datetime import datetime
from uuid import uuid4

from ..integrations.storage import StorageAdapter, StorageError
from ..models.domain import StoredFile
from ..repositories.files import FileOwnerNotFound, FileQuotaExceeded, FileRepository


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PURPOSES = {"source", "attachment", "checkpoint", "pptx", "thumbnail"}


class FileServiceError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class FileService:
    def __init__(
        self,
        *,
        repository: FileRepository,
        storage: StorageAdapter,
        storage_prefix: str,
        user_storage_quota_bytes: int,
        upload_file_max_bytes: int = 50 * 1024 * 1024,
        export_pptx_max_bytes: int = 100 * 1024 * 1024,
        thumbnail_max_bytes: int = 2 * 1024 * 1024,
        id_factory=lambda: uuid4().hex,
        now_factory=datetime.utcnow,
    ) -> None:
        normalized_prefix = storage_prefix.strip("/")
        if not normalized_prefix or any(
            not _SAFE_SEGMENT.fullmatch(part) for part in normalized_prefix.split("/")
        ):
            raise ValueError("对象存储前缀无效")
        if min(
            user_storage_quota_bytes,
            upload_file_max_bytes,
            export_pptx_max_bytes,
            thumbnail_max_bytes,
        ) <= 0:
            raise ValueError("文件容量配置必须大于零")
        self.repository = repository
        self.storage = storage
        self.storage_prefix = normalized_prefix
        self.user_storage_quota_bytes = user_storage_quota_bytes
        self.upload_file_max_bytes = upload_file_max_bytes
        self.export_pptx_max_bytes = export_pptx_max_bytes
        self.thumbnail_max_bytes = thumbnail_max_bytes
        self.id_factory = id_factory
        self.now_factory = now_factory

    def store(
        self,
        owner_user_id: int,
        presentation_id: str,
        *,
        purpose: str,
        mime_type: str,
        body: bytes,
    ) -> StoredFile:
        if owner_user_id <= 0 or not _SAFE_SEGMENT.fullmatch(presentation_id):
            raise FileServiceError("FILE_OWNER_NOT_FOUND", "作品不存在")
        if purpose not in _PURPOSES:
            raise FileServiceError("FILE_PURPOSE_INVALID", "文件用途无效")
        if not isinstance(body, bytes) or not body:
            raise FileServiceError("FILE_EMPTY", "文件不能为空")
        limit = (
            self.export_pptx_max_bytes
            if purpose == "pptx"
            else self.thumbnail_max_bytes
            if purpose == "thumbnail"
            else self.upload_file_max_bytes
        )
        if len(body) > limit:
            raise FileServiceError("FILE_TOO_LARGE", "文件超过大小上限")
        self._validate_signature(mime_type, body)

        digest = hashlib.sha256(body).hexdigest()
        now = self.now_factory()
        file_id = self.id_factory()
        if not _SAFE_SEGMENT.fullmatch(file_id):
            raise RuntimeError("file id factory returned unsafe value")
        # 客户端文件名从不参与对象键，sha使同作品同用途同内容天然幂等。
        object_key = (
            f"{self.storage_prefix}/users/{owner_user_id}/presentations/"
            f"{presentation_id}/{purpose}/{digest}"
        )
        file = StoredFile(
            id=file_id,
            owner_user_id=owner_user_id,
            presentation_id=presentation_id,
            purpose=purpose,
            object_key=object_key,
            mime_type=mime_type,
            size_bytes=len(body),
            sha256=digest,
            status="uploading",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        try:
            reserved = self.repository.reserve(
                file, user_storage_quota_bytes=self.user_storage_quota_bytes
            )
        except FileOwnerNotFound:
            raise FileServiceError("FILE_OWNER_NOT_FOUND", "作品不存在") from None
        except FileQuotaExceeded:
            raise FileServiceError("STORAGE_QUOTA_EXCEEDED", "存储空间不足") from None
        if reserved.reused:
            if reserved.ready:
                return reserved.file
            raise FileServiceError(
                "FILE_UPLOAD_IN_PROGRESS", "相同文件正在上传", retryable=True
            )

        try:
            self.storage.put(
                object_key=object_key,
                body=body,
                mime_type=mime_type,
                sha256=digest,
            )
            activated = self.repository.activate(owner_user_id, file_id, self.now_factory())
            if activated is None:
                raise StorageError("文件索引提交失败")
            return activated
        except StorageError:
            # 对象写成功但本地激活失败时先尽力删孤儿，再幂等释放占额；不暴露厂商异常正文。
            deleted = False
            try:
                self.storage.delete(object_key)
                deleted = True
            except StorageError:
                pass
            if deleted:
                self.repository.fail_upload(owner_user_id, file_id, self.now_factory())
            raise FileServiceError(
                "STORAGE_UNAVAILABLE", "对象存储暂时不可用", retryable=True
            ) from None

    def read(self, owner_user_id: int, file_id: str) -> bytes:
        file = self.repository.get_active(owner_user_id, file_id)
        if file is None:
            raise FileServiceError("FILE_NOT_FOUND", "文件不存在")
        try:
            body = self.storage.get(file.object_key, expected_size=file.size_bytes)
        except StorageError:
            raise FileServiceError(
                "STORAGE_UNAVAILABLE", "对象存储暂时不可用", retryable=True
            ) from None
        if len(body) != file.size_bytes or hashlib.sha256(body).hexdigest() != file.sha256:
            raise FileServiceError("FILE_INTEGRITY_FAILED", "文件完整性校验失败")
        return body

    def recover_stale_uploads(self, stale_before: datetime, *, limit: int = 100) -> int:
        """进程崩溃恢复：对象删除成功后才释放占额，删除失败保留记录供下一轮重试。"""
        if limit <= 0:
            raise ValueError("恢复批次必须大于零")
        recovered = 0
        for candidate in self.repository.list_stale_uploads(stale_before, limit=limit):
            file = self.repository.claim_stale_upload(
                candidate.id, stale_before=stale_before, now=self.now_factory()
            )
            if file is None:
                continue
            try:
                self.storage.delete(file.object_key)
            except StorageError:
                # 删除失败保持recovering_upload和占额；超过新租约后可再次恢复。
                continue
            recovered += int(
                self.repository.fail_upload(file.owner_user_id, file.id, self.now_factory())
            )
        return recovered

    def recover_stale_deletions(self, stale_before: datetime, *, limit: int = 100) -> int:
        """物理删除后本地提交前崩溃时，重放delete并最终释放索引与占额。"""
        recovered = 0
        for candidate in self.repository.list_stale_deletions(stale_before, limit=limit):
            file = self.repository.recover_deletion(
                candidate.id, stale_before=stale_before, now=self.now_factory()
            )
            if file is None:
                continue
            try:
                self.storage.delete(file.object_key)
            except StorageError:
                continue
            recovered += int(self.repository.complete_delete(
                file.owner_user_id, file.id, self.now_factory()
            ))
        return recovered

    def delete_unreferenced(self, owner_user_id: int, file_id: str, *, purpose: str) -> bool:
        """引用提交失败后的补偿删除；对象删除成功前不释放配额。"""
        file = self.repository.claim_unreferenced_file(
            owner_user_id, file_id, purpose, self.now_factory()
        )
        if file is None:
            return False
        try:
            self.storage.delete(file.object_key)
        except StorageError:
            # 保持deleting；租约到期由recover_stale_deletions用同一对象键重放。
            return False
        return self.repository.complete_delete(owner_user_id, file_id, self.now_factory())

    def cleanup_unreferenced_checkpoints(
        self, stale_before: datetime, *, limit: int = 100
    ) -> int:
        """清理冲突、崩溃或版本裁剪留下的检查点对象；引用仍存在时绝不删除。"""
        if limit <= 0:
            raise ValueError("清理批次必须大于零")
        cleaned = 0
        candidates = self.repository.list_checkpoint_cleanup_candidates(
            stale_before, limit=limit
        )
        for candidate in candidates:
            claimed = self.repository.claim_unreferenced_checkpoint(
                candidate.id, stale_before=stale_before, now=self.now_factory()
            )
            if claimed is None:
                continue
            try:
                self.storage.delete(claimed.object_key)
            except StorageError:
                # delete响应未知时保持deleting和占额，租约到期后按同一键重放，禁止恢复成伪active。
                continue
            cleaned += int(self.repository.complete_delete(
                claimed.owner_user_id, claimed.id, self.now_factory()
            ))
        return cleaned

    @staticmethod
    def _validate_signature(mime_type: str, body: bytes) -> None:
        valid = False
        if mime_type == "application/pdf":
            valid = body.startswith(b"%PDF-")
        elif mime_type in {"text/plain", "text/markdown", "application/json"}:
            try:
                body.decode("utf-8")
                valid = b"\x00" not in body
            except UnicodeDecodeError:
                valid = False
        elif mime_type in {
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            try:
                with ZipFile(BytesIO(body)) as archive:
                    names = set(archive.namelist())
                required = (
                    "ppt/presentation.xml"
                    if mime_type.endswith("presentationml.presentation")
                    else "word/document.xml"
                )
                valid = (
                    len(names) <= 10_000
                    and "[Content_Types].xml" in names
                    and required in names
                )
            except (BadZipFile, OSError, ValueError):
                valid = False
        elif mime_type == "image/png":
            valid = body.startswith(b"\x89PNG\r\n\x1a\n")
        elif mime_type == "image/jpeg":
            valid = body.startswith(b"\xff\xd8\xff")
        elif mime_type == "image/webp":
            valid = len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP"
        elif mime_type == "application/gzip":
            valid = body.startswith(b"\x1f\x8b")
        if not valid:
            raise FileServiceError("FILE_SIGNATURE_INVALID", "文件类型与内容不匹配")


__all__ = ["FileService", "FileServiceError"]

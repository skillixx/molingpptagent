"""T09 作品业务服务：owner作用域、原子创建、复制和软删除。"""

from __future__ import annotations

import json
import math
import uuid
import base64
import binascii
import gzip
import hashlib
import logging
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

from ..models.domain import BillingOperation, GenerationTask, Presentation, PresentationVersion
from ..repositories.resources import (
    PresentationCreateResult,
    PresentationLimitReached,
    PresentationPage,
    PresentationRepository,
    PresentationRequestConflict,
    PresentationSort,
    PresentationVersionRepository,
)
from ..schemas.presentations import (
    CreateCheckpointRequest,
    CreatePresentationRequest,
    SaveDraftPresentationRequest,
    RestoreCheckpointRequest,
    SavePresentationRequest,
)
from .files import FileService, FileServiceError


logger = logging.getLogger(__name__)


class PresentationServiceError(RuntimeError):
    """可安全映射到API的业务错误，不携带数据库异常或用户正文。"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


@dataclass(frozen=True)
class PresentationList:
    page: PresentationPage
    page_number: int
    page_size: int


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint: PresentationVersion
    content_sha256: str
    uncompressed_bytes: int
    created: bool = True


class PresentationService:
    """API编排只接收可信owner，浏览器字段无法改变作用域。"""

    def __init__(
        self,
        repository: PresentationRepository,
        *,
        task_max_attempts: int,
        user_presentation_limit: int | None,
        presentation_json_max_bytes: int = 10 * 1024 * 1024,
        checkpoint_max_count: int = 20,
        checkpoint_inline_max_bytes: int = 1024 * 1024,
        billing_enabled: bool = False,
        billing_product_id: int | None = None,
        billing_reserve_points: int | None = None,
        billing_settle_points: int | None = None,
        file_service: FileService | None = None,
        storage_upload_stale_seconds: int = 900,
        id_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.task_max_attempts = task_max_attempts
        self.user_presentation_limit = user_presentation_limit
        self.presentation_json_max_bytes = presentation_json_max_bytes
        self.checkpoint_max_count = checkpoint_max_count
        self.checkpoint_inline_max_bytes = checkpoint_inline_max_bytes
        if billing_enabled and (
            billing_product_id is None
            or billing_reserve_points is None
            or billing_settle_points is None
        ):
            # 开启计费时必须先锁定产品和金额，禁止生成无法审计的半成品计费任务。
            raise ValueError("billing configuration is incomplete")
        self.billing_enabled = billing_enabled
        self.billing_product_id = billing_product_id
        self.billing_reserve_points = billing_reserve_points
        self.billing_settle_points = billing_settle_points
        self.file_service = file_service
        self.storage_upload_stale_seconds = storage_upload_stale_seconds
        self.version_repository = PresentationVersionRepository(repository.engine)
        self.id_factory = id_factory or (lambda: str(uuid.uuid4()))
        self.now_factory = now_factory or (lambda: datetime.now(UTC).replace(tzinfo=None))

    def create(
        self,
        owner_user_id: int,
        request_id: str,
        request: CreatePresentationRequest,
        *,
        billing_entitlement_id: int | None = None,
    ) -> PresentationCreateResult:
        """作品、生成任务和可选计费意图同事务创建，失败时不留下孤儿记录。"""
        if self.billing_enabled and (
            type(billing_entitlement_id) is not int or billing_entitlement_id <= 0
        ):
            # 收费任务必须来自墨灵已精确绑定权益的入口，禁止退回按商品猜选。
            raise PresentationServiceError(
                "BILLING_ENTITLEMENT_REQUIRED",
                "请从墨灵指定的 PPT 资产重新进入应用",
                409,
            )
        now = self.now_factory()
        billing_mode = "prepaid" if self.billing_enabled else "none"
        presentation = Presentation(
            id=self.id_factory(),
            owner_user_id=owner_user_id,
            title=request.title,
            status="billing_pending" if self.billing_enabled else "generating",
            slides_json='{"slides":[]}',
            current_version=1,
            slide_count=0,
            template_id=request.template_id,
            thumbnail_file_id=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        task = GenerationTask(
            id=self.id_factory(),
            presentation_id=presentation.id,
            owner_user_id=owner_user_id,
            request_id=request_id,
            # 计费任务必须等 T17 预占成功后再进入 pending，Worker 只领取 pending 状态。
            status="billing_required" if self.billing_enabled else "pending",
            stage="awaiting_reserve" if self.billing_enabled else "queued",
            progress=0,
            input_json=json.dumps(
                {
                    "operation": "generate_presentation",
                    "title": request.title,
                    "content": request.content,
                    "language": request.language,
                    "model": request.model,
                    "template_id": request.template_id,
                    "generate_from_uploaded_file": request.generate_from_uploaded_file,
                    "generate_from_web_search": request.generate_from_web_search,
                    "billing_mode": billing_mode,
                    "billing_entitlement_id": billing_entitlement_id,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            error_message=None,
            retryable=True,
            attempt=0,
            max_attempts=self.task_max_attempts,
            next_attempt_at=now,
            locked_by=None,
            lock_token=None,
            locked_until=None,
            heartbeat_at=None,
            dispatch_started_at=None,
            last_error_code=None,
            started_at=None,
            finished_at=None,
            created_at=now,
            updated_at=now,
        )
        billing_operation: BillingOperation | None = None
        if self.billing_enabled:
            # 三个动作从任务 ID 派生稳定幂等键；T16 仅落意图，不发起任何平台写调用。
            billing_operation = BillingOperation(
                id=self.id_factory(),
                task_id=task.id,
                owner_user_id=owner_user_id,
                product_id=int(self.billing_product_id),
                entitlement_id=billing_entitlement_id,
                hold_id=None,
                action="reserve",
                reserved_amount=self.billing_reserve_points,
                actual_amount=self.billing_settle_points,
                status="planned",
                reserve_key=f"ppt:{task.id}:reserve",
                settle_key=f"ppt:{task.id}:settle",
                release_key=f"ppt:{task.id}:release",
                last_error_code=None,
                retry_count=0,
                next_retry_at=None,
                created_at=now,
                updated_at=now,
            )
        try:
            return self.repository.create_with_task(
                presentation,
                task,
                billing_operation=billing_operation,
                user_presentation_limit=self.user_presentation_limit,
            )
        except PresentationRequestConflict:
            raise PresentationServiceError(
                "PRESENTATION_REQUEST_CONFLICT", "请求标识已被其他操作占用", 409
            ) from None
        except PresentationLimitReached:
            raise PresentationServiceError(
                "PRESENTATION_LIMIT_REACHED", "作品数量已达到当前上限", 409
            ) from None

    def save_draft(
        self,
        owner_user_id: int,
        request_id: str,
        request: SaveDraftPresentationRequest,
    ):
        """把已在浏览器生成的完整编辑稿保存为草稿，不重复调用Agent或计费。"""
        now = self.now_factory()
        serialized = self._serialize_document(request.slides)
        # 用户作用域和幂等键共同派生ID；跨用户使用相同键不会碰撞或互相复用。
        presentation_id = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"trainppt:draft:{owner_user_id}:{request_id}")
        )
        presentation = Presentation(
            id=presentation_id,
            owner_user_id=owner_user_id,
            title=request.title,
            status="draft",
            slides_json=serialized,
            current_version=1,
            slide_count=len(request.slides["slides"]),
            template_id=request.template_id,
            thumbnail_file_id=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        try:
            return self.repository.create_draft(
                presentation,
                user_presentation_limit=self.user_presentation_limit,
            )
        except PresentationRequestConflict:
            raise PresentationServiceError(
                "PRESENTATION_REQUEST_CONFLICT", "请求标识已被其他操作占用", 409
            ) from None
        except PresentationLimitReached:
            raise PresentationServiceError(
                "PRESENTATION_LIMIT_REACHED", "作品数量已达到当前上限", 409
            ) from None

    def list(
        self,
        owner_user_id: int,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: str | None,
        sort: PresentationSort,
    ) -> PresentationList:
        normalized_search = search.strip() if search else None
        return PresentationList(
            self.repository.list_page(
                owner_user_id,
                page=page,
                page_size=page_size,
                search=normalized_search,
                status=status,
                sort=sort,
            ),
            page,
            page_size,
        )

    def get(self, owner_user_id: int, presentation_id: str) -> Presentation:
        presentation = self.repository.get(owner_user_id, presentation_id)
        if presentation is None:
            raise self._not_found()
        return presentation

    def duplicate(
        self,
        owner_user_id: int,
        presentation_id: str,
        title: str | None,
        slides: dict[str, object] | None = None,
    ) -> Presentation:
        source = self.repository.get(owner_user_id, presentation_id)
        if source is None:
            raise self._not_found()
        duplicate_title = title or self._copy_title(source.title)
        now = self.now_factory()
        duplicate = Presentation(
            id=self.id_factory(),
            owner_user_id=owner_user_id,
            title=duplicate_title,
            status="draft",
            slides_json='{"slides":[]}',
            current_version=1,
            slide_count=0,
            template_id=None,
            thumbnail_file_id=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        override_json: str | None = None
        override_count: int | None = None
        if slides is not None:
            override_json = self._serialize_document(slides)
            override_count = len(slides["slides"])
        try:
            copied = self.repository.duplicate(
                owner_user_id,
                presentation_id,
                duplicate,
                user_presentation_limit=self.user_presentation_limit,
                override_slides_json=override_json,
                override_slide_count=override_count,
            )
        except PresentationLimitReached:
            raise PresentationServiceError(
                "PRESENTATION_LIMIT_REACHED", "作品数量已达到当前上限", 409
            ) from None
        if copied is None:
            raise self._not_found()
        return copied

    def save(
        self,
        owner_user_id: int,
        presentation_id: str,
        request: SavePresentationRequest,
    ) -> Presentation:
        """按客户端基线版本保存规范当前稿，条件更新失败时返回脱敏冲突摘要。"""
        presentation = self.repository.get(owner_user_id, presentation_id)
        if presentation is None:
            raise self._not_found()
        if presentation.status not in {"ready", "draft"}:
            raise PresentationServiceError(
                "PRESENTATION_NOT_EDITABLE", "作品当前状态不可编辑", 409
            )
        serialized = self._serialize_document(request.slides)
        saved = self.repository.save_current(
            owner_user_id,
            presentation_id,
            title=request.title,
            slides_json=serialized,
            slide_count=len(request.slides["slides"]),
            base_version=request.base_version,
            updated_at=self.now_factory(),
        )
        if saved is None:
            # 删除或状态切换与保存竞争时，重新按owner判断，避免透露资源归属。
            current = self.repository.get(owner_user_id, presentation_id)
            if current is None:
                raise self._not_found()
            if current.status in {"ready", "draft"}:
                raise PresentationServiceError(
                    "PRESENTATION_VERSION_CONFLICT",
                    "作品已在其他页面更新",
                    409,
                    details={
                        "latest": {
                            "title": current.title,
                            "current_version": current.current_version,
                            "updated_at": (
                                current.updated_at.replace(tzinfo=UTC)
                                if current.updated_at.tzinfo is None
                                else current.updated_at.astimezone(UTC)
                            ).isoformat().replace("+00:00", "Z"),
                        }
                    },
                )
            raise PresentationServiceError(
                "PRESENTATION_NOT_EDITABLE", "作品当前状态不可编辑", 409
            )
        return saved

    def create_checkpoint(
        self,
        owner_user_id: int,
        presentation_id: str,
        request: CreateCheckpointRequest,
    ) -> CheckpointRecord:
        """把当前服务端稿压缩为检查点；同版本重复请求安全复用既有记录。"""
        presentation = self.repository.get(owner_user_id, presentation_id)
        if presentation is None:
            raise self._not_found()
        if presentation.status not in {"ready", "draft"}:
            raise PresentationServiceError(
                "PRESENTATION_NOT_EDITABLE", "作品当前状态不可创建检查点", 409
            )
        if presentation.current_version != request.base_version:
            raise self._version_conflict(presentation)
        raw = self._canonical_current_document(presentation)
        encoded = self._encode_checkpoint(
            raw, owner_user_id=owner_user_id, presentation_id=presentation_id
        )
        checkpoint = PresentationVersion(
            id=self.id_factory(),
            presentation_id=presentation_id,
            version=request.base_version,
            slides_json=encoded,
            reason=request.reason,
            created_by=owner_user_id,
            created_at=self.now_factory(),
        )
        result = self.version_repository.create_checkpoint(
            owner_user_id,
            presentation_id,
            checkpoint,
            base_version=request.base_version,
        )
        if result.state == "not_found":
            raise self._not_found()
        if result.state == "not_editable":
            raise PresentationServiceError(
                "PRESENTATION_NOT_EDITABLE", "作品当前状态不可创建检查点", 409
            )
        if result.state == "conflict":
            assert result.presentation is not None
            raise self._version_conflict(result.presentation)
        assert result.checkpoint is not None
        stored_raw = self._decode_checkpoint(result.checkpoint)
        return self._checkpoint_record(
            result.checkpoint, stored_raw, created=result.state == "created"
        )

    def list_checkpoints(
        self, owner_user_id: int, presentation_id: str
    ) -> tuple[CheckpointRecord, ...]:
        versions = self.version_repository.list_for_presentation(owner_user_id, presentation_id)
        if versions is None:
            raise self._not_found()
        return tuple(self._checkpoint_record(item, self._decode_checkpoint(item)) for item in versions)

    def restore_checkpoint(
        self,
        owner_user_id: int,
        presentation_id: str,
        target_version: int,
        request: RestoreCheckpointRequest,
    ) -> Presentation:
        """恢复历史稿时递增当前版本并新增restore检查点，绝不覆盖原历史行。"""
        target = self.version_repository.get_by_number(
            owner_user_id, presentation_id, target_version
        )
        if target is None:
            raise self._not_found()
        raw = self._decode_checkpoint(target)
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise PresentationServiceError(
                "PRESENTATION_VERSION_DATA_INVALID", "历史版本数据暂时无法读取", 500
            ) from None
        serialized = self._serialize_document(document)
        next_version = request.base_version + 1
        restored_checkpoint = PresentationVersion(
            id=self.id_factory(),
            presentation_id=presentation_id,
            version=next_version,
            slides_json=self._encode_checkpoint(
                serialized.encode("utf-8"),
                owner_user_id=owner_user_id,
                presentation_id=presentation_id,
            ),
            reason="restore",
            created_by=owner_user_id,
            created_at=self.now_factory(),
        )
        result = self.version_repository.restore(
            owner_user_id,
            presentation_id,
            target_version,
            base_version=request.base_version,
            slides_json=serialized,
            slide_count=len(document["slides"]),
            restored_checkpoint=restored_checkpoint,
            updated_at=self.now_factory(),
        )
        if result.state == "not_found":
            raise self._not_found()
        if result.state == "not_editable":
            raise PresentationServiceError(
                "PRESENTATION_NOT_EDITABLE", "作品当前状态不可恢复历史版本", 409
            )
        if result.state == "conflict":
            assert result.presentation is not None
            raise self._version_conflict(result.presentation)
        assert result.presentation is not None
        return result.presentation

    def _serialize_document(self, document: dict[str, object]) -> str:
        self._validate_document(document)
        serialized = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > self.presentation_json_max_bytes:
            raise PresentationServiceError(
                "PRESENTATION_DOCUMENT_TOO_LARGE", "作品内容超过保存上限", 413
            )
        return serialized

    def _canonical_current_document(self, presentation: Presentation) -> bytes:
        try:
            document = json.loads(presentation.slides_json)
        except (TypeError, json.JSONDecodeError):
            raise PresentationServiceError(
                "PRESENTATION_DATA_INVALID", "作品数据暂时无法读取", 500
            ) from None
        return self._serialize_document(document).encode("utf-8")

    def _encode_checkpoint(
        self, raw: bytes, *, owner_user_id: int, presentation_id: str
    ) -> str:
        compressed = gzip.compress(raw, compresslevel=6, mtime=0)
        if len(compressed) > self.checkpoint_inline_max_bytes:
            if self.file_service is None:
                raise PresentationServiceError(
                    "CHECKPOINT_STORAGE_UNAVAILABLE", "检查点超过数据库内联上限且对象存储尚不可用", 503
                )
            try:
                stored = self.file_service.store(
                    owner_user_id,
                    presentation_id,
                    purpose="checkpoint",
                    mime_type="application/gzip",
                    body=compressed,
                )
            except FileServiceError as exc:
                status = 409 if exc.code == "STORAGE_QUOTA_EXCEEDED" else 503
                raise PresentationServiceError(exc.code, exc.message, status) from None
            return json.dumps(
                {"format": "storage-gzip-v1", "file_id": stored.id},
                separators=(",", ":"),
            )
        return json.dumps(
            {
                "format": "gzip+base64-v1",
                "data": base64.b64encode(compressed).decode("ascii"),
            },
            separators=(",", ":"),
        )

    def _decode_checkpoint(self, checkpoint: PresentationVersion) -> bytes:
        try:
            envelope = json.loads(checkpoint.slides_json)
            if isinstance(envelope, dict) and envelope.get("format") == "gzip+base64-v1":
                encoded = envelope["data"]
                if not isinstance(encoded, str) or len(encoded) > (self.checkpoint_inline_max_bytes * 4 // 3 + 8):
                    raise ValueError("checkpoint envelope exceeds inline limit")
                compressed = base64.b64decode(encoded, validate=True)
                if len(compressed) > self.checkpoint_inline_max_bytes:
                    raise ValueError("checkpoint compressed body exceeds inline limit")
                raw = self._decompress_checkpoint(compressed)
            elif isinstance(envelope, dict) and envelope.get("format") == "storage-gzip-v1":
                file_id = envelope.get("file_id")
                if not isinstance(file_id, str) or self.file_service is None:
                    raise ValueError("checkpoint storage reference invalid")
                try:
                    compressed = self.file_service.read(checkpoint.created_by, file_id)
                except FileServiceError as exc:
                    if exc.code == "STORAGE_UNAVAILABLE":
                        raise PresentationServiceError(
                            "CHECKPOINT_STORAGE_UNAVAILABLE", "检查点对象存储暂时不可用", 503
                        ) from None
                    raise ValueError("checkpoint storage object invalid") from None
                raw = self._decompress_checkpoint(compressed)
            else:
                # 兼容迁移前已存在的原始JSON检查点，读取后续创建仍统一使用压缩信封。
                try:
                    raw = self._serialize_document(envelope).encode("utf-8")
                except PresentationServiceError:
                    raise ValueError("legacy checkpoint document is invalid") from None
            if len(raw) > self.presentation_json_max_bytes:
                raise ValueError("checkpoint exceeds document limit")
            return raw
        except (KeyError, TypeError, ValueError, OSError, binascii.Error, zlib.error, json.JSONDecodeError):
            raise PresentationServiceError(
                "PRESENTATION_VERSION_DATA_INVALID", "历史版本数据暂时无法读取", 500
            ) from None

    def _decompress_checkpoint(self, compressed: bytes) -> bytes:
        """所有内联和对象检查点共用同一受限解压边界，防止压缩炸弹。"""
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        raw = decompressor.decompress(compressed, self.presentation_json_max_bytes + 1)
        if (
            len(raw) > self.presentation_json_max_bytes
            or not decompressor.eof
            or decompressor.unused_data
            or decompressor.unconsumed_tail
        ):
            raise ValueError("checkpoint decompression limit exceeded")
        return raw

    @staticmethod
    def _checkpoint_record(
        checkpoint: PresentationVersion, raw: bytes, *, created: bool = True
    ) -> CheckpointRecord:
        return CheckpointRecord(
            checkpoint=checkpoint,
            content_sha256=hashlib.sha256(raw).hexdigest(),
            uncompressed_bytes=len(raw),
            created=created,
        )

    def prune_checkpoints(self, owner_user_id: int, presentation_id: str) -> None:
        """供响应后后台任务调用；失败只记录脱敏错误并保留已提交的新版本。"""
        try:
            self.version_repository.prune_oldest(
                owner_user_id, presentation_id, keep_count=self.checkpoint_max_count
            )
            if self.file_service is not None:
                self.file_service.cleanup_unreferenced_checkpoints(
                    self.now_factory()
                    - timedelta(seconds=self.storage_upload_stale_seconds),
                    # 候选中可能多数仍有引用，批次至少100，避免未引用对象因排序落在窗口外。
                    limit=max(self.checkpoint_max_count * 2, 100),
                )
        except Exception:
            # 清理属于提交后的可重试维护动作，失败不能撤销已创建的新版本，也不记录正文或原始ID。
            safe_id = hashlib.sha256(presentation_id.encode("utf-8")).hexdigest()[:12]
            logger.exception("检查点清理失败 presentation_hash=%s", safe_id)

    @staticmethod
    def _version_conflict(presentation: Presentation) -> PresentationServiceError:
        return PresentationServiceError(
            "PRESENTATION_VERSION_CONFLICT",
            "作品已在其他页面更新",
            409,
            details={
                "latest": {
                    "title": presentation.title,
                    "current_version": presentation.current_version,
                    "updated_at": (
                        presentation.updated_at.replace(tzinfo=UTC)
                        if presentation.updated_at.tzinfo is None
                        else presentation.updated_at.astimezone(UTC)
                    ).isoformat().replace("+00:00", "Z"),
                }
            },
        )

    @staticmethod
    def _validate_document(document: dict[str, object]) -> None:
        """只接收当前schema的完整页面骨架，避免把半结构稿写进主记录。"""
        if not set(document).issubset(
            {"schema_version", "slides", "theme", "viewport_size", "viewport_ratio"}
        ):
            raise PresentationServiceError(
                "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
            )
        if document.get("schema_version") != 1:
            raise PresentationServiceError(
                "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
            )
        slides = document.get("slides")
        if not isinstance(slides, list):
            raise PresentationServiceError(
                "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
            )
        for slide in slides:
            if (
                not isinstance(slide, dict)
                or not isinstance(slide.get("id"), str)
                or not slide["id"]
                or not isinstance(slide.get("elements"), list)
            ):
                raise PresentationServiceError(
                    "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
                )
            if "remark" in slide and not isinstance(slide["remark"], str):
                raise PresentationServiceError(
                    "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
                )
            if "notes" in slide and not isinstance(slide["notes"], list):
                raise PresentationServiceError(
                    "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
                )
            for element in slide["elements"]:
                if (
                    not isinstance(element, dict)
                    or not isinstance(element.get("id"), str)
                    or not element["id"]
                    or not isinstance(element.get("type"), str)
                    or not element["type"]
                ):
                    raise PresentationServiceError(
                        "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
                    )
        for key, minimum, maximum in (
            ("viewport_size", 320, 10_000),
            ("viewport_ratio", 0.1, 3),
        ):
            value = document.get(key)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < minimum
                or value > maximum
            ):
                raise PresentationServiceError(
                    "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
                )
        theme = document.get("theme")
        if theme is not None and not isinstance(theme, dict):
            raise PresentationServiceError(
                "PRESENTATION_DOCUMENT_INVALID", "作品数据格式无效", 422
            )

    def delete(self, owner_user_id: int, presentation_id: str) -> None:
        if not self.repository.soft_delete(
            owner_user_id, presentation_id, deleted_at=self.now_factory()
        ):
            raise self._not_found()

    @staticmethod
    def _copy_title(source: str) -> str:
        suffix = " 副本"
        return f"{source[: 255 - len(suffix)]}{suffix}"

    @staticmethod
    def _not_found() -> PresentationServiceError:
        return PresentationServiceError("PRESENTATION_NOT_FOUND", "作品不存在", 404)


__all__ = ["PresentationList", "PresentationService", "PresentationServiceError"]

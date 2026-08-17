"""资源所有权仓储；调用方不能绕过 owner 条件读取业务对象。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import BigInteger, Engine, asc, delete, desc, func, inspect, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ..models.domain import (
    BillingOperation,
    GenerationTask,
    Presentation,
    PresentationExport,
    PresentationVersion,
    StoredFile,
)


class _OwnerRepository:
    """具有直接 owner_user_id 列的资源仓储基类。"""

    model = Presentation

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def get(self, owner_user_id: int, resource_id: str):
        """他人资源与不存在资源统一返回 None，供 API 映射为 404。"""
        model = self.model
        conditions = [model.id == resource_id, model.owner_user_id == owner_user_id]
        if hasattr(model, "deleted_at"):
            conditions.append(model.deleted_at.is_(None))
        with self._session_factory() as db:
            return db.scalar(select(model).where(*conditions))


class PresentationRepository(_OwnerRepository):
    """作品仓储，默认排除软删除数据。"""

    model = Presentation

    def ensure_schema(self) -> None:
        """启动前检查迁移是否到位，禁止首个用户请求才暴露缺表500。"""
        try:
            schema = inspect(self.engine)
            tables = set(schema.get_table_names())
            if not {
                "trainppt_presentations", "trainppt_presentation_versions",
                "trainppt_generation_tasks", "trainppt_billing_operations"
            }.issubset(tables):
                raise PresentationSchemaError("作品数据表迁移未完成")
            task_columns = {column["name"] for column in schema.get_columns("trainppt_generation_tasks")}
            if "dispatch_started_at" not in task_columns:
                raise PresentationSchemaError("作品数据表迁移未完成")
            billing_columns = {
                column["name"]: column["type"]
                for column in schema.get_columns("trainppt_billing_operations")
            }
            if not {"entitlement_id", "hold_id"}.issubset(billing_columns):
                raise PresentationSchemaError("作品数据表迁移未完成")
            if not all(
                isinstance(billing_columns[name], BigInteger)
                for name in ("entitlement_id", "hold_id")
            ):
                raise PresentationSchemaError("作品数据表迁移未完成")
            task_uniques = {
                constraint["name"]
                for constraint in schema.get_unique_constraints("trainppt_generation_tasks")
            }
            if "uq_generation_tasks_owner_request" not in task_uniques:
                # 旧全局幂等约束会让不同用户互相冲突，必须在接流量前完成0005迁移。
                raise PresentationSchemaError("作品数据表迁移未完成")
        except PresentationSchemaError:
            raise
        except Exception:
            raise PresentationSchemaError("作品数据表迁移检查失败") from None

    def create_with_task(
        self,
        presentation: Presentation,
        task: GenerationTask,
        *,
        billing_operation: BillingOperation | None = None,
        user_presentation_limit: int | None,
    ) -> "PresentationCreateResult":
        """原子创建作品、任务及可选计费意图；兼容重试只能复用完全相同的请求。"""
        try:
            with self._session_factory.begin() as db:
                existing_task = db.scalar(
                    select(GenerationTask).where(
                        GenerationTask.owner_user_id == task.owner_user_id,
                        GenerationTask.request_id == task.request_id,
                    )
                )
                if existing_task is not None:
                    return self._reuse_existing_request(
                        db, presentation, task, billing_operation, existing_task
                    )

                self._ensure_capacity(
                    db, presentation.owner_user_id, user_presentation_limit
                )

                # ORM 模型没有声明对象关系，单次 add_all 无法保证 MySQL 按外键层级写入。
                # 仍保持同一事务，但依次 flush 父作品、子任务和可选计费意图，避免外键 1452。
                db.add(presentation)
                db.flush()
                db.add(task)
                db.flush()
                if billing_operation is not None:
                    db.add(billing_operation)
                    db.flush()
                return PresentationCreateResult(presentation, task, False)
        except IntegrityError:
            # 并发请求由用户作用域唯一约束判定输赢，败方必须重新核对完整业务载荷。
            with self._session_factory() as db:
                existing_task = db.scalar(
                    select(GenerationTask).where(
                        GenerationTask.owner_user_id == task.owner_user_id,
                        GenerationTask.request_id == task.request_id,
                    )
                )
                if existing_task is None:
                    raise PresentationRequestConflict from None
                return self._reuse_existing_request(
                    db, presentation, task, billing_operation, existing_task
                )

    def create_draft(
        self,
        presentation: Presentation,
        *,
        user_presentation_limit: int | None,
    ) -> "PresentationDraftCreateResult":
        """创建不带生成任务的可编辑草稿；确定性ID为网络重试提供幂等围栏。"""
        try:
            with self._session_factory.begin() as db:
                existing = db.get(Presentation, presentation.id)
                if existing is not None:
                    return self._reuse_existing_draft(existing, presentation)
                self._ensure_capacity(
                    db, presentation.owner_user_id, user_presentation_limit
                )
                db.add(presentation)
                db.flush()
                return PresentationDraftCreateResult(presentation, False)
        except IntegrityError:
            with self._session_factory() as db:
                existing = db.get(Presentation, presentation.id)
                if existing is None:
                    raise PresentationRequestConflict from None
                return self._reuse_existing_draft(existing, presentation)

    @staticmethod
    def _reuse_existing_draft(
        existing: Presentation,
        requested: Presentation,
    ) -> "PresentationDraftCreateResult":
        """同一幂等键只能复用完全相同且仍属于同一用户的草稿。"""
        if (
            existing.owner_user_id != requested.owner_user_id
            or existing.deleted_at is not None
            or existing.status != "draft"
            or existing.title != requested.title
            or existing.template_id != requested.template_id
            or existing.slides_json != requested.slides_json
        ):
            raise PresentationRequestConflict
        return PresentationDraftCreateResult(existing, True)

    @staticmethod
    def _reuse_existing_request(
        db: Session,
        presentation: Presentation,
        task: GenerationTask,
        billing_operation: BillingOperation | None,
        existing_task: GenerationTask,
    ) -> "PresentationCreateResult":
        """只复用同一业务请求，防止相同幂等键把新内容误绑定到旧作品。"""
        if existing_task.input_json != task.input_json:
            raise PresentationRequestConflict
        existing_presentation = db.scalar(
            select(Presentation).where(
                Presentation.id == existing_task.presentation_id,
                Presentation.owner_user_id == presentation.owner_user_id,
                Presentation.deleted_at.is_(None),
            )
        )
        if existing_presentation is None:
            raise PresentationRequestConflict

        existing_billing = db.scalar(
            select(BillingOperation).where(
                BillingOperation.task_id == existing_task.id,
                BillingOperation.owner_user_id == presentation.owner_user_id,
            )
        )
        if (billing_operation is None) != (existing_billing is None):
            raise PresentationRequestConflict
        if billing_operation is not None and existing_billing is not None:
            # 重试会先生成临时 task_id，因此只比较业务配置；已落库键必须由原 task_id 派生。
            expected = (
                billing_operation.product_id,
                billing_operation.reserved_amount,
                billing_operation.actual_amount,
            )
            actual = (
                existing_billing.product_id,
                existing_billing.reserved_amount,
                existing_billing.actual_amount,
            )
            stable_keys = (
                f"ppt:{existing_task.id}:reserve",
                f"ppt:{existing_task.id}:settle",
                f"ppt:{existing_task.id}:release",
            )
            actual_keys = (
                existing_billing.reserve_key,
                existing_billing.settle_key,
                existing_billing.release_key,
            )
            if actual != expected or actual_keys != stable_keys:
                raise PresentationRequestConflict
        return PresentationCreateResult(existing_presentation, existing_task, True)

    def list_page(
        self,
        owner_user_id: int,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: str | None,
        sort: "PresentationSort",
    ) -> "PresentationPage":
        """只查询当前owner，搜索自动转义通配符并使用稳定ID作为次排序键。"""
        conditions = [
            Presentation.owner_user_id == owner_user_id,
            Presentation.deleted_at.is_(None),
        ]
        if search:
            conditions.append(Presentation.title.contains(search, autoescape=True))
        if status:
            conditions.append(Presentation.status == status)
        orders = {
            "updated_desc": (desc(Presentation.updated_at), desc(Presentation.id)),
            "updated_asc": (asc(Presentation.updated_at), asc(Presentation.id)),
            "created_desc": (desc(Presentation.created_at), desc(Presentation.id)),
            "title_asc": (asc(Presentation.title), asc(Presentation.id)),
        }[sort]
        with self._session_factory() as db:
            total = int(
                db.scalar(select(func.count()).select_from(Presentation).where(*conditions)) or 0
            )
            items = db.scalars(
                select(Presentation)
                .where(*conditions)
                .order_by(*orders)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return PresentationPage(tuple(items), total)

    def duplicate(
        self,
        owner_user_id: int,
        presentation_id: str,
        duplicate: Presentation,
        *,
        user_presentation_limit: int | None,
        override_slides_json: str | None = None,
        override_slide_count: int | None = None,
    ) -> Presentation | None:
        """复制当前编辑稿；生成中、失败或计费待处理状态不能传播到新作品。"""
        with self._session_factory.begin() as db:
            source = db.scalar(
                select(Presentation).where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            )
            if source is None:
                return None
            self._ensure_capacity(db, owner_user_id, user_presentation_limit)
            duplicate.slides_json = override_slides_json or source.slides_json
            duplicate.slide_count = (
                override_slide_count if override_slide_count is not None else source.slide_count
            )
            duplicate.template_id = source.template_id
            duplicate.thumbnail_file_id = source.thumbnail_file_id
            duplicate.status = "ready" if source.status == "ready" else "draft"
            db.add(duplicate)
            db.flush()
            return duplicate

    def save_current(
        self,
        owner_user_id: int,
        presentation_id: str,
        *,
        title: str,
        slides_json: str,
        slide_count: int,
        base_version: int,
        updated_at: datetime,
    ) -> Presentation | None:
        """以owner和旧版本为条件原子更新当前稿，保证跨标签只有一个写入者成功。"""
        with self._session_factory.begin() as db:
            result = db.execute(
                update(Presentation)
                .where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                    Presentation.status.in_(("ready", "draft")),
                    Presentation.current_version == base_version,
                )
                .values(
                    title=title,
                    slides_json=slides_json,
                    slide_count=slide_count,
                    current_version=Presentation.current_version + 1,
                    updated_at=updated_at,
                )
            )
            if result.rowcount != 1:
                return None
            # 同一事务内按owner回读，响应不会因浏览器ID伪造返回他人作品。
            return db.scalar(
                select(Presentation).where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            )

    def soft_delete(self, owner_user_id: int, presentation_id: str, *, deleted_at: datetime) -> bool:
        """幂等软删除；只有资源 owner 能首次修改，重复调用仍报告目标已删除。"""
        with self._session_factory.begin() as db:
            existing = db.scalar(
                select(Presentation.id).where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                )
            )
            if existing is None:
                return False
            db.execute(
                update(Presentation)
                .where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
                .values(status="deleted", deleted_at=deleted_at, updated_at=deleted_at)
            )
            return True

    @staticmethod
    def _ensure_capacity(
        db: Session,
        owner_user_id: int,
        user_presentation_limit: int | None,
    ) -> None:
        """配置上限时锁定owner索引范围，避免并发创建共同越过容量检查。"""
        if user_presentation_limit is None:
            return
        active_ids = db.scalars(
            select(Presentation.id)
            .where(
                Presentation.owner_user_id == owner_user_id,
                Presentation.deleted_at.is_(None),
            )
            .limit(user_presentation_limit)
            .with_for_update()
        ).all()
        if len(active_ids) >= user_presentation_limit:
            raise PresentationLimitReached


PresentationSort = Literal["updated_desc", "updated_asc", "created_desc", "title_asc"]


@dataclass(frozen=True)
class PresentationPage:
    items: tuple[Presentation, ...]
    total: int


@dataclass(frozen=True)
class PresentationCreateResult:
    presentation: Presentation
    task: GenerationTask
    reused: bool


@dataclass(frozen=True)
class PresentationDraftCreateResult:
    presentation: Presentation
    reused: bool


class PresentationRequestConflict(RuntimeError):
    """请求幂等键已被不兼容的业务请求占用。"""


class PresentationLimitReached(RuntimeError):
    """当前owner已达到配置的作品数量上限。"""


class PresentationSchemaError(RuntimeError):
    """数据库尚未迁移到作品/任务所需版本；错误不包含连接信息。"""


class StoredFileRepository(_OwnerRepository):
    model = StoredFile


class PresentationVersionRepository:
    """版本自身不冗余 owner，必须联结未删除作品完成归属校验。"""

    def __init__(self, engine: Engine) -> None:
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def create_checkpoint(
        self,
        owner_user_id: int,
        presentation_id: str,
        checkpoint: PresentationVersion,
        *,
        base_version: int,
    ) -> "CheckpointCreateResult":
        """在作品行锁内校验版本并创建唯一检查点；重复请求复用原记录。"""
        try:
            with self._session_factory.begin() as db:
                presentation = db.scalar(
                    select(Presentation)
                    .where(
                        Presentation.id == presentation_id,
                        Presentation.owner_user_id == owner_user_id,
                        Presentation.deleted_at.is_(None),
                    )
                    .with_for_update()
                )
                if presentation is None:
                    return CheckpointCreateResult("not_found")
                if presentation.status not in {"ready", "draft"}:
                    return CheckpointCreateResult("not_editable", presentation=presentation)
                if presentation.current_version != base_version:
                    return CheckpointCreateResult("conflict", presentation=presentation)
                existing = db.scalar(
                    select(PresentationVersion).where(
                        PresentationVersion.presentation_id == presentation_id,
                        PresentationVersion.version == base_version,
                    )
                )
                if existing is not None:
                    return CheckpointCreateResult("existing", checkpoint=existing, presentation=presentation)
                db.add(checkpoint)
                db.flush()
                return CheckpointCreateResult("created", checkpoint=checkpoint, presentation=presentation)
        except IntegrityError:
            # 并发创建同一版本时唯一约束决定赢家；输家只能读取同owner的既有记录。
            with self._session_factory() as db:
                existing = db.scalar(
                    select(PresentationVersion)
                    .join(Presentation, Presentation.id == PresentationVersion.presentation_id)
                    .where(
                        PresentationVersion.presentation_id == presentation_id,
                        PresentationVersion.version == base_version,
                        Presentation.owner_user_id == owner_user_id,
                        Presentation.deleted_at.is_(None),
                    )
                )
                if existing is not None:
                    return CheckpointCreateResult("existing", checkpoint=existing)
            raise

    def list_for_presentation(
        self, owner_user_id: int, presentation_id: str
    ) -> tuple[PresentationVersion, ...] | None:
        """先确认作品归属，再按版本倒序返回至多由服务层限制的检查点。"""
        with self._session_factory() as db:
            owned = db.scalar(
                select(Presentation.id).where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            )
            if owned is None:
                return None
            return tuple(
                db.scalars(
                    select(PresentationVersion)
                    .where(PresentationVersion.presentation_id == presentation_id)
                    .order_by(PresentationVersion.version.desc())
                ).all()
            )

    def restore(
        self,
        owner_user_id: int,
        presentation_id: str,
        target_version: int,
        *,
        base_version: int,
        slides_json: str,
        slide_count: int,
        restored_checkpoint: PresentationVersion,
        updated_at: datetime,
    ) -> "CheckpointRestoreResult":
        """恢复通过条件更新生成新版本，并在同一事务保留恢复结果检查点。"""
        with self._session_factory.begin() as db:
            target = db.scalar(
                select(PresentationVersion)
                .join(Presentation, Presentation.id == PresentationVersion.presentation_id)
                .where(
                    PresentationVersion.presentation_id == presentation_id,
                    PresentationVersion.version == target_version,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            )
            if target is None:
                return CheckpointRestoreResult("not_found")
            result = db.execute(
                update(Presentation)
                .where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                    Presentation.status.in_(("ready", "draft")),
                    Presentation.current_version == base_version,
                )
                .values(
                    slides_json=slides_json,
                    slide_count=slide_count,
                    current_version=base_version + 1,
                    updated_at=updated_at,
                )
            )
            if result.rowcount != 1:
                current = db.scalar(
                    select(Presentation).where(
                        Presentation.id == presentation_id,
                        Presentation.owner_user_id == owner_user_id,
                        Presentation.deleted_at.is_(None),
                    )
                )
                if current is None:
                    return CheckpointRestoreResult("not_found")
                state: Literal["conflict", "not_editable"] = (
                    "conflict" if current.status in {"ready", "draft"} else "not_editable"
                )
                return CheckpointRestoreResult(state, presentation=current)
            db.add(restored_checkpoint)
            db.flush()
            restored = db.scalar(
                select(Presentation).where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                )
            )
            return CheckpointRestoreResult("restored", presentation=restored)

    def prune_oldest(
        self, owner_user_id: int, presentation_id: str, *, keep_count: int
    ) -> int:
        """新检查点提交后再清理最旧历史；任何失败都不会回滚刚完成的恢复。"""
        with self._session_factory.begin() as db:
            owned = db.scalar(
                select(Presentation.id).where(
                    Presentation.id == presentation_id,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            )
            if owned is None:
                return 0
            stale_ids = list(
                db.scalars(
                    select(PresentationVersion.id)
                    .where(PresentationVersion.presentation_id == presentation_id)
                    .order_by(PresentationVersion.version.desc())
                    .offset(keep_count)
                ).all()
            )
            if not stale_ids:
                return 0
            result = db.execute(delete(PresentationVersion).where(PresentationVersion.id.in_(stale_ids)))
            return int(result.rowcount or 0)

    def get(self, owner_user_id: int, version_id: str) -> PresentationVersion | None:
        with self._session_factory() as db:
            return db.scalar(
                select(PresentationVersion)
                .join(Presentation, Presentation.id == PresentationVersion.presentation_id)
                .where(
                    PresentationVersion.id == version_id,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            )

    def get_by_number(
        self, owner_user_id: int, presentation_id: str, version: int
    ) -> PresentationVersion | None:
        with self._session_factory() as db:
            return db.scalar(
                select(PresentationVersion)
                .join(Presentation, Presentation.id == PresentationVersion.presentation_id)
                .where(
                    PresentationVersion.presentation_id == presentation_id,
                    PresentationVersion.version == version,
                    Presentation.owner_user_id == owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            )


@dataclass(frozen=True)
class CheckpointCreateResult:
    state: Literal["created", "existing", "not_found", "not_editable", "conflict"]
    checkpoint: PresentationVersion | None = None
    presentation: Presentation | None = None


@dataclass(frozen=True)
class CheckpointRestoreResult:
    state: Literal["restored", "not_found", "not_editable", "conflict"]
    presentation: Presentation | None = None


class GenerationTaskRepository(_OwnerRepository):
    model = GenerationTask


class BillingOperationRepository(_OwnerRepository):
    model = BillingOperation


class PresentationExportRepository(_OwnerRepository):
    model = PresentationExport


__all__ = [
    "BillingOperationRepository",
    "GenerationTaskRepository",
    "PresentationExportRepository",
    "PresentationRepository",
    "PresentationCreateResult",
    "PresentationLimitReached",
    "PresentationPage",
    "PresentationRequestConflict",
    "PresentationSchemaError",
    "PresentationSort",
    "PresentationVersionRepository",
    "CheckpointCreateResult",
    "CheckpointRestoreResult",
    "StoredFileRepository",
]

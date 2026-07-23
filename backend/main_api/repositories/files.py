"""T19 文件索引与用户占额仓储。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, func, inspect, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from ..models.domain import (
    OwnerStorageUsage, Presentation, PresentationExport, PresentationVersion, StoredFile,
)


class FileQuotaExceeded(RuntimeError):
    """用户级对象占额不足。"""


class FileOwnerNotFound(RuntimeError):
    """作品不存在或不属于当前owner。"""


class FileSchemaError(RuntimeError):
    """文件与占额迁移未完成。"""


@dataclass(frozen=True)
class FileReserveResult:
    file: StoredFile
    reused: bool
    ready: bool = True


class FileRepository:
    """在owner汇总行锁内检查并占用字节，上传中的对象也计入配额。"""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def ensure_schema(self) -> None:
        """存储开启时在监听前检查0006，禁止首个上传才暴露缺表。"""
        try:
            schema = inspect(self.engine)
            if not {"trainppt_files", "trainppt_owner_storage_usage"}.issubset(schema.get_table_names()):
                raise FileSchemaError("文件数据表迁移未完成")
            columns = {item["name"] for item in schema.get_columns("trainppt_owner_storage_usage")}
            if not {"owner_user_id", "used_bytes", "file_count", "updated_at"}.issubset(columns):
                raise FileSchemaError("文件数据表迁移未完成")
        except FileSchemaError:
            raise
        except Exception:
            raise FileSchemaError("文件数据表迁移检查失败") from None

    def reserve(
        self,
        file: StoredFile,
        *,
        user_storage_quota_bytes: int,
    ) -> FileReserveResult:
        with self._session_factory() as db:
            if db.scalar(
                select(Presentation.id).where(
                    Presentation.id == file.presentation_id,
                    Presentation.owner_user_id == file.owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            ) is None:
                raise FileOwnerNotFound
        self._ensure_usage_row(file.owner_user_id, file.created_at)
        try:
            with self._session_factory.begin() as db:
                presentation = db.scalar(
                select(Presentation.id).where(
                    Presentation.id == file.presentation_id,
                    Presentation.owner_user_id == file.owner_user_id,
                    Presentation.deleted_at.is_(None),
                )
            )
                if presentation is None:
                    raise FileOwnerNotFound
                existing = db.scalar(
                select(StoredFile).where(
                    StoredFile.owner_user_id == file.owner_user_id,
                    StoredFile.presentation_id == file.presentation_id,
                    StoredFile.purpose == file.purpose,
                    StoredFile.mime_type == file.mime_type,
                    StoredFile.size_bytes == file.size_bytes,
                    StoredFile.sha256 == file.sha256,
                    StoredFile.status == "active",
                    StoredFile.deleted_at.is_(None),
                )
            )
                if existing is not None:
                    # 复用也是一次使用租约：条件touch与GC的active→deleting认领互斥。
                    if self._touch_active(db, existing.id, file.created_at):
                        existing.updated_at = file.created_at
                        return FileReserveResult(existing, True)
                    # GC已赢得active→deleting时直接要求重试；禁止从identity map回读旧active。
                    return FileReserveResult(existing, True, ready=False)

                # 单条条件更新在SQLite和MySQL均可原子判定配额，不能依赖SQLite忽略的FOR UPDATE。
                reserved = db.execute(
                    update(OwnerStorageUsage)
                    .where(
                        OwnerStorageUsage.owner_user_id == file.owner_user_id,
                        OwnerStorageUsage.used_bytes
                        <= user_storage_quota_bytes - file.size_bytes,
                    )
                    .values(
                        used_bytes=OwnerStorageUsage.used_bytes + file.size_bytes,
                        file_count=OwnerStorageUsage.file_count + 1,
                        updated_at=file.created_at,
                    )
                )
                if reserved.rowcount != 1:
                    raise FileQuotaExceeded
                db.add(file)
                db.flush()
                return FileReserveResult(file, False)
        except IntegrityError:
            # 同内容并发时object_key唯一约束决定上传赢家；输家只观察现有状态，绝不重复写对象。
            with self._session_factory() as db:
                existing = db.scalar(
                    select(StoredFile).where(
                        StoredFile.owner_user_id == file.owner_user_id,
                        StoredFile.object_key == file.object_key,
                        StoredFile.deleted_at.is_(None),
                    )
                )
                if existing is None:
                    raise
                return FileReserveResult(existing, True)

    @staticmethod
    def _touch_active(db, file_id: str, now: datetime) -> bool:
        touched = db.execute(
            update(StoredFile)
            .where(StoredFile.id == file_id, StoredFile.status == "active")
            .values(updated_at=now)
        )
        return touched.rowcount == 1

    def _ensure_usage_row(self, owner_user_id: int, now: datetime) -> None:
        """首个并发上传使用方言upsert创建唯一owner汇总行，不依赖应用级先查后插。"""
        values = {
            "owner_user_id": owner_user_id,
            "used_bytes": 0,
            "file_count": 0,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            if self.engine.dialect.name == "sqlite":
                statement = sqlite_insert(OwnerStorageUsage).values(**values)
                connection.execute(statement.on_conflict_do_nothing(index_elements=["owner_user_id"]))
            elif self.engine.dialect.name == "mysql":
                statement = mysql_insert(OwnerStorageUsage).values(**values)
                connection.execute(
                    statement.on_duplicate_key_update(
                        owner_user_id=statement.inserted.owner_user_id
                    )
                )
            else:
                # 部署工厂只接受MySQL；此分支供明确的测试方言尽早失败。
                raise RuntimeError("unsupported storage database dialect")

    def activate(self, owner_user_id: int, file_id: str, now: datetime) -> StoredFile | None:
        with self._session_factory.begin() as db:
            file = db.scalar(
                select(StoredFile).where(
                    StoredFile.id == file_id,
                    StoredFile.owner_user_id == owner_user_id,
                    StoredFile.status == "uploading",
                    StoredFile.deleted_at.is_(None),
                ).with_for_update()
            )
            if file is None:
                return None
            file.status = "active"
            file.updated_at = now
            return file

    def fail_upload(self, owner_user_id: int, file_id: str, now: datetime) -> bool:
        """只有uploading可释放占额，重复补偿不会把汇总减成负数。"""
        with self._session_factory.begin() as db:
            file = db.scalar(
                select(StoredFile).where(
                    StoredFile.id == file_id,
                    StoredFile.owner_user_id == owner_user_id,
                    StoredFile.status.in_(("uploading", "recovering_upload")),
                ).with_for_update()
            )
            if file is None:
                return False
            usage = db.get(OwnerStorageUsage, owner_user_id, with_for_update=True)
            if usage is None:
                raise RuntimeError("storage usage missing")
            usage.used_bytes = max(usage.used_bytes - file.size_bytes, 0)
            usage.file_count = max(usage.file_count - 1, 0)
            usage.updated_at = now
            # 已尽力删除对象后移除未激活索引，使相同内容可安全重试；active记录永不走此分支。
            db.delete(file)
            return True

    def get_active(self, owner_user_id: int, file_id: str) -> StoredFile | None:
        with self._session_factory() as db:
            return db.scalar(
                select(StoredFile).where(
                    StoredFile.id == file_id,
                    StoredFile.owner_user_id == owner_user_id,
                    StoredFile.status == "active",
                    StoredFile.deleted_at.is_(None),
                )
            )

    def list_stale_uploads(self, stale_before: datetime, *, limit: int) -> tuple[StoredFile, ...]:
        """只返回未激活且已陈旧的索引，恢复器删除对象后再释放占额。"""
        with self._session_factory() as db:
            return tuple(db.scalars(
                select(StoredFile)
                .where(
                    StoredFile.status.in_(("uploading", "recovering_upload")),
                    StoredFile.updated_at <= stale_before,
                    StoredFile.deleted_at.is_(None),
                )
                .order_by(StoredFile.updated_at, StoredFile.id)
                .limit(limit)
            ))

    def claim_stale_upload(
        self, file_id: str, *, stale_before: datetime, now: datetime
    ) -> StoredFile | None:
        """原子围栏陈旧上传；认领后原上传者不能再activate。"""
        with self._session_factory.begin() as db:
            won = db.execute(
                update(StoredFile)
                .where(
                    StoredFile.id == file_id,
                    StoredFile.status.in_(("uploading", "recovering_upload")),
                    StoredFile.updated_at <= stale_before,
                )
                .values(status="recovering_upload", updated_at=now)
            )
            return db.get(StoredFile, file_id) if won.rowcount == 1 else None

    def list_checkpoint_cleanup_candidates(
        self, stale_before: datetime, *, limit: int
    ) -> tuple[StoredFile, ...]:
        with self._session_factory() as db:
            return tuple(db.scalars(
                select(StoredFile)
                .where(
                    StoredFile.purpose == "checkpoint",
                    StoredFile.status == "active",
                    StoredFile.updated_at <= stale_before,
                    StoredFile.deleted_at.is_(None),
                )
                .order_by(StoredFile.updated_at, StoredFile.id)
                .limit(limit)
            ))

    def claim_unreferenced_checkpoint(
        self, file_id: str, *, stale_before: datetime, now: datetime
    ) -> StoredFile | None:
        """租约到期且没有版本信封引用时才转deleting，避免清理正在提交的检查点。"""
        with self._session_factory.begin() as db:
            file = db.scalar(
                select(StoredFile).where(
                    StoredFile.id == file_id,
                    StoredFile.purpose == "checkpoint",
                    StoredFile.status == "active",
                    StoredFile.updated_at <= stale_before,
                ).with_for_update()
            )
            if file is None:
                return None
            reference = db.scalar(
                select(PresentationVersion.id).where(
                    PresentationVersion.presentation_id == file.presentation_id,
                    PresentationVersion.slides_json.contains(f'"file_id":"{file.id}"'),
                ).limit(1)
            )
            if reference is not None:
                return None
            won = db.execute(
                update(StoredFile)
                .where(
                    StoredFile.id == file.id,
                    StoredFile.status == "active",
                    StoredFile.updated_at <= stale_before,
                )
                .values(status="deleting", updated_at=now)
            )
            return db.get(StoredFile, file.id) if won.rowcount == 1 else None

    def restore_deleting(self, owner_user_id: int, file_id: str, now: datetime) -> bool:
        with self._session_factory.begin() as db:
            file = db.scalar(select(StoredFile).where(
                StoredFile.id == file_id,
                StoredFile.owner_user_id == owner_user_id,
                StoredFile.status == "deleting",
            ).with_for_update())
            if file is None:
                return False
            file.status = "active"
            file.updated_at = now
            return True

    def claim_unreferenced_file(
        self, owner_user_id: int, file_id: str, purpose: str, now: datetime
    ) -> StoredFile | None:
        """归档提交失败或缩略图换代后，只有无业务引用的active文件可进入删除态。"""
        with self._session_factory.begin() as db:
            file = db.scalar(select(StoredFile).where(
                StoredFile.id == file_id,
                StoredFile.owner_user_id == owner_user_id,
                StoredFile.purpose == purpose,
                StoredFile.status == "active",
                StoredFile.deleted_at.is_(None),
            ).with_for_update())
            if file is None or self._has_reference(db, file):
                return None
            won = db.execute(update(StoredFile).where(
                StoredFile.id == file.id, StoredFile.status == "active",
            ).values(status="deleting", updated_at=now))
            return db.get(StoredFile, file.id) if won.rowcount == 1 else None

    def complete_delete(self, owner_user_id: int, file_id: str, now: datetime) -> bool:
        return self._release_and_delete(owner_user_id, file_id, "deleting", now)

    def list_stale_deletions(
        self, stale_before: datetime, *, limit: int
    ) -> tuple[StoredFile, ...]:
        with self._session_factory() as db:
            return tuple(db.scalars(
                select(StoredFile)
                .where(
                    StoredFile.status == "deleting",
                    StoredFile.updated_at <= stale_before,
                )
                .order_by(StoredFile.updated_at, StoredFile.id)
                .limit(limit)
            ))

    def recover_deletion(
        self, file_id: str, *, stale_before: datetime, now: datetime
    ) -> StoredFile | None:
        """删除中崩溃可重放；若期间出现版本引用则恢复active而不碰对象。"""
        with self._session_factory.begin() as db:
            file = db.scalar(select(StoredFile).where(
                StoredFile.id == file_id,
                StoredFile.status == "deleting",
                StoredFile.updated_at <= stale_before,
            ).with_for_update())
            if file is None:
                return None
            if self._has_reference(db, file):
                file.status = "active"
                file.updated_at = now
                return None
            file.updated_at = now
            return file

    @staticmethod
    def _has_reference(db, file: StoredFile) -> bool:
        """按用途检查强引用；删除恢复与主动清理共享同一安全判定。"""
        if file.purpose == "checkpoint":
            return db.scalar(select(PresentationVersion.id).where(
                PresentationVersion.presentation_id == file.presentation_id,
                PresentationVersion.slides_json.contains(f'"file_id":"{file.id}"'),
            ).limit(1)) is not None
        if file.purpose == "pptx":
            return db.scalar(select(PresentationExport.id).where(
                PresentationExport.file_id == file.id,
            ).limit(1)) is not None
        if file.purpose == "thumbnail":
            return db.scalar(select(Presentation.id).where(
                Presentation.thumbnail_file_id == file.id,
            ).limit(1)) is not None
        # source/attachment尚无独立引用表，禁止通用回收器误删。
        return True

    def used_bytes(self, owner_user_id: int) -> int:
        with self._session_factory() as db:
            value = db.scalar(
                select(OwnerStorageUsage.used_bytes).where(
                    OwnerStorageUsage.owner_user_id == owner_user_id
                )
            )
            return int(value or 0)

    def active_count(self, owner_user_id: int) -> int:
        with self._session_factory() as db:
            return int(db.scalar(
                select(func.count(StoredFile.id)).where(
                    StoredFile.owner_user_id == owner_user_id,
                    StoredFile.status == "active",
                    StoredFile.deleted_at.is_(None),
                )
            ) or 0)

    def _release_and_delete(
        self, owner_user_id: int, file_id: str, expected_status: str, now: datetime
    ) -> bool:
        with self._session_factory.begin() as db:
            file = db.scalar(select(StoredFile).where(
                StoredFile.id == file_id,
                StoredFile.owner_user_id == owner_user_id,
                StoredFile.status == expected_status,
            ).with_for_update())
            if file is None:
                return False
            usage = db.get(OwnerStorageUsage, owner_user_id, with_for_update=True)
            if usage is None:
                raise RuntimeError("storage usage missing")
            usage.used_bytes = max(usage.used_bytes - file.size_bytes, 0)
            usage.file_count = max(usage.file_count - 1, 0)
            usage.updated_at = now
            db.delete(file)
            return True


__all__ = [
    "FileOwnerNotFound",
    "FileQuotaExceeded",
    "FileRepository",
    "FileReserveResult",
    "FileSchemaError",
]

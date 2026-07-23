"""T06 核心业务持久化模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


# 编辑稿和检查点可能超过 MySQL TEXT 的 64 KiB 上限；测试方言仍使用通用 Text。
LONG_TEXT = Text().with_variant(mysql.LONGTEXT(), "mysql")


class Presentation(Base):
    """作品当前编辑稿；任何读取都必须经 owner 作用域仓储。"""

    __tablename__ = "trainppt_presentations"
    __table_args__ = (
        Index("ix_presentations_owner_deleted_updated", "owner_user_id", "deleted_at", "updated_at"),
        Index("ix_presentations_owner_status_updated", "owner_user_id", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    slides_json: Mapped[str] = mapped_column(LONG_TEXT, nullable=False)
    current_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1, server_default="1")
    slide_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    thumbnail_file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class PresentationVersion(Base):
    """不可覆盖的作品检查点，版本号在单个作品内唯一。"""

    __tablename__ = "trainppt_presentation_versions"
    __table_args__ = (
        UniqueConstraint("presentation_id", "version", name="uq_presentation_versions_presentation_version"),
        Index("ix_presentation_versions_presentation_created", "presentation_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    presentation_id: Mapped[str] = mapped_column(
        ForeignKey("trainppt_presentations.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    slides_json: Mapped[str] = mapped_column(LONG_TEXT, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class GenerationTask(Base):
    """可持久恢复的生成任务；lock_token 是防止旧 Worker 提交终态的围栏。"""

    __tablename__ = "trainppt_generation_tasks"
    __table_args__ = (
        # 客户端幂等键只在当前用户作用域内唯一，避免不同用户采用相同随机值时互相冲突。
        UniqueConstraint(
            "owner_user_id", "request_id", name="uq_generation_tasks_owner_request"
        ),
        Index("ix_generation_tasks_owner_created", "owner_user_id", "created_at"),
        Index("ix_generation_tasks_claim", "status", "next_attempt_at", "locked_until", "created_at"),
        Index("ix_generation_tasks_recovery", "status", "locked_until", "dispatch_started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    presentation_id: Mapped[str] = mapped_column(
        ForeignKey("trainppt_presentations.id", ondelete="RESTRICT"), nullable=False
    )
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    input_json: Mapped[str] = mapped_column(LONG_TEXT, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lock_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    dispatch_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class BillingOperation(Base):
    """计费动作审计表；三个动作各用独立唯一幂等键。"""

    __tablename__ = "trainppt_billing_operations"
    __table_args__ = (
        UniqueConstraint("reserve_key", name="uq_billing_operations_reserve_key"),
        UniqueConstraint("settle_key", name="uq_billing_operations_settle_key"),
        UniqueConstraint("release_key", name="uq_billing_operations_release_key"),
        Index("ix_billing_operations_owner_created", "owner_user_id", "created_at"),
        Index("ix_billing_operations_task", "task_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("trainppt_generation_tasks.id", ondelete="RESTRICT"), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    entitlement_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hold_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reserved_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    actual_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reserve_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    settle_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    release_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class StoredFile(Base):
    """对象存储索引；object_key 只能由服务端生成。"""

    __tablename__ = "trainppt_files"
    __table_args__ = (
        UniqueConstraint("object_key", name="uq_files_object_key"),
        Index("ix_files_owner_created", "owner_user_id", "created_at"),
        Index("ix_files_presentation_purpose", "presentation_id", "purpose", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    presentation_id: Mapped[str] = mapped_column(
        ForeignKey("trainppt_presentations.id", ondelete="RESTRICT"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    # 512 个字符在 utf8mb4 下仍可安全建立唯一索引，且足以容纳服务端命名空间。
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class OwnerStorageUsage(Base):
    """用户级对象占额汇总；按owner主键加锁，避免并发上传各自通过配额检查。"""

    __tablename__ = "trainppt_owner_storage_usage"

    owner_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    used_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    file_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class PresentationExport(Base):
    """作品某版本的导出记录，通过 owner 字段避免只凭文件 ID 越权。"""

    __tablename__ = "trainppt_exports"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "request_id", name="uq_exports_owner_request"),
        Index("ix_exports_owner_created", "owner_user_id", "created_at"),
        Index("ix_exports_presentation_version", "presentation_id", "presentation_version", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 浏览器重试必须复用同一业务键；唯一约束是并发幂等的最终裁决者。
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    presentation_id: Mapped[str] = mapped_column(
        ForeignKey("trainppt_presentations.id", ondelete="RESTRICT"), nullable=False
    )
    presentation_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_id: Mapped[str] = mapped_column(ForeignKey("trainppt_files.id", ondelete="RESTRICT"), nullable=False)
    export_format: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


__all__ = [
    "BillingOperation",
    "GenerationTask",
    "OwnerStorageUsage",
    "Presentation",
    "PresentationExport",
    "PresentationVersion",
    "StoredFile",
]

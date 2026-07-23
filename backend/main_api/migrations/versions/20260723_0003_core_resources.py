"""创建 T06 核心资源、所有权索引和任务租约表。

Revision ID: 20260723_0003
Revises: 20260723_0002
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql


revision: str = "20260723_0003"
down_revision: str | None = "20260723_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# MySQL 使用 LONGTEXT 保存完整编辑稿，SQLite 隔离迁移测试仍可编译为通用 Text。
LONG_TEXT = sa.Text().with_variant(mysql.LONGTEXT(), "mysql")


def upgrade() -> None:
    """只向前新增业务结构，不迁移、覆盖或删除任何既有用户数据。"""
    op.create_table(
        "trainppt_presentations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("slides_json", LONG_TEXT, nullable=False),
        sa.Column("current_version", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column("slide_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("template_id", sa.String(length=64), nullable=True),
        sa.Column("thumbnail_file_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_presentations"),
    )
    op.create_index(
        "ix_presentations_owner_deleted_updated",
        "trainppt_presentations",
        ["owner_user_id", "deleted_at", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_presentations_owner_status_updated",
        "trainppt_presentations",
        ["owner_user_id", "status", "updated_at"],
        unique=False,
    )

    op.create_table(
        "trainppt_presentation_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("presentation_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("slides_json", LONG_TEXT, nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["presentation_id"], ["trainppt_presentations.id"], name="fk_versions_presentation", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_presentation_versions"),
        sa.UniqueConstraint("presentation_id", "version", name="uq_presentation_versions_presentation_version"),
    )
    op.create_index(
        "ix_presentation_versions_presentation_created",
        "trainppt_presentation_versions",
        ["presentation_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "trainppt_generation_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("presentation_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("input_json", LONG_TEXT, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("attempt", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("lock_token", sa.String(length=64), nullable=True),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["presentation_id"], ["trainppt_presentations.id"], name="fk_tasks_presentation", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_generation_tasks"),
        sa.UniqueConstraint("request_id", name="uq_generation_tasks_request_id"),
    )
    op.create_index("ix_generation_tasks_owner_created", "trainppt_generation_tasks", ["owner_user_id", "created_at"], unique=False)
    op.create_index(
        "ix_generation_tasks_claim",
        "trainppt_generation_tasks",
        ["status", "next_attempt_at", "locked_until", "created_at"],
        unique=False,
    )

    op.create_table(
        "trainppt_billing_operations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("entitlement_id", sa.String(length=128), nullable=True),
        sa.Column("hold_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reserved_amount", sa.BigInteger(), nullable=True),
        sa.Column("actual_amount", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reserve_key", sa.String(length=128), nullable=True),
        sa.Column("settle_key", sa.String(length=128), nullable=True),
        sa.Column("release_key", sa.String(length=128), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["trainppt_generation_tasks.id"], name="fk_billing_task", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_billing_operations"),
        sa.UniqueConstraint("reserve_key", name="uq_billing_operations_reserve_key"),
        sa.UniqueConstraint("settle_key", name="uq_billing_operations_settle_key"),
        sa.UniqueConstraint("release_key", name="uq_billing_operations_release_key"),
    )
    op.create_index("ix_billing_operations_owner_created", "trainppt_billing_operations", ["owner_user_id", "created_at"], unique=False)
    op.create_index("ix_billing_operations_task", "trainppt_billing_operations", ["task_id"], unique=False)

    op.create_table(
        "trainppt_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("presentation_id", sa.String(length=36), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["presentation_id"], ["trainppt_presentations.id"], name="fk_files_presentation", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_files"),
        sa.UniqueConstraint("object_key", name="uq_files_object_key"),
    )
    op.create_index("ix_files_owner_created", "trainppt_files", ["owner_user_id", "created_at"], unique=False)
    op.create_index("ix_files_presentation_purpose", "trainppt_files", ["presentation_id", "purpose", "created_at"], unique=False)

    op.create_table(
        "trainppt_exports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("presentation_id", sa.String(length=36), nullable=False),
        sa.Column("presentation_version", sa.BigInteger(), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("export_format", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["trainppt_files.id"], name="fk_exports_file", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["presentation_id"], ["trainppt_presentations.id"], name="fk_exports_presentation", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_exports"),
    )
    op.create_index("ix_exports_owner_created", "trainppt_exports", ["owner_user_id", "created_at"], unique=False)
    op.create_index(
        "ix_exports_presentation_version",
        "trainppt_exports",
        ["presentation_id", "presentation_version", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """仅供隔离测试回退；生产应用回滚不得自动执行破坏性降级。"""
    op.drop_index("ix_exports_presentation_version", table_name="trainppt_exports")
    op.drop_index("ix_exports_owner_created", table_name="trainppt_exports")
    op.drop_table("trainppt_exports")
    op.drop_index("ix_files_presentation_purpose", table_name="trainppt_files")
    op.drop_index("ix_files_owner_created", table_name="trainppt_files")
    op.drop_table("trainppt_files")
    op.drop_index("ix_billing_operations_task", table_name="trainppt_billing_operations")
    op.drop_index("ix_billing_operations_owner_created", table_name="trainppt_billing_operations")
    op.drop_table("trainppt_billing_operations")
    op.drop_index("ix_generation_tasks_claim", table_name="trainppt_generation_tasks")
    op.drop_index("ix_generation_tasks_owner_created", table_name="trainppt_generation_tasks")
    op.drop_table("trainppt_generation_tasks")
    op.drop_index("ix_presentation_versions_presentation_created", table_name="trainppt_presentation_versions")
    op.drop_table("trainppt_presentation_versions")
    op.drop_index("ix_presentations_owner_status_updated", table_name="trainppt_presentations")
    op.drop_index("ix_presentations_owner_deleted_updated", table_name="trainppt_presentations")
    op.drop_table("trainppt_presentations")

"""增加 T08 Agent派发崩溃恢复标记和扫描索引。

Revision ID: 20260723_0004
Revises: 20260723_0003
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260723_0004"
down_revision: str | None = "20260723_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """只新增可空派发标记，现有任务保持可迁移且不会被自动执行。"""
    op.add_column("trainppt_generation_tasks", sa.Column("dispatch_started_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_generation_tasks_recovery",
        "trainppt_generation_tasks",
        ["status", "locked_until", "dispatch_started_at"],
        unique=False,
    )


def downgrade() -> None:
    """仅供隔离测试；生产应用回滚不得自动删除恢复证据。"""
    op.drop_index("ix_generation_tasks_recovery", table_name="trainppt_generation_tasks")
    op.drop_column("trainppt_generation_tasks", "dispatch_started_at")

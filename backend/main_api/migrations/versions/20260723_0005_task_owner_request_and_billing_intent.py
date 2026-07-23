"""T16 将生成任务幂等键限定到用户作用域。

Revision ID: 20260723_0005
Revises: 20260723_0004
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260723_0005"
down_revision: str | None = "20260723_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """同一用户内保持唯一，不同用户可安全复用相同客户端请求值。"""
    # batch 模式同时兼容 SQLite 测试库和生产 MySQL，重建期间不改动业务数据。
    with op.batch_alter_table("trainppt_generation_tasks") as batch_op:
        batch_op.drop_constraint("uq_generation_tasks_request_id", type_="unique")
        batch_op.create_unique_constraint(
            "uq_generation_tasks_owner_request", ["owner_user_id", "request_id"]
        )


def downgrade() -> None:
    """仅供隔离测试；若不同用户已复用请求值，生产环境不得直接降级。"""
    with op.batch_alter_table("trainppt_generation_tasks") as batch_op:
        batch_op.drop_constraint("uq_generation_tasks_owner_request", type_="unique")
        batch_op.create_unique_constraint(
            "uq_generation_tasks_request_id", ["request_id"]
        )

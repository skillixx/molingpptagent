"""T20 为导出记录增加owner作用域幂等键。

Revision ID: 20260723_0007
Revises: 20260723_0006
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260723_0007"
down_revision: str | None = "20260723_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """既有未开放记录以自身ID回填，随后冻结owner内唯一约束。"""
    op.add_column("trainppt_exports", sa.Column("request_id", sa.String(128), nullable=True))
    op.execute(sa.text("UPDATE trainppt_exports SET request_id = id WHERE request_id IS NULL"))
    # batch模式兼容SQLite验收库，同时在MySQL生成常规ALTER TABLE。
    with op.batch_alter_table("trainppt_exports") as batch:
        batch.alter_column("request_id", existing_type=sa.String(128), nullable=False)
        batch.create_unique_constraint(
            "uq_exports_owner_request", ["owner_user_id", "request_id"]
        )


def downgrade() -> None:
    """仅供隔离环境回退；生产应保留导出幂等审计。"""
    with op.batch_alter_table("trainppt_exports") as batch:
        batch.drop_constraint("uq_exports_owner_request", type_="unique")
        batch.drop_column("request_id")

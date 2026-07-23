"""创建墨灵应用Session表。

Revision ID: 20260723_0002
Revises: 20260723_0001
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260723_0002"
down_revision: str | None = "20260723_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """只新增Session表；浏览器原始Cookie不得出现在任何列。"""
    op.create_table(
        "app_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("app_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_app_sessions"),
    )
    op.create_index("ix_app_sessions_user_id", "app_sessions", ["user_id"], unique=False)
    op.create_index("ix_app_sessions_expires_at", "app_sessions", ["expires_at"], unique=False)


def downgrade() -> None:
    """仅供隔离测试库回退；生产应用回滚禁止执行破坏性降级。"""
    op.drop_index("ix_app_sessions_expires_at", table_name="app_sessions")
    op.drop_index("ix_app_sessions_user_id", table_name="app_sessions")
    op.drop_table("app_sessions")

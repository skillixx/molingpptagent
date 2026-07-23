"""T19 增加用户对象存储占额汇总。

Revision ID: 20260723_0006
Revises: 20260723_0005
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260723_0006"
down_revision: str | None = "20260723_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """汇总行以owner为锁粒度；既有文件回填后才能开放生产写入。"""
    op.create_table(
        "trainppt_owner_storage_usage",
        sa.Column("owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("used_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("file_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("owner_user_id", name="pk_owner_storage_usage"),
    )
    # 当前生产功能尚未开放；仍按既有files数据回填，避免预置数据绕过配额。
    op.execute(sa.text("""
        INSERT INTO trainppt_owner_storage_usage (owner_user_id, used_bytes, file_count, updated_at)
        SELECT owner_user_id, COALESCE(SUM(size_bytes), 0), COUNT(*), CURRENT_TIMESTAMP
        FROM trainppt_files
        WHERE status IN ('uploading', 'active') AND deleted_at IS NULL
        GROUP BY owner_user_id
    """))


def downgrade() -> None:
    """仅供隔离测试；生产回滚保留汇总表，禁止丢失配额审计依据。"""
    op.drop_table("trainppt_owner_storage_usage")

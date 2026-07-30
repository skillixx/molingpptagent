"""把墨灵票据指定权益贯穿 Session，并统一计费数值标识。

Revision ID: 20260730_0008
Revises: 20260723_0007
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op


revision: str = "20260730_0008"
down_revision: str | None = "20260723_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MAX_SIGNED_BIGINT = 9_223_372_036_854_775_807


def _validate_numeric_billing_ids() -> None:
    """迁移前拒绝不可追溯的旧字符串，禁止静默转零或截断。"""
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT entitlement_id, hold_id FROM trainppt_billing_operations "
            "WHERE entitlement_id IS NOT NULL OR hold_id IS NOT NULL"
        )
    )
    invalid_count = 0
    for entitlement_id, hold_id in rows:
        for value in (entitlement_id, hold_id):
            if value is None:
                continue
            raw = str(value)
            if not raw.isascii() or not raw.isdigit():
                invalid_count += 1
                continue
            parsed = int(raw)
            if parsed <= 0 or parsed > _MAX_SIGNED_BIGINT:
                invalid_count += 1
    if invalid_count:
        # 只报告数量，不把任务、权益或持有单明细写入部署日志。
        raise RuntimeError(f"计费标识迁移发现 {invalid_count} 个非法历史值")


def upgrade() -> None:
    """先验证旧值，再把会话选择和平台数值标识写入强类型列。"""
    if not context.is_offline_mode():
        _validate_numeric_billing_ids()

    with op.batch_alter_table("app_sessions") as batch_op:
        batch_op.add_column(sa.Column("entitlement_id", sa.BigInteger(), nullable=True))

    with op.batch_alter_table("trainppt_billing_operations") as batch_op:
        batch_op.alter_column(
            "entitlement_id",
            existing_type=sa.String(length=128),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "hold_id",
            existing_type=sa.String(length=128),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )


def downgrade() -> None:
    """仅供隔离测试回退；生产降级前必须先确认没有新会话和活动持有单。"""
    with op.batch_alter_table("trainppt_billing_operations") as batch_op:
        batch_op.alter_column(
            "hold_id",
            existing_type=sa.BigInteger(),
            type_=sa.String(length=128),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "entitlement_id",
            existing_type=sa.BigInteger(),
            type_=sa.String(length=128),
            existing_nullable=True,
        )

    with op.batch_alter_table("app_sessions") as batch_op:
        batch_op.drop_column("entitlement_id")

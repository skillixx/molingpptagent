"""建立 TrainPPTAgent 业务数据库的空迁移基线。"""

from typing import Sequence


revision: str = "20260723_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """T02 只建立版本基线，T06 才新增核心业务表。"""
    pass


def downgrade() -> None:
    """空基线不删除任何业务对象，保证应用回滚保留数据。"""
    pass

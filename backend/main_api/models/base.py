"""所有TrainPPTAgent ORM模型共享的声明基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """统一元数据，供迁移与测试创建隔离表结构。"""

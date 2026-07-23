"""T06 核心业务表、所有权隔离与任务租约的公开行为测试。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.main_api.models.base import Base
from backend.main_api.models.domain import GenerationTask, Presentation, PresentationVersion, StoredFile
from backend.main_api.repositories.resources import (
    GenerationTaskRepository,
    PresentationRepository,
    PresentationVersionRepository,
    StoredFileRepository,
)
from backend.main_api.repositories.tasks import TaskLease, TaskLeaseRepository, claim_candidate_statement


NOW = datetime(2026, 7, 23, 2, 45, 0)


@pytest.fixture()
def engine(tmp_path: Path):
    """文件型 SQLite 允许多个独立连接验证真实事务竞争。"""
    database = tmp_path / "t06.db"
    value = create_engine(
        f"sqlite:///{database.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    Base.metadata.create_all(value)
    try:
        yield value
    finally:
        value.dispose()


def _presentation(identifier: str, owner: int) -> Presentation:
    return Presentation(
        id=identifier,
        owner_user_id=owner,
        title=f"作品-{identifier}",
        status="draft",
        slides_json="{}",
        current_version=1,
        slide_count=0,
        created_at=NOW,
        updated_at=NOW,
    )


def test_owner_scoped_repository_hides_foreign_and_soft_deleted_resources(engine) -> None:
    """他人资源、已删除资源和不存在资源必须呈现相同的未找到结果。"""
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(_presentation("p-owner", 1001))
        db.add(
            StoredFile(
                id="f-owner",
                owner_user_id=1001,
                presentation_id="p-owner",
                purpose="thumbnail",
                object_key="users/1001/presentations/p-owner/thumbnails/f-owner.png",
                mime_type="image/png",
                size_bytes=12,
                sha256="a" * 64,
                status="ready",
                created_at=NOW,
                updated_at=NOW,
            )
        )

    presentations = PresentationRepository(engine)
    files = StoredFileRepository(engine)
    assert presentations.get(1001, "p-owner") is not None
    assert presentations.get(2002, "p-owner") is None
    assert files.get(1001, "f-owner") is not None
    assert files.get(2002, "f-owner") is None

    assert presentations.soft_delete(2002, "p-owner", deleted_at=NOW) is False
    assert presentations.soft_delete(1001, "p-owner", deleted_at=NOW) is True
    assert presentations.soft_delete(1001, "p-owner", deleted_at=NOW) is True
    assert presentations.get(1001, "p-owner") is None


def test_task_and_version_repositories_apply_owner_scope(engine) -> None:
    """任务直接校验 owner，版本必须经未删除作品间接校验 owner。"""
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(_presentation("p-scoped", 1001))
        db.add(
            PresentationVersion(
                id="v-scoped",
                presentation_id="p-scoped",
                version=1,
                slides_json="{}",
                reason="manual",
                created_by=1001,
                created_at=NOW,
            )
        )
        db.add(
            GenerationTask(
                id="t-scoped",
                presentation_id="p-scoped",
                owner_user_id=1001,
                request_id="request-scoped",
                status="pending",
                stage="queued",
                progress=0,
                input_json="{}",
                retryable=True,
                attempt=0,
                max_attempts=3,
                next_attempt_at=NOW,
                created_at=NOW,
                updated_at=NOW,
            )
        )

    tasks = GenerationTaskRepository(engine)
    versions = PresentationVersionRepository(engine)
    assert tasks.get(1001, "t-scoped") is not None
    assert tasks.get(2002, "t-scoped") is None
    assert versions.get(1001, "v-scoped") is not None
    assert versions.get(2002, "v-scoped") is None


def test_request_id_and_presentation_version_are_database_unique(engine) -> None:
    """业务请求和作品检查点必须由数据库约束兜住并发幂等。"""
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(_presentation("p-unique", 1001))
        db.add(
            PresentationVersion(
                id="v-1",
                presentation_id="p-unique",
                version=1,
                slides_json="{}",
                reason="manual",
                created_by=1001,
                created_at=NOW,
            )
        )
        db.add(
            GenerationTask(
                id="t-1",
                presentation_id="p-unique",
                owner_user_id=1001,
                request_id="request-unique",
                status="pending",
                stage="queued",
                progress=0,
                input_json="{}",
                retryable=True,
                attempt=0,
                max_attempts=3,
                next_attempt_at=NOW,
                created_at=NOW,
                updated_at=NOW,
            )
        )

    with pytest.raises(IntegrityError):
        with factory.begin() as db:
            db.add(
                GenerationTask(
                    id="t-2",
                    presentation_id="p-unique",
                    owner_user_id=1001,
                    request_id="request-unique",
                    status="pending",
                    stage="queued",
                    progress=0,
                    input_json="{}",
                    retryable=True,
                    attempt=0,
                    max_attempts=3,
                    next_attempt_at=NOW,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )

    with pytest.raises(IntegrityError):
        with factory.begin() as db:
            db.add(
                PresentationVersion(
                    id="v-duplicate",
                    presentation_id="p-unique",
                    version=1,
                    slides_json="{}",
                    reason="manual",
                    created_by=1001,
                    created_at=NOW,
                )
            )


def test_two_transactions_only_one_can_claim_the_same_task(engine) -> None:
    """两个 Worker 同时竞争时只允许一个随机租约令牌成为有效围栏。"""
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(_presentation("p-claim", 1001))
        db.add(
            GenerationTask(
                id="t-claim",
                presentation_id="p-claim",
                owner_user_id=1001,
                request_id="request-claim",
                status="pending",
                stage="queued",
                progress=0,
                input_json="{}",
                retryable=True,
                attempt=0,
                max_attempts=3,
                next_attempt_at=NOW,
                created_at=NOW,
                updated_at=NOW,
            )
        )

    repository = TaskLeaseRepository(engine)
    with ThreadPoolExecutor(max_workers=2) as pool:
        leases = list(
            pool.map(
                lambda worker: repository.claim_next(
                    worker,
                    now=NOW,
                    locked_until=NOW + timedelta(seconds=120),
                ),
                ("worker-a", "worker-b"),
            )
        )

    winners = [lease for lease in leases if lease is not None]
    assert len(winners) == 1
    winner = winners[0]
    assert winner.task_id == "t-claim"
    assert winner.lock_token

    # 错误令牌不能续租或提交终态；持有者的令牌才是数据库写入围栏。
    assert repository.renew("t-claim", "stale-token", NOW + timedelta(seconds=240), NOW) is False
    assert repository.complete("t-claim", "stale-token", NOW) is False
    assert repository.renew("t-claim", winner.lock_token, NOW + timedelta(seconds=240), NOW) is True
    assert repository.complete("t-claim", winner.lock_token, NOW) is True


def test_failed_terminal_write_also_requires_current_fence(engine) -> None:
    """Agent 失败返回也不能由已丢失租约的旧 Worker 写入。"""
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(_presentation("p-fail", 1001))
        db.add(
            GenerationTask(
                id="t-fail",
                presentation_id="p-fail",
                owner_user_id=1001,
                request_id="request-fail",
                status="pending",
                stage="queued",
                progress=0,
                input_json="{}",
                retryable=True,
                attempt=0,
                max_attempts=3,
                next_attempt_at=NOW,
                created_at=NOW,
                updated_at=NOW,
            )
        )

    repository = TaskLeaseRepository(engine)
    lease = repository.claim_next("worker", now=NOW, locked_until=NOW + timedelta(seconds=120))
    assert lease is not None
    assert repository.fail(
        "t-fail",
        "stale-token",
        NOW,
        error_code="AGENT_FAILED",
        error_message="已脱敏失败",
        retryable=True,
    ) is False
    assert repository.fail(
        "t-fail",
        lease.lock_token,
        NOW,
        error_code="AGENT_FAILED",
        error_message="已脱敏失败",
        retryable=True,
    ) is True


def test_pending_task_with_unexpired_lock_is_not_claimable(engine) -> None:
    """异常状态下仍存在有效租期时不得覆盖令牌，过期回收逻辑留给 T08。"""
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(_presentation("p-locked", 1001))
        db.add(
            GenerationTask(
                id="t-locked",
                presentation_id="p-locked",
                owner_user_id=1001,
                request_id="request-locked",
                status="pending",
                stage="queued",
                progress=0,
                input_json="{}",
                retryable=True,
                attempt=0,
                max_attempts=3,
                next_attempt_at=NOW,
                locked_by="existing-worker",
                lock_token="existing-token",
                locked_until=NOW + timedelta(seconds=30),
                created_at=NOW,
                updated_at=NOW,
            )
        )

    assert TaskLeaseRepository(engine).claim_next(
        "new-worker", now=NOW, locked_until=NOW + timedelta(seconds=120)
    ) is None


def test_core_schema_contains_required_indexes_and_lease_columns(engine) -> None:
    """迁移模型必须显式提供 owner、幂等与租约扫描所需结构。"""
    schema = inspect(engine)
    assert {
        "trainppt_presentations",
        "trainppt_presentation_versions",
        "trainppt_generation_tasks",
        "trainppt_billing_operations",
        "trainppt_files",
        "trainppt_exports",
    }.issubset(schema.get_table_names())

    task_columns = {column["name"] for column in schema.get_columns("trainppt_generation_tasks")}
    assert {
        "status",
        "attempt",
        "next_attempt_at",
        "locked_by",
        "lock_token",
        "locked_until",
        "heartbeat_at",
        "dispatch_started_at",
        "last_error_code",
    }.issubset(task_columns)

    presentation_indexes = {index["name"] for index in schema.get_indexes("trainppt_presentations")}
    assert "ix_presentations_owner_deleted_updated" in presentation_indexes
    assert "ix_presentations_owner_status_updated" in presentation_indexes
    task_indexes = {index["name"] for index in schema.get_indexes("trainppt_generation_tasks")}
    assert "ix_generation_tasks_claim" in task_indexes
    assert "ix_generation_tasks_recovery" in task_indexes


def test_mysql_claim_statement_uses_skip_locked_without_exposing_tokens() -> None:
    """MySQL 8 候选查询必须跳过已锁行，租约对象表示也不得泄漏围栏令牌。"""
    sql = str(
        claim_candidate_statement(NOW, skip_locked=True).compile(
            dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).upper()
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "secret-fence" not in repr(TaskLease("task", "worker", "secret-fence"))

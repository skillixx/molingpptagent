"""T08 持久化任务执行器：租约、心跳、崩溃恢复与有限重试。"""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Protocol

from ..repositories.tasks import TaskLeaseRepository, TaskRecord


@dataclass(frozen=True)
class TaskExecution:
    """传给业务处理器的只读任务；request_id 在全部重试中保持稳定。"""

    task_id: str
    presentation_id: str
    owner_user_id: int
    request_id: str
    input: dict[str, Any]
    attempt: int
    max_attempts: int
    # 仅由实际 Worker 执行携带；对账器只读探测历史产物时不需要租约令牌。
    lock_token: str | None = None


class TaskHandler(Protocol):
    """T09 业务适配器契约；产物探测必须只读且可重复。"""

    async def execute(self, task: TaskExecution) -> None: ...

    async def has_persisted_result(self, task: TaskExecution) -> bool: ...


class RetryableTaskError(Exception):
    """明确可重试错误；调用者只可提供脱敏后的稳定错误信息。"""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class NonRetryableTaskError(Exception):
    """明确不可重试错误，例如输入无效或权限已撤销。"""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class PersistentTaskWorker:
    """一次领取一个任务的持久化 Worker，可由独立进程循环调用。"""

    def __init__(
        self,
        *,
        repository: TaskLeaseRepository,
        handler: TaskHandler,
        worker_id: str,
        lease_seconds: float,
        heartbeat_seconds: float,
        retry_backoff_seconds: float,
        claim_batch_size: int,
        agent_timeout_seconds: float,
        clock: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        if lease_seconds <= 0 or heartbeat_seconds <= 0:
            raise ValueError("租约和心跳间隔必须大于零")
        if heartbeat_seconds >= lease_seconds:
            raise ValueError("心跳间隔必须小于租约时长")
        if retry_backoff_seconds <= 0 or claim_batch_size <= 0 or agent_timeout_seconds <= 0:
            raise ValueError("退避、批量和超时配置必须大于零")
        self.repository = repository
        self.handler = handler
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.retry_backoff_seconds = retry_backoff_seconds
        self.claim_batch_size = claim_batch_size
        self.agent_timeout_seconds = agent_timeout_seconds
        self.clock = clock

    async def run_once(self) -> bool:
        """先回收过期租约，再尝试执行一个到期任务；返回本轮是否领取任务。"""
        await self.recover_expired()
        now = self.clock()
        lease = await asyncio.to_thread(
            self.repository.claim_next,
            self.worker_id,
            now=now,
            locked_until=now + timedelta(seconds=self.lease_seconds),
        )
        if lease is None:
            return False

        record = await asyncio.to_thread(
            self.repository.get_for_execution, lease.task_id, lease.lock_token
        )
        if record is None:
            return True

        try:
            execution = self._execution(record)
        except NonRetryableTaskError as exc:
            await self._record_failure(record, exc.code, exc.safe_message, retryable=False)
            return True

        # 此标记必须先独立提交，再发起外部调用；它是崩溃恢复不重复调用 Agent 的边界。
        marked = await asyncio.to_thread(
            self.repository.mark_dispatch_started,
            record.task_id,
            record.lock_token,
            self.clock(),
        )
        if not marked:
            return True

        lease_lost = asyncio.Event()
        execution_task = asyncio.create_task(self.handler.execute(execution))
        heartbeat = asyncio.create_task(
            self._heartbeat(record, execution_task, lease_lost)
        )
        try:
            await asyncio.wait_for(
                execution_task, timeout=self.agent_timeout_seconds
            )
        except TimeoutError:
            # Agent 已经收到外部请求，超时后的实际结果未知；自动重放会重复消耗整份 PPT 的 Token。
            await self._record_failure(
                record, "AGENT_TIMEOUT", "Agent 调用超时", retryable=False
            )
        except RetryableTaskError as exc:
            # mark_dispatch_started 已经提交；此后即使异常被上游标为可重试，自动重放也可能重复计费。
            await self._record_failure(record, exc.code, exc.safe_message, retryable=False)
        except NonRetryableTaskError as exc:
            await self._record_failure(record, exc.code, exc.safe_message, retryable=False)
        except asyncio.CancelledError:
            if lease_lost.is_set():
                # 删除或租约转移已经由数据库写入终态；这里只负责结束外部调用。
                return True
            raise
        except Exception:
            # 派发后的未知异常既不能泄露内部信息，也不能自动重放结果未知的外部请求。
            await self._record_failure(
                record, "WORKER_EXECUTION_ERROR", "任务执行发生内部错误", retryable=False
            )
        else:
            await asyncio.to_thread(
                self.repository.complete, record.task_id, record.lock_token, self.clock()
            )
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
        return True

    async def recover_expired(self) -> int:
        """恢复过期租约；已派发任务在数据库事务外探测产物，禁止盲目重放。"""
        now = self.clock()
        expired = await asyncio.to_thread(
            self.repository.list_expired, now, limit=self.claim_batch_size
        )
        recovered = 0
        for record in expired:
            if record.dispatch_started_at is None:
                resolved = await asyncio.to_thread(
                    self.repository.recover_before_dispatch,
                    record,
                    now=now,
                    next_attempt_at=now + timedelta(seconds=self._backoff(record.attempt)),
                )
            else:
                try:
                    has_result = await self.handler.has_persisted_result(self._execution(record))
                except Exception:
                    # 探测故障不能等同于“没有产物”，保留过期行供下一轮安全重试探测。
                    continue
                resolved = await asyncio.to_thread(
                    self.repository.recover_after_dispatch,
                    record,
                    now=now,
                    has_result=has_result,
                )
            recovered += int(resolved)
        return recovered

    async def _heartbeat(
        self,
        record: TaskRecord,
        execution_task: asyncio.Task[None],
        lease_lost: asyncio.Event,
    ) -> None:
        """续租失败立即取消业务协程，避免失去租约后仍继续调用外部 Agent。"""
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            now = self.clock()
            renewed = await asyncio.to_thread(
                self.repository.renew,
                record.task_id,
                record.lock_token,
                now + timedelta(seconds=self.lease_seconds),
                now,
            )
            if not renewed:
                lease_lost.set()
                execution_task.cancel()
                return

    async def _record_failure(
        self,
        record: TaskRecord,
        code: str,
        message: str,
        *,
        retryable: bool,
    ) -> None:
        now = self.clock()
        await asyncio.to_thread(
            self.repository.record_failure,
            record,
            now=now,
            next_attempt_at=now + timedelta(seconds=self._backoff(record.attempt)),
            error_code=code[:64],
            error_message=message[:512],
            retryable=retryable,
        )

    def _backoff(self, attempt: int) -> float:
        """指数退避封顶一小时，避免故障任务形成热循环。"""
        return min(self.retry_backoff_seconds * (2 ** max(attempt - 1, 0)), 3600)

    @staticmethod
    def _execution(record: TaskRecord) -> TaskExecution:
        try:
            payload = json.loads(record.input_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise NonRetryableTaskError("TASK_INPUT_INVALID", "任务输入不是有效 JSON") from exc
        if not isinstance(payload, dict):
            raise NonRetryableTaskError("TASK_INPUT_INVALID", "任务输入必须是 JSON 对象")
        return TaskExecution(
            task_id=record.task_id,
            presentation_id=record.presentation_id,
            owner_user_id=record.owner_user_id,
            request_id=record.request_id,
            input=payload,
            attempt=record.attempt,
            max_attempts=record.max_attempts,
            lock_token=record.lock_token,
        )


__all__ = [
    "NonRetryableTaskError",
    "PersistentTaskWorker",
    "RetryableTaskError",
    "TaskExecution",
    "TaskHandler",
]

"""独立持久化 Worker 进程入口。

从仓库根目录执行：python -m backend.main_api.workers.main。
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import socket
from collections.abc import Callable

from ..core.config import ConfigValidationError, Settings, load_settings
from ..core.db import DatabaseConnectionError, create_verified_database_engine
from ..integrations.moling import MolingClient
from ..repositories.billing import BillingWorkflowRepository
from ..repositories.reconciliation import BillingReconciliationRepository
from ..repositories.tasks import TaskLeaseRepository
from ..services.billing import BillingPolicy
from ..services.generation_orchestrator import BillingGenerationOrchestrator, BillingTaskHandler
from .runner import PersistentTaskWorker, TaskHandler
from .reconciliation import BillingReconciliationWorker

logger = logging.getLogger("trainppt.task_worker")


class WorkerStartupError(RuntimeError):
    """仅携带稳定脱敏文案的 Worker 启动错误。"""


def load_handler(settings: Settings) -> TaskHandler:
    """从显式配置加载 T09 业务工厂，不把导入异常或配置原值写入日志。"""
    reference = settings.task_handler_factory
    if not reference or ":" not in reference:
        raise WorkerStartupError("Worker 处理器配置无效")
    module_name, attribute = reference.rsplit(":", 1)
    try:
        factory: Callable[[Settings], TaskHandler] = getattr(
            importlib.import_module(module_name), attribute
        )
        handler = factory(settings)
    except Exception:
        raise WorkerStartupError("Worker 处理器加载失败") from None
    if not callable(getattr(handler, "execute", None)) or not callable(
        getattr(handler, "has_persisted_result", None)
    ):
        raise WorkerStartupError("Worker 处理器契约无效")
    return handler


async def serve(settings: Settings, handler: TaskHandler) -> None:
    """持续轮询数据库；空队列仅短暂等待，不形成 CPU 或数据库热循环。"""
    assert settings.database_url is not None
    engine = create_verified_database_engine(
        settings.database_url.get_secret_value(),
        # 仅测试环境允许独立 SQLite 验收库，生产与预发布仍强制使用 MySQL。
        allow_sqlite=settings.app_env == "test",
    )
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    billing_orchestrator: BillingGenerationOrchestrator | None = None
    reconciliation_worker: BillingReconciliationWorker | None = None
    effective_handler = handler
    billing_runtime_configured = all(
        value is not None
        for value in (
            settings.moling_api_base_url,
            settings.internal_api_token,
            settings.moling_app_id,
            settings.moling_product_id,
            settings.ppt_generation_reserve_points,
            settings.ppt_generation_settle_points,
        )
    )
    # BILLING_ENABLED只控制新收费任务；关闭后若配置仍在，Worker继续安全收尾遗留hold。
    if billing_runtime_configured:
        assert settings.moling_api_base_url is not None
        assert settings.internal_api_token is not None
        assert settings.moling_app_id is not None
        assert settings.moling_product_id is not None
        assert settings.ppt_generation_reserve_points is not None
        assert settings.ppt_generation_settle_points is not None
        billing_client = MolingClient(
            base_url=settings.moling_api_base_url,
            internal_api_token=settings.internal_api_token.get_secret_value(),
            app_id=settings.moling_app_id,
            product_id=settings.moling_product_id,
            connect_timeout_seconds=settings.moling_connect_timeout_seconds,
            read_timeout_seconds=settings.moling_read_timeout_seconds,
        )
        billing_orchestrator = BillingGenerationOrchestrator(
            repository=BillingWorkflowRepository(engine),
            client=billing_client,
            policy=BillingPolicy(
                reserve_points=settings.ppt_generation_reserve_points,
                settle_points=settings.ppt_generation_settle_points,
            ),
        )
        # 新计费关闭时仍允许用原幂等键收尾历史 hold；对账器本身没有 reserve 能力。
        reconciliation_worker = BillingReconciliationWorker(
            repository=BillingReconciliationRepository(engine),
            client=billing_client,
            result_inspector=handler,
            base_interval_seconds=settings.billing_reconcile_interval_seconds,
            # 覆盖pool/connect/write/read四段最坏超时并增加5秒调度余量，禁止并行重放在途写。
            inflight_stale_seconds=(
                2 * settings.moling_connect_timeout_seconds
                + 2 * settings.moling_read_timeout_seconds
                + 5
            ),
            max_retries=settings.billing_reconcile_max_retries,
        )
        # 同一常驻进程先处理持久预占意图，再用计费包装器执行已放行的Agent任务。
        effective_handler = BillingTaskHandler(inner=handler, orchestrator=billing_orchestrator)
    worker = PersistentTaskWorker(
        repository=TaskLeaseRepository(
            engine, allow_billing_tasks=billing_orchestrator is not None
        ),
        handler=effective_handler,
        worker_id=worker_id,
        lease_seconds=settings.task_lease_seconds,
        heartbeat_seconds=settings.task_heartbeat_seconds,
        retry_backoff_seconds=settings.task_retry_backoff_seconds,
        claim_batch_size=settings.task_claim_batch_size,
        agent_timeout_seconds=settings.task_agent_timeout_seconds,
    )
    logger.info("持久化任务 Worker 已启动")
    try:
        while True:
            reconciled = (
                await reconciliation_worker.run_once()
                if reconciliation_worker is not None
                else False
            )
            prepared = (
                await billing_orchestrator.prepare_next()
                if billing_orchestrator is not None and settings.billing_enabled
                else False
            )
            claimed = await worker.run_once()
            if not reconciled and not prepared and not claimed:
                await asyncio.sleep(settings.task_poll_seconds)
    finally:
        engine.dispose()
        logger.info("持久化任务 Worker 已停止")


def main() -> int:
    """默认安全关闭；配置、数据库或处理器错误均使用稳定文案退出。"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = load_settings()
        if not settings.task_worker_enabled:
            logger.info("持久化任务 Worker 未启用")
            return 0
        handler = load_handler(settings)
        asyncio.run(serve(settings, handler))
        return 0
    except (ConfigValidationError, DatabaseConnectionError, WorkerStartupError):
        logger.error("持久化任务 Worker 启动失败")
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

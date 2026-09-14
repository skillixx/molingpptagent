"""Content Agent A2A 执行器的远端取消测试。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
import pytest
from google.genai import types
from a2a.server.tasks import TaskUpdater
from types import SimpleNamespace

from a2a.types import TaskState

from backend.slide_agent.adk_agent_executor import ADKAgentExecutor


class FakeEventQueue:
    def __init__(self) -> None:
        self.events = []

    async def enqueue_event(self, event) -> None:
        self.events.append(event)


@pytest.mark.parametrize("ending", ["normal", "error", "cancel", "empty"])
def test_visible_final_output_requires_clean_runner_end(ending) -> None:
    """可见输出分支正常结束才发完成；异常、取消及空结果不能冒充成功。"""
    session = SimpleNamespace(id="session", state={})
    runner = SimpleNamespace(app_name="test", agent=SimpleNamespace(name="root", sub_agents=[]),
                             session_service=SimpleNamespace(get_session=AsyncMock(return_value=session)))
    executor = ADKAgentExecutor(runner, object(), None, ["writer"])
    executor._upsert_session = AsyncMock(return_value=session)
    event = SimpleNamespace(author="writer", content=types.Content(parts=[types.Part(text="固定页面")]),
                            error_code=None, is_final_response=lambda: True)
    async def events(*args):
        if ending != "empty":
            yield event
        if ending == "error":
            raise RuntimeError("模拟异常")
        if ending == "cancel":
            raise asyncio.CancelledError()
    executor._run_agent = events
    queue = FakeEventQueue()
    async def run():
        await executor._process_request(types.Content(parts=[]), "session", TaskUpdater(queue, "task", "session"))
    if ending == "error":
        with pytest.raises(RuntimeError): asyncio.run(run())
    elif ending == "cancel":
        with pytest.raises(asyncio.CancelledError): asyncio.run(run())
    else:
        asyncio.run(run())
    completed = [e for e in queue.events if getattr(e, "status", None) and e.status.state == TaskState.completed]
    assert len(completed) == (1 if ending == "normal" else 0)
    if ending == "empty":
        assert queue.events[-1].status.state == TaskState.failed


def test_cancel_stops_registered_agent_execution_and_emits_terminal_status() -> None:
    executor = ADKAgentExecutor(
        runner=object(),
        card=object(),
        run_config=None,
        show_agent=[],
    )
    queue = FakeEventQueue()

    async def scenario() -> None:
        running = asyncio.create_task(asyncio.Event().wait())
        executor._running_sessions["remote-task-1"] = running
        context = SimpleNamespace(
            task_id="remote-task-1",
            context_id="session-1",
        )

        await executor.cancel(context, queue)
        await asyncio.sleep(0)

        assert running.cancelled()

    asyncio.run(scenario())

    assert len(queue.events) == 1
    assert queue.events[0].final is True
    assert queue.events[0].status.state == TaskState.canceled

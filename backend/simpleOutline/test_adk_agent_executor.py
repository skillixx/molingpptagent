"""Outline Agent A2A 执行器的远端取消测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from a2a.types import TaskState

from backend.simpleOutline.adk_agent_executor import ADKAgentExecutor


class FakeEventQueue:
    def __init__(self) -> None:
        self.events = []

    async def enqueue_event(self, event) -> None:
        self.events.append(event)


def test_cancel_stops_registered_outline_execution_and_emits_terminal_status() -> None:
    executor = ADKAgentExecutor(
        runner=object(),
        card=object(),
        run_config=None,
    )
    queue = FakeEventQueue()

    async def scenario() -> None:
        running = asyncio.create_task(asyncio.Event().wait())
        executor._running_sessions["outline-remote-task-1"] = running
        context = SimpleNamespace(
            task_id="outline-remote-task-1",
            context_id="outline-session-1",
        )

        await executor.cancel(context, queue)
        await asyncio.sleep(0)

        assert running.cancelled()

    asyncio.run(scenario())

    assert len(queue.events) == 1
    assert queue.events[0].final is True
    assert queue.events[0].status.state == TaskState.canceled

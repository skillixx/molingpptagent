"""Content Agent A2A 执行器的远端取消测试。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
import pytest
from google.genai import types
from a2a.server.tasks import TaskUpdater
from types import SimpleNamespace

from a2a.types import Part, TextPart, TaskState
from google.adk.events import Event, EventActions

from backend.slide_agent.adk_agent_executor import ADKAgentExecutor


class FakeEventQueue:
    def __init__(self) -> None:
        self.events = []

    async def enqueue_event(self, event) -> None:
        self.events.append(event)


def _execute_fixed_events(events, state):
    """通过执行器公开入口验证终态，Runner 和会话服务使用固定数据，不触发模型。"""
    session = SimpleNamespace(id="session", state=state)
    async def run_async(**_kwargs):
        for event in events:
            yield event
    runner = SimpleNamespace(run_async=run_async, app_name="test",
        session_service=SimpleNamespace(get_session=AsyncMock(return_value=session)))
    executor = ADKAgentExecutor(runner, object(), None, ["ControllerAgent"])
    context = SimpleNamespace(task_id="task", context_id="session", current_task=None,
                             message=SimpleNamespace(parts=[Part(root=TextPart(text="固定请求"))], metadata={}))
    queue = FakeEventQueue()
    asyncio.run(executor.execute(context, queue))
    return queue.events


def test_partial_plan_clean_eof_must_fail_not_complete():
    """迭代上限导致正常 EOF 时，已有一页不能冒充十页计划完成。"""
    events = _execute_fixed_events(
        [Event(author="ControllerAgent", content=types.Content(parts=[types.Part(text="固定页面")]))],
        {"slides_plan_num": 10, "current_slide_index": 1, "generated_slides_content": [{"type": "cover"}]},
    )
    assert events[-1].status.state == TaskState.failed
    assert not any(getattr(e, "status", None) and e.status.state == TaskState.completed for e in events)


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
        if ending == "normal":
            yield Event(author="ControllerAgent", actions=EventActions(escalate=True, state_delta={
                "ppt_generation_completion": {"complete": True, "planned": 1, "index": 1, "produced": 1},
            }))
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


@pytest.mark.parametrize("author,proof,expected", [
    ("ControllerAgent", {"complete": True, "planned": 2, "index": 2, "produced": 2}, TaskState.completed),
    ("ControllerAgent", {"complete": True, "planned": 2, "index": 1, "produced": 1}, TaskState.failed),
    ("ControllerAgent", {"complete": True, "planned": 2, "index": 2, "produced": 1}, TaskState.failed),
    ("ControllerAgent", {"complete": False, "planned": 2, "index": 2, "produced": 2}, TaskState.failed),
    ("ControllerAgent", {"complete": True, "planned": True, "index": True, "produced": True}, TaskState.failed),
    ("ControllerAgent", None, TaskState.failed),
    ("writer", {"complete": True, "planned": 2, "index": 2, "produced": 2}, TaskState.failed),
])
def test_only_verified_controller_completion_is_accepted(author, proof, expected):
    """完成证据必须来自 Controller 且各项计数一致，不能信任旧会话或模型文字。"""
    events = _execute_fixed_events([
        Event(author="ControllerAgent", content=types.Content(parts=[types.Part(text="固定页面")])),
        Event(author=author, actions=EventActions(escalate=True, state_delta={"ppt_generation_completion": proof})),
    ], {"ppt_generation_completion": {"complete": True}})
    terminal = [e for e in events if getattr(e, "final", False)]
    assert len(terminal) == 1
    assert terminal[0].status.state == expected


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

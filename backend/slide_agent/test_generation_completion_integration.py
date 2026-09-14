"""真实 ADK Runner/Loop/Controller 与 A2A 执行器联测；Writer 固定数据，零模型调用。"""

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from a2a.types import Part, TextPart, TaskState
from google.adk import Runner
from google.adk.agents import BaseAgent, LoopAgent
from google.adk.agents.run_config import RunConfig
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService

from backend.slide_agent.adk_agent_executor import ADKAgentExecutor
from backend.slide_agent.slide_agent.generation_utils import initialize_generation_state


class FixedWriter(BaseAgent):
    """替代外部模型，仅把当前计划页作为已校验结果交给真实 Controller。"""

    async def _run_async_impl(self, ctx):
        index = ctx.session.state["current_slide_index"]
        page = ctx.session.state["outline_json"][index]
        yield Event(author=self.name, actions=EventActions(state_delta={
            "last_slide_json": page, "is_valid_json": True,
        }))


@pytest.mark.parametrize("iterations,expected", [(1, TaskState.failed), (2, TaskState.completed)])
def test_real_loop_requires_all_planned_pages(monkeypatch, iterations, expected):
    # 加载真实 Controller 源码，但替换模型工厂；模块中的演示 Writer 不会构造真实模型客户端。
    factory_module = "backend.slide_agent.slide_agent.create_model"
    monkeypatch.setitem(sys.modules, factory_module, SimpleNamespace(create_model=lambda **_kwargs: "unused-test-model"))
    name = "backend.slide_agent.slide_agent.sub_agents.ppt_writer._completion_test"
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / "slide_agent/sub_agents/ppt_writer/agent.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)

    async def scenario():
        service = InMemorySessionService()
        state = {}
        initialize_generation_state(state, slides=[
            {"type": "cover", "data": {"title": "固定标题"}},
            {"type": "end", "data": {"title": "感谢观看"}},
        ], markdown="# 固定大纲", language="zh-CN")
        await service.create_session(app_name="test", user_id="self", session_id="session", state=state)
        loop = LoopAgent(name="FixedLoop", max_iterations=iterations,
                         sub_agents=[FixedWriter(name="FixedWriter"), module.ControllerAgent()])
        runner = Runner(app_name="test", agent=loop, session_service=service)
        executor = ADKAgentExecutor(runner, object(), RunConfig(), ["ControllerAgent"])
        class Queue:
            def __init__(self): self.events = []
            async def enqueue_event(self, event): self.events.append(event)
        queue = Queue()
        context = SimpleNamespace(task_id="task", context_id="session", current_task=None,
            message=SimpleNamespace(parts=[Part(root=TextPart(text="固定请求"))], metadata={}))
        await executor.execute(context, queue)
        terminal = [e for e in queue.events if getattr(e, "final", False)]
        assert len(terminal) == 1
        assert terminal[0].status.state == expected
    asyncio.run(scenario())

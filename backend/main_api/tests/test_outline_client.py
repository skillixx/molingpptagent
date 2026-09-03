"""Outline Agent A2A 客户端的远端取消测试。"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from a2a.types import (
    CancelTaskResponse,
    CancelTaskSuccessResponse,
    Task,
    TaskState,
    TaskStatus,
)

from backend.main_api import outline_client as outline_client_module
from backend.main_api.outline_client import A2AOutlineClientWrapper


class FakeChunk:
    def model_dump(self, **_kwargs) -> dict:
        return {
            "result": {
                "kind": "status-update",
                "taskId": "outline-remote-task-1",
                "status": {"state": "submitted"},
            },
        }


class FakeHttpClient:
    def __init__(self, **_kwargs) -> None:
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None


class FakeA2AClient:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled_task_ids: list[str] = []

    async def _stream(self):
        yield FakeChunk()
        self.started.set()
        await asyncio.Event().wait()

    def send_message_streaming(self, _request):
        return self._stream()

    async def cancel_task(self, request):
        self.cancelled_task_ids.append(request.params.id)
        return CancelTaskResponse(root=CancelTaskSuccessResponse(
            id=request.id,
            result=Task(
                id=request.params.id,
                contextId="outline-session-1",
                status=TaskStatus(state=TaskState.canceled),
            ),
        ))


class FailingStreamA2AClient(FakeA2AClient):
    async def _stream(self):
        yield FakeChunk()
        raise httpx.ReadError("模拟大纲流中断")


def test_outline_stream_cancellation_cancels_remote_agent_task(monkeypatch) -> None:
    fake_client = FakeA2AClient()
    monkeypatch.setattr(outline_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(outline_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AOutlineClientWrapper(
        session_id="outline-session-1",
        agent_url="http://outline-agent.invalid",
    )
    wrapper.agent_card = object()

    async def consume() -> None:
        async for _chunk in wrapper.generate("固定主题"):
            pass

    async def scenario() -> None:
        consumer = asyncio.create_task(consume())
        await fake_client.started.wait()
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer

    asyncio.run(scenario())

    assert fake_client.cancelled_task_ids == ["outline-remote-task-1"]


def test_outline_stream_error_after_acceptance_attempts_remote_cancel(monkeypatch) -> None:
    """大纲远端已接受任务后断流时，也必须尽力停止孤儿任务。"""
    fake_client = FailingStreamA2AClient()
    monkeypatch.setattr(outline_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(outline_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AOutlineClientWrapper(
        session_id="outline-session-network-error",
        agent_url="http://outline-agent.invalid",
    )
    wrapper.agent_card = object()

    async def consume() -> None:
        async for _chunk in wrapper.generate("固定主题"):
            pass

    with pytest.raises(httpx.ReadError):
        asyncio.run(consume())

    assert fake_client.cancelled_task_ids == ["outline-remote-task-1"]

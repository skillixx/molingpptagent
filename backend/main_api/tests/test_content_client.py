"""Content Agent A2A 客户端的取消与流式边界测试。"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from a2a.types import (
    CancelTaskResponse,
    CancelTaskSuccessResponse,
    JSONRPCErrorResponse,
    Task,
    TaskNotCancelableError,
    TaskState,
    TaskStatus,
)

from backend.main_api import content_client as content_client_module
from backend.main_api.content_client import A2AContentClientWrapper


class FakeChunk:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def model_dump(self, **_kwargs) -> dict:
        return self.payload


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
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-1",
                "status": {"state": "submitted"},
            },
        })
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
                contextId="session-1",
                status=TaskStatus(state=TaskState.canceled),
            ),
        ))


class RejectingCancelA2AClient(FakeA2AClient):
    async def cancel_task(self, request):
        self.cancelled_task_ids.append(request.params.id)
        return CancelTaskResponse(root=JSONRPCErrorResponse(
            id=request.id,
            error=TaskNotCancelableError(),
        ))


class FakeTextA2AClient(FakeA2AClient):
    async def _stream(self):
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-during-delay",
                "status": {"state": "submitted"},
            },
        })
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-during-delay",
                "status": {
                    "state": "working",
                    "message": {
                        "parts": [{"kind": "text", "text": '{"type":"cover"}'}],
                        "metadata": {"author": "ControllerAgent"},
                    },
                },
            },
        })
        await asyncio.Event().wait()


class FailingStreamA2AClient(FakeA2AClient):
    async def _stream(self):
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-network-error",
                "status": {"state": "submitted"},
            },
        })
        raise httpx.ReadError("模拟远端流中断")


def test_content_stream_cancellation_cancels_remote_agent_task(monkeypatch) -> None:
    fake_client = FakeA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(
        content_client_module,
        "A2AClient",
        lambda **_kwargs: fake_client,
    )
    wrapper = A2AContentClientWrapper(
        session_id="session-1",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def consume() -> None:
        async for _chunk in wrapper.generate("固定大纲", metadata={}):
            pass

    async def scenario() -> None:
        consumer = asyncio.create_task(consume())
        await fake_client.started.wait()
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer

    asyncio.run(scenario())

    assert fake_client.cancelled_task_ids == ["remote-task-1"]


def test_cancellation_during_chunk_delay_still_cancels_remote_task(monkeypatch) -> None:
    fake_client = FakeTextA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AContentClientWrapper(
        session_id="session-delay",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()
    received = asyncio.Event()

    async def consume() -> None:
        async for _chunk in wrapper.generate("固定大纲", metadata={}):
            received.set()

    async def scenario() -> None:
        consumer = asyncio.create_task(consume())
        await received.wait()
        await asyncio.sleep(0)
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer

    asyncio.run(scenario())

    assert fake_client.cancelled_task_ids == ["remote-task-during-delay"]


def test_protocol_error_cancel_response_is_not_reported_as_success(monkeypatch, caplog) -> None:
    """HTTP 成功不代表 A2A 取消成功，协议错误必须保留为告警。"""
    fake_client = RejectingCancelA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AContentClientWrapper(
        session_id="session-rejected-cancel",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def consume() -> None:
        async for _chunk in wrapper.generate("固定大纲", metadata={}):
            pass

    async def scenario() -> None:
        consumer = asyncio.create_task(consume())
        await fake_client.started.wait()
        consumer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await consumer

    asyncio.run(scenario())

    assert fake_client.cancelled_task_ids == ["remote-task-1"]
    assert "正文 Agent 远端取消未确认" in caplog.text
    assert "正文 Agent 远端任务已取消" not in caplog.text


def test_stream_error_after_remote_acceptance_attempts_remote_cancel(monkeypatch) -> None:
    """远端已返回任务 ID 后断流时，必须尽力停止孤儿任务且保留原异常。"""
    fake_client = FailingStreamA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AContentClientWrapper(
        session_id="session-network-error",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def consume() -> None:
        async for _chunk in wrapper.generate("固定大纲", metadata={}):
            pass

    with pytest.raises(httpx.ReadError):
        asyncio.run(consume())

    assert fake_client.cancelled_task_ids == ["remote-task-network-error"]

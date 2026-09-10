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


class HangingCancelA2AClient(FakeTextA2AClient):
    async def cancel_task(self, request):
        self.cancelled_task_ids.append(request.params.id)
        await asyncio.Event().wait()


class PartialThenFailedA2AClient(FakeA2AClient):
    async def _stream(self):
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-failed",
                "status": {
                    "state": "working",
                    "message": {
                        "parts": [{
                            "kind": "text",
                            "text": '{"type":"content","data":{"title":"半成品","items":[]}}',
                        }],
                        "metadata": {"author": "ControllerAgent"},
                    },
                },
            },
        })
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-failed",
                "status": {"state": "failed"},
            },
        })


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


def test_consumer_closing_stream_after_render_failure_cancels_remote_task(monkeypatch) -> None:
    """本地渲染失败关闭消费流时，必须取消已经派发的远端生成任务。"""

    fake_client = FakeTextA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AContentClientWrapper(
        session_id="session-render-failure",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def scenario() -> None:
        stream = wrapper.generate("固定大纲", metadata={})
        chunk = await anext(stream)
        assert chunk["type"] == "text"
        await stream.aclose()

    asyncio.run(scenario())

    assert fake_client.cancelled_task_ids == ["remote-task-during-delay"]


def test_outer_generator_close_guarantees_remote_cancel(monkeypatch) -> None:
    """即使内层流关闭不负责取消，外层生成器也必须保证远端任务被停止。"""

    fake_client = FakeTextA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AContentClientWrapper(
        session_id="session-outer-close",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def passthrough(stream_response):
        async for chunk in stream_response:
            yield chunk

    monkeypatch.setattr(wrapper, "_stream_with_remote_cancel", passthrough)

    async def scenario() -> None:
        stream = wrapper.generate("固定大纲", metadata={})
        chunk = await anext(stream)
        assert chunk["type"] == "text"
        await stream.aclose()

    asyncio.run(scenario())

    assert fake_client.cancelled_task_ids == ["remote-task-during-delay"]


def test_completed_outer_generator_does_not_cancel_remote_task(monkeypatch) -> None:
    """远端流正常结束时不得发送取消请求，避免把成功任务误标记为取消。"""

    fake_client = FakeA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AContentClientWrapper(
        session_id="session-completed",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def completed_stream():
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-completed",
                "status": {"state": "submitted"},
            },
        })
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-completed",
                "status": {"state": "completed"},
            },
        })

    monkeypatch.setattr(fake_client, "send_message_streaming", lambda _request: completed_stream())

    async def consume() -> list[dict]:
        return [chunk async for chunk in wrapper.generate("固定大纲", metadata={})]

    chunks = asyncio.run(consume())

    assert chunks[-1] == {"type": "final", "text": "对话结束", "author": "system"}
    assert fake_client.cancelled_task_ids == []


def test_submitted_then_clean_eof_is_canceled_and_not_reported_complete(monkeypatch) -> None:
    """只观察到 submitted 后断流不代表成功，必须取消远端任务并保留失败。"""

    fake_client = FakeA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AContentClientWrapper(
        session_id="session-premature-eof",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def submitted_only_stream():
        yield FakeChunk({
            "result": {
                "kind": "status-update",
                "taskId": "remote-task-premature-eof",
                "status": {"state": "submitted"},
            },
        })

    monkeypatch.setattr(fake_client, "send_message_streaming", lambda _request: submitted_only_stream())

    async def consume() -> None:
        async for _chunk in wrapper.generate("固定大纲", metadata={}):
            pass

    with pytest.raises(RuntimeError, match="完成前结束"):
        asyncio.run(consume())

    assert fake_client.cancelled_task_ids == ["remote-task-premature-eof"]


def test_partial_content_followed_by_failed_terminal_is_not_reported_complete(monkeypatch) -> None:
    """已收到局部正文也不能掩盖远端失败终态。"""

    fake_client = PartialThenFailedA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    wrapper = A2AContentClientWrapper(
        session_id="session-partial-failed",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def no_delay() -> None:
        return None

    monkeypatch.setattr(wrapper, "_delay_between_chunks", no_delay)

    async def consume() -> list[dict]:
        return [chunk async for chunk in wrapper.generate("固定大纲", metadata={})]

    with pytest.raises(RuntimeError, match="未成功完成"):
        asyncio.run(consume())

    assert fake_client.cancelled_task_ids == []


def test_inner_stream_close_failure_does_not_escape_outer_cleanup(monkeypatch, caplog) -> None:
    """本地清理失败只记录告警，不能覆盖触发关闭的原始业务异常。"""

    wrapper = A2AContentClientWrapper(
        session_id="session-close-failure",
        agent_url="http://agent.invalid",
    )

    async def failing_close(_question, metadata):
        del metadata
        try:
            yield {"type": "text", "text": "固定内容", "author": "tester"}
            await asyncio.Event().wait()
        finally:
            raise RuntimeError("模拟内层流关闭失败")

    monkeypatch.setattr(wrapper, "_generate_impl", failing_close)

    async def scenario() -> None:
        stream = wrapper.generate("固定大纲", metadata={})
        assert (await anext(stream))["text"] == "固定内容"
        await stream.aclose()

    asyncio.run(scenario())

    assert "正文 Agent 本地生成流关闭失败" in caplog.text


def test_remote_cancel_timeout_keeps_outer_close_bounded(monkeypatch, caplog) -> None:
    """远端取消端点无响应时，本地关流必须在短超时内返回。"""

    fake_client = HangingCancelA2AClient()
    monkeypatch.setattr(content_client_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(content_client_module, "A2AClient", lambda **_kwargs: fake_client)
    monkeypatch.setattr(
        content_client_module,
        "REMOTE_CANCEL_TIMEOUT_SECONDS",
        0.01,
        raising=False,
    )
    wrapper = A2AContentClientWrapper(
        session_id="session-cancel-timeout",
        agent_url="http://agent.invalid",
    )
    wrapper.agent_card = object()

    async def scenario() -> None:
        stream = wrapper.generate("固定大纲", metadata={})
        assert (await anext(stream))["type"] == "text"
        await asyncio.wait_for(stream.aclose(), timeout=0.2)

    asyncio.run(scenario())

    assert fake_client.cancelled_task_ids == ["remote-task-during-delay"]
    assert "正文 Agent 远端取消超时" in caplog.text

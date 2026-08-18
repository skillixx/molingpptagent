"""真实演示文稿 Worker 处理器的持久化与围栏测试。"""

from __future__ import annotations

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from backend.main_api.models.base import Base
from backend.main_api.models.domain import GenerationTask, Presentation
from backend.main_api.repositories.generation_results import GenerationResultRepository
from backend.main_api.workers.presentation_handler import PresentationGenerationHandler
from backend.main_api.workers.runner import NonRetryableTaskError, RetryableTaskError, TaskExecution
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer


NOW = datetime(2026, 7, 30, 9, 0, 0)


class ScriptedAgent:
    """按顺序返回测试分片，并记录处理器传入的参数。"""

    def __init__(self, chunks: list[dict[str, object]]) -> None:
        self.chunks = chunks
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def generate(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        for chunk in self.chunks:
            yield chunk


def _engine(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'presentation-handler.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return engine


def _insert_running_task(engine, *, lock_token: str = "current-lock") -> None:
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(
            Presentation(
                id="presentation-1",
                owner_user_id=479,
                title="积分闭环测试",
                status="generating",
                slides_json='{"slides":[]}',
                current_version=1,
                slide_count=0,
                template_id="template_1",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        db.add(
            GenerationTask(
                id="task-1",
                presentation_id="presentation-1",
                owner_user_id=479,
                request_id="request-1",
                status="running",
                stage="generating",
                progress=20,
                input_json="{}",
                retryable=True,
                attempt=1,
                max_attempts=3,
                next_attempt_at=NOW,
                locked_by="worker-1",
                lock_token=lock_token,
                locked_until=NOW + timedelta(minutes=2),
                created_at=NOW,
                updated_at=NOW,
            )
        )


def _execution(
    *,
    lock_token: str = "current-lock",
    content: str = "请生成一份积分闭环介绍",
    generate_from_uploaded_file: bool = False,
    generate_from_web_search: bool = True,
    template_id: str | None = None,
) -> TaskExecution:
    task_input = {
        "operation": "generate_presentation",
        "title": "积分闭环测试",
        "content": content,
        "language": "chinese",
        "model": "deepseek-chat",
        "generate_from_uploaded_file": generate_from_uploaded_file,
        "generate_from_web_search": generate_from_web_search,
    }
    if template_id is not None:
        task_input["template_id"] = template_id
    return TaskExecution(
        task_id="task-1",
        presentation_id="presentation-1",
        owner_user_id=479,
        request_id="request-1",
        input=task_input,
        attempt=1,
        max_attempts=3,
        lock_token=lock_token,
    )


def _handler(engine, outline: ScriptedAgent, content: ScriptedAgent):
    return PresentationGenerationHandler(
        repository=GenerationResultRepository(engine),
        outline_factory=lambda _session_id: outline,
        content_factory=lambda _session_id: content,
        max_document_bytes=1024 * 1024,
        now_factory=lambda: NOW,
    )


def test_handler_calls_both_agents_and_persists_editable_document(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        _insert_running_task(engine)
        outline = ScriptedAgent([{"type": "text", "text": "# 积分闭环\n## 目标"}])
        content = ScriptedAgent(
            [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"type": "cover", "data": {"title": "积分闭环", "text": "可靠计费"}},
                        ensure_ascii=False,
                    ),
                },
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "type": "content",
                            "data": {
                                "title": "关键步骤",
                                "items": [{"title": "预占", "text": "生成前冻结 1 积分"}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
        )
        handler = _handler(engine, outline, content)

        asyncio.run(handler.execute(_execution()))

        factory = sessionmaker(engine, expire_on_commit=False)
        with factory() as db:
            presentation = db.scalar(select(Presentation))
            assert presentation is not None
            document = json.loads(presentation.slides_json)
            assert presentation.status == "ready"
            assert presentation.slide_count == 2
            assert document["schema_version"] == 1
            assert document["slides"][0]["elements"][0]["type"] == "text"
            assert "积分闭环" in document["slides"][0]["elements"][0]["content"]
            task = db.scalar(select(GenerationTask))
            assert task is not None
            assert task.stage == "generating"
            assert 1 <= task.progress <= 95
            assert asyncio.run(handler.has_persisted_result(_execution())) is True
        with factory.begin() as db:
            db.execute(
                update(Presentation)
                .where(Presentation.id == "presentation-1")
                .values(status="billing_pending")
            )
        assert asyncio.run(handler.has_persisted_result(_execution())) is True
        assert outline.calls[0][1]["user_id"] == "479"
        assert content.calls[0][1]["metadata"]["user_id"] == "479"
    finally:
        engine.dispose()


def test_handler_persists_selected_template_design(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        _insert_running_task(engine)
        outline = ScriptedAgent([{"type": "text", "text": "# 毕业答辩\n## 核心成果"}])
        content = ScriptedAgent(
            [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"type": "cover", "data": {"title": "毕业答辩", "text": "成果汇报"}},
                        ensure_ascii=False,
                    ),
                },
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "type": "content",
                            "data": {
                                "title": "核心成果",
                                "items": [
                                    {"title": "成果一", "text": "已完成模板渲染"},
                                    {"title": "成果二", "text": "已完成自动展示"},
                                    {"title": "成果三", "text": "已完成文字适配"},
                                ],
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
        )
        handler = PresentationGenerationHandler(
            repository=GenerationResultRepository(engine),
            outline_factory=lambda _session_id: outline,
            content_factory=lambda _session_id: content,
            max_document_bytes=1024 * 1024,
            template_renderer=PresentationTemplateRenderer(Path(__file__).resolve().parents[1] / "template"),
            now_factory=lambda: NOW,
        )

        asyncio.run(handler.execute(_execution(template_id="template_5")))

        factory = sessionmaker(engine, expire_on_commit=False)
        with factory() as db:
            presentation = db.scalar(select(Presentation))
            assert presentation is not None
            document = json.loads(presentation.slides_json)
            assert document["viewport_size"] == 1280
            assert document["theme"]["themeColors"][0] == "#B42318"
            assert len(document["slides"][1]["elements"]) >= 16
            assert "已完成模板渲染" in presentation.slides_json
    finally:
        engine.dispose()


def test_handler_persists_capacity_paginated_template_document(tmp_path: Path) -> None:
    """Worker 必须保存模板渲染器拆页后的真实页数和全部正文。"""
    engine = _engine(tmp_path)
    try:
        _insert_running_task(engine)
        items = [
            {
                "title": f"产业要点 {index}",
                "text": f"第 {index} 项通过数据采集、治理、分析和应用形成业务闭环。" * 3,
            }
            for index in range(1, 6)
        ]
        handler = PresentationGenerationHandler(
            repository=GenerationResultRepository(engine),
            outline_factory=lambda _session_id: ScriptedAgent(
                [{"type": "text", "text": "# 大数据产业\n## 生态\n### 产业形成"}]
            ),
            content_factory=lambda _session_id: ScriptedAgent(
                [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "type": "content",
                                "data": {
                                    "title": "大数据产业生态形成",
                                    "items": items,
                                },
                                "images": [
                                    {
                                        "id": "industry-image",
                                        "src": "https://example.com/industry.jpg",
                                        "alt": "大数据产业配图",
                                    }
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ]
            ),
            max_document_bytes=1024 * 1024,
            template_renderer=PresentationTemplateRenderer(
                Path(__file__).resolve().parents[1] / "template"
            ),
            now_factory=lambda: NOW,
        )

        asyncio.run(handler.execute(_execution(template_id="template_1")))

        factory = sessionmaker(engine, expire_on_commit=False)
        with factory() as db:
            presentation = db.scalar(select(Presentation))
            assert presentation is not None
            document = json.loads(presentation.slides_json)
            assert presentation.slide_count == len(document["slides"]) == 2
            for item in items:
                assert item["text"] in presentation.slides_json
            assert all(
                any(
                    element.get("type") == "image"
                    and element.get("src") == "https://example.com/industry.jpg"
                    for element in slide["elements"]
                )
                for slide in document["slides"]
            )
    finally:
        engine.dispose()


def test_handler_escapes_agent_html_before_persisting(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        _insert_running_task(engine)
        handler = _handler(
            engine,
            ScriptedAgent([{"type": "text", "text": "# outline"}]),
            ScriptedAgent(
                [
                    {
                        "type": "text",
                        "text": '{"type":"content","data":{"title":"<script>x</script>","items":[]}}',
                    }
                ]
            ),
        )
        asyncio.run(handler.execute(_execution()))
        factory = sessionmaker(engine, expire_on_commit=False)
        with factory() as db:
            presentation = db.scalar(select(Presentation))
            assert presentation is not None
            assert "<script>" not in presentation.slides_json
            assert "&lt;script&gt;" in presentation.slides_json
    finally:
        engine.dispose()


def test_confirmed_markdown_outline_skips_outline_agent_and_preserves_search_modes(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        _insert_running_task(engine)
        outline = ScriptedAgent([])
        content = ScriptedAgent([{"type": "text", "text": '{"type":"end","data":{}}'}])
        handler = _handler(engine, outline, content)

        asyncio.run(handler.execute(_execution(
            content="# 已确认大纲\n## 第一章",
            generate_from_uploaded_file=True,
            generate_from_web_search=False,
        )))

        assert outline.calls == []
        assert content.calls[0][0] == ()
        assert content.calls[0][1]["user_question"] == "# 已确认大纲\n## 第一章"
        assert content.calls[0][1]["metadata"]["search_engine"] == ["KnowledgeBaseSearch"]
    finally:
        engine.dispose()


def test_stale_worker_cannot_persist_result(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        _insert_running_task(engine)
        handler = _handler(
            engine,
            ScriptedAgent([{"type": "text", "text": "# outline"}]),
            ScriptedAgent([{"type": "text", "text": '{"type":"end","data":{}}'}]),
        )
        with pytest.raises(NonRetryableTaskError) as error:
            asyncio.run(handler.execute(_execution(lock_token="stale-lock")))
        assert error.value.code == "GENERATION_RESULT_FENCED"
        assert asyncio.run(handler.has_persisted_result(_execution())) is False
    finally:
        engine.dispose()


def test_malformed_agent_output_is_retryable(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    try:
        _insert_running_task(engine)
        handler = _handler(
            engine,
            ScriptedAgent([{"type": "text", "text": "# outline"}]),
            ScriptedAgent([{"type": "text", "text": "not-json"}]),
        )
        with pytest.raises(RetryableTaskError) as error:
            asyncio.run(handler.execute(_execution()))
        assert error.value.code == "CONTENT_RESULT_EMPTY"
    finally:
        engine.dispose()

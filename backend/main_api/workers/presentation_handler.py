"""调用现有 A2A Agent 并持久化可编辑演示文稿的 Worker 处理器。"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Protocol
from uuid import NAMESPACE_URL, uuid5

import httpx

from ..content_client import A2AContentClientWrapper
from ..core.config import Settings
from ..core.db import create_verified_database_engine
from ..outline_client import A2AOutlineClientWrapper
from ..repositories.generation_results import GenerationResultRepository
from .runner import NonRetryableTaskError, RetryableTaskError, TaskExecution
from .template_renderer import PresentationTemplateRenderer, TemplateRenderError


logger = logging.getLogger(__name__)


class AgentWrapper(Protocol):
    def generate(self, *args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]: ...


WrapperFactory = Callable[[str], AgentWrapper]


class PresentationGenerationHandler:
    """把提示词依次交给大纲和正文 Agent，并落库为基础可编辑页面。"""

    def __init__(
        self,
        *,
        repository: GenerationResultRepository,
        outline_factory: WrapperFactory,
        content_factory: WrapperFactory,
        max_document_bytes: int,
        template_renderer: PresentationTemplateRenderer | None = None,
        now_factory: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self.repository = repository
        self.outline_factory = outline_factory
        self.content_factory = content_factory
        self.max_document_bytes = max_document_bytes
        self.template_renderer = template_renderer
        self.now_factory = now_factory

    async def execute(self, task: TaskExecution) -> None:
        payload = self._validate_input(task)
        context_id = f"trainppt-{task.task_id}"
        try:
            # 模板页提交的是用户已确认的大纲；其他调用方传普通主题时才补跑大纲 Agent。
            outline = payload["content"]
            if not self._is_markdown_outline(outline):
                outline = await self._collect_outline(
                    self.outline_factory(context_id),
                    payload["content"],
                    payload["language"],
                    task.owner_user_id,
                )
            semantic_slides = await self._collect_slides(
                self.content_factory(context_id),
                outline,
                payload["language"],
                task.owner_user_id,
                generate_from_uploaded_file=payload["generate_from_uploaded_file"],
                generate_from_web_search=payload["generate_from_web_search"],
                on_slide=lambda slides: self._persist_preview(
                    task,
                    title=payload["title"],
                    template_id=payload["template_id"],
                    outline=outline,
                    semantic_slides=slides,
                ),
            )
        except (httpx.TimeoutException, httpx.NetworkError):
            raise RetryableTaskError("AGENT_UNAVAILABLE", "Agent 暂时不可用") from None
        except (RetryableTaskError, NonRetryableTaskError):
            raise
        except Exception:
            # A2A SDK 可能包装底层连接异常；不得把上游响应或提示词写入任务错误。
            raise RetryableTaskError("AGENT_REQUEST_FAILED", "Agent 调用失败") from None

        document = self._render_document(
            title=payload["title"],
            template_id=payload["template_id"],
            semantic_slides=semantic_slides,
            task_id=task.task_id,
            presentation_id=task.presentation_id,
        )
        encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > self.max_document_bytes:
            raise NonRetryableTaskError("GENERATION_RESULT_TOO_LARGE", "生成结果超过作品大小限制")
        persisted = await asyncio.to_thread(
            self.repository.persist,
            task,
            slides_json=encoded,
            slide_count=len(document["slides"]),
            now=self.now_factory(),
        )
        if not persisted:
            raise NonRetryableTaskError("GENERATION_RESULT_FENCED", "生成结果未通过当前任务租约校验")

    async def has_persisted_result(self, task: TaskExecution) -> bool:
        return await asyncio.to_thread(self.repository.has_persisted_result, task)

    @staticmethod
    def _validate_input(task: TaskExecution) -> dict[str, Any]:
        if task.input.get("operation") != "generate_presentation":
            raise NonRetryableTaskError("TASK_OPERATION_UNSUPPORTED", "任务操作不受支持")
        values: dict[str, Any] = {}
        for key in ("title", "content", "language"):
            value = task.input.get(key)
            if not isinstance(value, str) or not value.strip():
                raise NonRetryableTaskError("TASK_INPUT_INVALID", "任务输入不完整")
            values[key] = value.strip()
        template_id = task.input.get("template_id")
        if template_id is not None and (
            not isinstance(template_id, str)
            or re.fullmatch(r"template_[1-9][0-9]*", template_id) is None
        ):
            raise NonRetryableTaskError("TASK_TEMPLATE_INVALID", "任务模板无效")
        values["template_id"] = template_id
        for key, default in (
            ("generate_from_uploaded_file", False),
            ("generate_from_web_search", True),
        ):
            value = task.input.get(key, default)
            if not isinstance(value, bool):
                raise NonRetryableTaskError("TASK_INPUT_INVALID", "任务输入不完整")
            values[key] = value
        return values

    @staticmethod
    def _is_markdown_outline(content: str) -> bool:
        return re.search(r"(?m)^#{1,6}\s+\S", content) is not None

    @staticmethod
    async def _collect_outline(
        wrapper: AgentWrapper,
        content: str,
        language: str,
        owner_user_id: int,
    ) -> str:
        parts: list[str] = []
        async for chunk in wrapper.generate(
            content,
            language=language,
            user_id=str(owner_user_id),
        ):
            if chunk.get("type") == "text" and isinstance(chunk.get("text"), str):
                parts.append(chunk["text"])
        outline = "".join(parts).strip()
        if not outline:
            raise RetryableTaskError("OUTLINE_RESULT_EMPTY", "大纲 Agent 未返回有效结果")
        return outline

    @classmethod
    async def _collect_slides(
        cls,
        wrapper: AgentWrapper,
        outline: str,
        language: str,
        owner_user_id: int,
        *,
        generate_from_uploaded_file: bool,
        generate_from_web_search: bool,
        on_slide: Callable[[list[dict[str, Any]]], Any] | None = None,
    ) -> list[dict[str, Any]]:
        slides: list[dict[str, Any]] = []
        search_engine: list[str] = []
        if generate_from_uploaded_file:
            search_engine.append("KnowledgeBaseSearch")
        if generate_from_web_search:
            search_engine.append("DocumentSearch")
        metadata = {
            "user_id": str(owner_user_id),
            "search_engine": search_engine,
            "language": language,
        }
        async for chunk in wrapper.generate(user_question=outline, metadata=metadata):
            if chunk.get("type") != "text" or not isinstance(chunk.get("text"), str):
                continue
            parsed = cls._parse_semantic_slide(chunk["text"])
            if parsed is not None:
                slides.append(parsed)
                if on_slide is not None:
                    await on_slide(list(slides))
        if not slides:
            raise RetryableTaskError("CONTENT_RESULT_EMPTY", "正文 Agent 未返回有效页面")
        if len(slides) > 200:
            raise NonRetryableTaskError("CONTENT_RESULT_TOO_MANY_SLIDES", "生成页数超过限制")
        return slides

    async def _persist_preview(
        self,
        task: TaskExecution,
        *,
        title: str,
        template_id: str | None,
        outline: str,
        semantic_slides: list[dict[str, Any]],
    ) -> None:
        """收到完整页面后立即发布只读预览，最终完成前不开放编辑。"""
        document = self._render_document(
            title=title,
            template_id=template_id,
            semantic_slides=semantic_slides,
            task_id=task.task_id,
            presentation_id=task.presentation_id,
        )
        encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > self.max_document_bytes:
            raise NonRetryableTaskError("GENERATION_RESULT_TOO_LARGE", "生成结果超过作品大小限制")
        expected = self._expected_slide_count(outline)
        progress = min(95, max(5, int(len(semantic_slides) / max(expected, 1) * 100)))
        persisted = await asyncio.to_thread(
            self.repository.persist_progress,
            task,
            slides_json=encoded,
            slide_count=len(semantic_slides),
            progress=progress,
            now=self.now_factory(),
        )
        if not persisted:
            raise NonRetryableTaskError("GENERATION_RESULT_FENCED", "生成预览未通过当前任务租约校验")

    @staticmethod
    def _expected_slide_count(outline: str) -> int:
        """按既有大纲规则估算总页数，仅用于展示单调递增的近似进度。"""
        section_count = len(re.findall(r"(?m)^##\s+\S", outline))
        content_count = len(re.findall(r"(?m)^###\s+\S", outline))
        return 1 + (1 if section_count else 0) + section_count + content_count + 1

    @staticmethod
    def _parse_semantic_slide(raw: str) -> dict[str, Any] | None:
        text = raw.strip()
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(value, dict) or not isinstance(value.get("type"), str):
            return None
        return value

    def _render_document(
        self,
        *,
        title: str,
        template_id: str | None,
        semantic_slides: list[dict[str, Any]],
        task_id: str,
        presentation_id: str,
    ) -> dict[str, Any]:
        if template_id and self.template_renderer is not None:
            try:
                return self.template_renderer.render(
                    template_id=template_id,
                    semantic_slides=semantic_slides,
                    task_id=task_id,
                    fallback_title=title,
                )
            except TemplateRenderError as exc:
                # 日志只记录任务、模板与槽位类别，禁止写入用户完整标题或正文。
                logger.warning(
                    "presentation template render failed task_id=%s presentation_id=%s "
                    "template_id=%s code=%s slide_type=%s layout_kind=%s slot_type=%s "
                    "text_length=%s font_size=%s width=%s height=%s item_count=%s "
                    "image_count=%s variant=%s",
                    task_id,
                    presentation_id,
                    template_id,
                    exc.code,
                    exc.context.get("slide_type", "unknown"),
                    exc.context.get("layout_kind", "default"),
                    exc.context.get("slot_type", exc.context.get("text_type", "unknown")),
                    exc.context.get("text_length", "unknown"),
                    exc.context.get("font_size", exc.context.get("minimum_font_size", "unknown")),
                    exc.context.get("width", "unknown"),
                    exc.context.get("height", "unknown"),
                    exc.context.get("item_count", "unknown"),
                    exc.context.get("image_count", "unknown"),
                    exc.context.get("variant", "unknown"),
                )
                safe_messages = {
                    "TEMPLATE_TEXT_OVERFLOW": "模板无法容纳本页文字",
                    "TEMPLATE_MISSING_SLOT": "模板缺少必要内容槽位",
                    "TEMPLATE_DATA_INVALID": "模板数据无效",
                    "TEMPLATE_RESOURCE_MISSING": "模板资源缺失",
                }
                code = exc.code if exc.code in safe_messages else "TEMPLATE_DATA_INVALID"
                raise NonRetryableTaskError(code, safe_messages[code]) from None
        return self._render_basic_document(
            title=title,
            semantic_slides=semantic_slides,
            task_id=task_id,
        )

    @classmethod
    def _render_basic_document(
        cls,
        *,
        title: str,
        semantic_slides: list[dict[str, Any]],
        task_id: str,
    ) -> dict[str, Any]:
        slides = [
            cls._render_slide(item, task_id=task_id, index=index, fallback_title=title)
            for index, item in enumerate(semantic_slides)
        ]
        return {
            "schema_version": 1,
            "slides": slides,
            "theme": {
                "themeColors": ["#0F766E", "#2563EB", "#D97706", "#DC2626", "#334155"],
                "fontColor": "#172033",
                "fontName": "Microsoft YaHei",
                "backgroundColor": "#FFFFFF",
            },
            "viewport_size": 1000,
            "viewport_ratio": 0.5625,
        }

    @classmethod
    def _render_slide(
        cls,
        item: dict[str, Any],
        *,
        task_id: str,
        index: int,
        fallback_title: str,
    ) -> dict[str, Any]:
        slide_type = item.get("type", "content")
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        title = cls._plain_text(data.get("title")) or (fallback_title if index == 0 else "")
        body = cls._body_text(data, item)
        slide_id = cls._stable_id(task_id, f"slide-{index}")
        elements: list[dict[str, Any]] = []
        if title:
            elements.append(
                cls._text_element(
                    task_id,
                    f"title-{index}",
                    title,
                    left=70,
                    top=70 if slide_type != "cover" else 175,
                    width=860,
                    height=90,
                    font_size=42 if slide_type == "cover" else 32,
                    bold=True,
                    centered=slide_type in {"cover", "end"},
                    text_type="title",
                )
            )
        if body:
            elements.append(
                cls._text_element(
                    task_id,
                    f"body-{index}",
                    body,
                    left=90,
                    top=285 if slide_type == "cover" else 175,
                    width=820,
                    height=280,
                    font_size=20,
                    centered=slide_type in {"cover", "end"},
                    text_type="content",
                )
            )
        return {
            "id": slide_id,
            "elements": elements,
            "background": {"type": "solid", "color": "#FFFFFF"},
            "type": slide_type,
        }

    @classmethod
    def _text_element(
        cls,
        task_id: str,
        key: str,
        text: str,
        *,
        left: int,
        top: int,
        width: int,
        height: int,
        font_size: int,
        bold: bool = False,
        centered: bool = False,
        text_type: str,
    ) -> dict[str, Any]:
        escaped = html.escape(text).replace("\n", "<br>")
        content = f'<span style="font-size: {font_size}px;">{escaped}</span>'
        if bold:
            content = f"<strong>{content}</strong>"
        align = ' style="text-align: center;"' if centered else ""
        return {
            "type": "text",
            "id": cls._stable_id(task_id, key),
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "rotate": 0,
            "content": f"<p{align}>{content}</p>",
            "defaultFontName": "Microsoft YaHei",
            "defaultColor": "#172033",
            "textType": text_type,
        }

    @classmethod
    def _body_text(cls, data: dict[str, Any], item: dict[str, Any]) -> str:
        candidates = data.get("items")
        lines: list[str] = []
        if isinstance(candidates, list):
            for candidate in candidates:
                if isinstance(candidate, dict):
                    heading = cls._plain_text(candidate.get("title"))
                    detail = cls._plain_text(candidate.get("text") or candidate.get("content"))
                    line = "：".join(part for part in (heading, detail) if part)
                else:
                    line = cls._plain_text(candidate)
                if line:
                    lines.append(f"• {line}")
        for key in ("text", "subtitle"):
            value = cls._plain_text(data.get(key))
            if value:
                lines.append(value)
        if not lines and item.get("type") == "end":
            lines.append("感谢观看")
        return "\n".join(lines)

    @staticmethod
    def _plain_text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return ""

    @staticmethod
    def _stable_id(task_id: str, key: str) -> str:
        return uuid5(NAMESPACE_URL, f"trainppt:{task_id}:{key}").hex[:16]


def create_handler(settings: Settings) -> PresentationGenerationHandler:
    """Worker 默认工厂；仅创建独立连接池，不执行迁移或任何外部写入。"""
    if settings.database_url is None:
        raise ValueError("DATABASE_URL is required")
    engine = create_verified_database_engine(
        settings.database_url.get_secret_value(),
        allow_sqlite=settings.app_env == "test",
    )
    return PresentationGenerationHandler(
        repository=GenerationResultRepository(engine),
        outline_factory=lambda session_id: A2AOutlineClientWrapper(
            session_id=session_id,
            agent_url=settings.outline_api,
        ),
        content_factory=lambda session_id: A2AContentClientWrapper(
            session_id=session_id,
            agent_url=settings.content_api,
        ),
        max_document_bytes=settings.presentation_json_max_bytes,
        template_renderer=PresentationTemplateRenderer(Path(__file__).resolve().parents[1] / "template"),
    )


__all__ = ["PresentationGenerationHandler", "create_handler"]

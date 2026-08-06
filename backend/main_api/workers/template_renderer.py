"""把 Agent 语义页映射到 PPTist 模板的样式与文字槽位。"""

from __future__ import annotations

import copy
import html
import json
import math
import re
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from lxml import etree
from lxml import html as lxml_html


class TemplateRenderError(RuntimeError):
    """模板缺失、损坏或不具备必要版式时使用的稳定错误。"""


class PresentationTemplateRenderer:
    """确定性选择模板版式，并保留装饰、背景、字体和元素坐标。"""

    _SAFE_TEMPLATE_ID = re.compile(r"^template_[1-9][0-9]*$")

    def __init__(self, template_root: Path) -> None:
        self.template_root = template_root.resolve()
        self._cache: dict[str, dict[str, Any]] = {}

    def render(
        self,
        *,
        template_id: str,
        semantic_slides: list[dict[str, Any]],
        task_id: str,
        fallback_title: str,
    ) -> dict[str, Any]:
        template = self._load(template_id)
        source_slides = template.get("slides")
        if not isinstance(source_slides, list) or not source_slides:
            raise TemplateRenderError("模板没有可用页面")

        rendered: list[dict[str, Any]] = []
        transition_number = 0
        for index, semantic in enumerate(semantic_slides):
            if semantic.get("type") == "transition":
                transition_number += 1
            rendered.append(self._render_slide(
                source_slides,
                semantic,
                task_id=task_id,
                index=index,
                fallback_title=fallback_title,
                transition_number=transition_number,
            ))
        width = self._number(template.get("width"), 1000)
        height = self._number(template.get("height"), width * 0.5625)
        theme = template.get("theme") if isinstance(template.get("theme"), dict) else {}
        return {
            "schema_version": 1,
            "slides": rendered,
            "theme": copy.deepcopy(theme),
            "viewport_size": width,
            "viewport_ratio": height / width,
        }

    def _load(self, template_id: str) -> dict[str, Any]:
        if not self._SAFE_TEMPLATE_ID.fullmatch(template_id):
            raise TemplateRenderError("模板标识无效")
        cached = self._cache.get(template_id)
        if cached is not None:
            return cached
        path = (self.template_root / f"{template_id}.json").resolve()
        if path.parent != self.template_root or not path.is_file():
            raise TemplateRenderError("模板不存在")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise TemplateRenderError("模板数据损坏") from None
        if not isinstance(value, dict):
            raise TemplateRenderError("模板数据损坏")
        self._cache[template_id] = value
        return value

    def _render_slide(
        self,
        templates: list[dict[str, Any]],
        semantic: dict[str, Any],
        *,
        task_id: str,
        index: int,
        fallback_title: str,
        transition_number: int,
    ) -> dict[str, Any]:
        slide_type = semantic.get("type") if isinstance(semantic.get("type"), str) else "content"
        data = semantic.get("data") if isinstance(semantic.get("data"), dict) else {}
        candidates = [slide for slide in templates if slide.get("type") == slide_type]
        if not candidates:
            candidates = [slide for slide in templates if slide.get("type") == "content"]
        if not candidates:
            raise TemplateRenderError("模板缺少内容版式")
        selected = self._select(candidates, slide_type, data, index)
        slide = copy.deepcopy(selected)
        elements = slide.get("elements") if isinstance(slide.get("elements"), list) else []

        title = self._text(data.get("title")) or (fallback_title if index == 0 else "")
        if slide_type == "cover":
            self._fill_single(elements, "title", title, max_lines=2)
            self._fill_single(elements, "content", self._text(data.get("text")), max_lines=3)
        elif slide_type == "contents":
            self._fill_list(elements, "item", self._string_items(data.get("items")), max_lines=2)
            self._fill_numbers(elements, "itemNumber", len(self._string_items(data.get("items"))), semantic)
        elif slide_type == "transition":
            self._fill_single(elements, "title", title, max_lines=2)
            self._fill_single(elements, "content", self._text(data.get("text")), max_lines=4)
            self._fill_list(elements, "partNumber", [str(transition_number).zfill(2)], max_lines=1)
        elif slide_type == "end":
            if title:
                self._fill_single(elements, "title", title, max_lines=2)
            if self._text(data.get("text")):
                self._fill_single(elements, "content", self._text(data.get("text")), max_lines=3)
        else:
            self._fill_single(elements, "title", title, max_lines=2)
            self._fill_content(elements, data, semantic)

        slide["id"] = self._stable_id(task_id, f"slide-{index}")
        slide["elements"] = self._unique_element_ids(elements, task_id, index)
        slide["type"] = slide_type
        return slide

    def _select(
        self,
        candidates: list[dict[str, Any]],
        slide_type: str,
        data: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        if slide_type == "content":
            count = max(1, len(self._content_items(data.get("items"))))
            scored = sorted(
                candidates,
                key=lambda slide: (self._content_layout_score(slide, count), str(slide.get("id", ""))),
            )
            best = self._content_layout_score(scored[0], count)
            peers = [slide for slide in scored if self._content_layout_score(slide, count) == best]
            return peers[index % len(peers)]
        if slide_type == "contents":
            count = len(self._string_items(data.get("items")))
            return min(
                candidates,
                key=lambda slide: (self._slot_distance(slide, "item", count), str(slide.get("id", ""))),
            )
        # 封面、章节和结束页固定使用同套首选版式，避免一份作品视觉语言漂移。
        return candidates[0]

    def _content_layout_score(self, slide: dict[str, Any], count: int) -> tuple[int, int]:
        item_slots = self._slot_count(slide, "item")
        content_slots = self._slot_count(slide, "content")
        if item_slots >= count:
            return (0, item_slots - count)
        if content_slots >= count:
            return (1, content_slots - count)
        if content_slots > 0:
            return (2, count - content_slots)
        return (3, count - item_slots)

    def _fill_content(self, elements: list[dict[str, Any]], data: dict[str, Any], semantic: dict[str, Any]) -> None:
        items = self._content_items(data.get("items"))
        item_slots = self._slots(elements, "item")
        if item_slots:
            self._fill_list(elements, "itemTitle", [item[0] for item in items], max_lines=2)
            self._fill_list(elements, "item", [item[1] or item[0] for item in items], max_lines=5)
            self._fill_numbers(elements, "itemNumber", len(items), semantic)
            return

        content_slots = self._slots(elements, "content")
        subtitle_slots = self._slots(elements, "subtitle")
        if len(content_slots) > 1:
            self._fill_list(elements, "subtitle", [item[0] for item in items], max_lines=2)
            self._fill_list(
                elements,
                "content",
                [item[1] or item[0] for item in items],
                max_lines=6,
            )
            return

        lines = ["：".join(part for part in item if part) for item in items]
        body = "\n".join(f"• {line}" for line in lines if line)
        if not body:
            body = self._text(data.get("text"))
        self._fill_single(elements, "content", body, max_lines=max(6, len(lines) * 2))
        if subtitle_slots and items:
            self._fill_single(elements, "subtitle", items[0][0], max_lines=2)

    def _fill_single(self, elements: list[dict[str, Any]], slot_type: str, value: str, *, max_lines: int) -> None:
        self._fill_list(elements, slot_type, [value] if value else [], max_lines=max_lines)

    def _fill_numbers(
        self,
        elements: list[dict[str, Any]],
        slot_type: str,
        count: int,
        semantic: dict[str, Any],
    ) -> None:
        offset = semantic.get("offset") if isinstance(semantic.get("offset"), int) else 0
        values = [str(index + offset + 1).zfill(2) for index in range(count)]
        self._fill_list(elements, slot_type, values, max_lines=1)

    def _fill_list(self, elements: list[dict[str, Any]], slot_type: str, values: list[str], *, max_lines: int) -> None:
        slots = self._slots(elements, slot_type)
        unused_ids: set[str] = set()
        unused_groups: set[str] = set()
        for index, element in enumerate(slots):
            value = values[index] if index < len(values) else ""
            if value:
                self._replace_element_text(element, value, max_lines=max_lines)
                continue
            if isinstance(element.get("id"), str):
                unused_ids.add(element["id"])
            if isinstance(element.get("groupId"), str):
                unused_groups.add(element["groupId"])
        if unused_ids or unused_groups:
            elements[:] = [
                element for element in elements
                if element.get("id") not in unused_ids
                and element.get("groupId") not in unused_groups
            ]

    def _replace_element_text(self, element: dict[str, Any], value: str, *, max_lines: int) -> None:
        if element.get("type") == "text":
            raw = element.get("content") if isinstance(element.get("content"), str) else ""
            element["content"] = self._replace_html(raw, value, element, max_lines)
            return
        text = element.get("text") if isinstance(element.get("text"), dict) else None
        if text is not None:
            raw = text.get("content") if isinstance(text.get("content"), str) else ""
            text["content"] = self._replace_html(raw, value, element, max_lines)

    def _replace_html(self, raw: str, value: str, element: dict[str, Any], max_lines: int) -> str:
        try:
            root = lxml_html.fragment_fromstring(raw or "<p><span></span></p>", create_parent="div")
        except (etree.ParserError, ValueError):
            root = lxml_html.fragment_fromstring("<p><span></span></p>", create_parent="div")
        target = next((node for node in root.iterdescendants() if node.text and node.text.strip()), None)
        if target is None:
            target = next(root.iterdescendants(), root)
        for node in root.iter():
            node.text = None
            for child in node:
                child.tail = None
        lines = value.splitlines() or [value]
        target.text = lines[0]
        for line in lines[1:]:
            br = etree.SubElement(target, "br")
            br.tail = line
        self._adapt_font_size(root, value, element, max_lines)
        return "".join(
            etree.tostring(child, encoding="unicode", method="html") for child in root
        ) or f"<p>{html.escape(value)}</p>"

    def _adapt_font_size(self, root: etree._Element, value: str, element: dict[str, Any], max_lines: int) -> None:
        sizes: list[float] = []
        for node in root.iter():
            style = node.get("style", "")
            match = re.search(r"font-size\s*:\s*([0-9.]+)px", style)
            if match:
                sizes.append(float(match.group(1)))
        if not sizes:
            return
        original = max(sizes)
        width = self._number(element.get("width"), 300)
        height = self._number(element.get("height"), original * max_lines * 1.45)
        weighted_length = sum(1.0 if ord(char) > 255 else 0.56 for char in value.replace("\n", ""))
        # PPTist 未显式设置行高时接近 1.45；以文本框真实高度限制行数，避免正文压过分隔线。
        height_lines = max(1, math.floor(height / max(original * 1.45, 1.0)))
        available_lines = min(max_lines, height_lines)
        # 预留 10% 给文本框内边距、标点和浏览器换行差异，避免理论刚好容纳却实际多出一行。
        capacity = max(1.0, width / max(original, 1.0) * available_lines * 0.9)
        ratio = min(1.0, capacity / max(weighted_length, 1.0))
        adapted = max(10.0, round(original * ratio, 1))
        for node in root.iter():
            style = node.get("style")
            if style and re.search(r"font-size\s*:\s*[0-9.]+px", style):
                node.set("style", re.sub(r"font-size\s*:\s*[0-9.]+px", f"font-size: {adapted}px", style))

    def _unique_element_ids(self, elements: list[dict[str, Any]], task_id: str, index: int) -> list[dict[str, Any]]:
        group_ids: dict[str, str] = {}
        for position, element in enumerate(elements):
            original = str(element.get("id") or position)
            element["id"] = self._stable_id(task_id, f"element-{index}-{original}-{position}")
            group_id = element.get("groupId")
            if isinstance(group_id, str):
                group_ids.setdefault(group_id, self._stable_id(task_id, f"group-{index}-{group_id}"))
                element["groupId"] = group_ids[group_id]
        return elements

    @classmethod
    def _slots(cls, elements: list[dict[str, Any]], slot_type: str) -> list[dict[str, Any]]:
        return sorted(
            [element for element in elements if cls._slot_type(element) == slot_type],
            key=lambda element: (
                cls._number(element.get("top"), 0),
                cls._number(element.get("left"), 0),
            ),
        )

    @classmethod
    def _slot_count(cls, slide: dict[str, Any], slot_type: str) -> int:
        elements = slide.get("elements") if isinstance(slide.get("elements"), list) else []
        return len(cls._slots(elements, slot_type))

    @classmethod
    def _slot_distance(cls, slide: dict[str, Any], slot_type: str, count: int) -> tuple[int, int]:
        slots = cls._slot_count(slide, slot_type)
        return (0 if slots >= count else 1, abs(slots - count))

    @staticmethod
    def _slot_type(element: dict[str, Any]) -> str | None:
        if element.get("type") == "text" and isinstance(element.get("textType"), str):
            return element["textType"]
        text = element.get("text")
        if element.get("type") == "shape" and isinstance(text, dict) and isinstance(text.get("type"), str):
            return text["type"]
        return None

    @classmethod
    def _content_items(cls, value: Any) -> list[tuple[str, str]]:
        if not isinstance(value, list):
            return []
        items: list[tuple[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                title = cls._text(item.get("title"))
                body = cls._text(item.get("text") or item.get("content"))
                if title or body:
                    items.append((title, body))
            else:
                text = cls._text(item)
                if text:
                    items.append((text, ""))
        return items

    @classmethod
    def _string_items(cls, value: Any) -> list[str]:
        return [title or body for title, body in cls._content_items(value)]

    @staticmethod
    def _text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return ""

    @staticmethod
    def _number(value: Any, fallback: float) -> float:
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else fallback

    @staticmethod
    def _stable_id(task_id: str, key: str) -> str:
        return uuid5(NAMESPACE_URL, f"trainppt:{task_id}:{key}").hex[:16]


__all__ = ["PresentationTemplateRenderer", "TemplateRenderError"]

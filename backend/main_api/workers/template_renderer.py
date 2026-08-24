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
    """携带安全分类和最小版式上下文的模板错误，不包含用户完整正文。"""

    def __init__(
        self,
        message: str,
        *,
        code: str = "TEMPLATE_DATA_INVALID",
        context: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}


class PresentationTemplateRenderer:
    """确定性选择模板版式，并保留装饰、背景、字体和元素坐标。"""

    _SAFE_TEMPLATE_ID = re.compile(r"^template_[1-9][0-9]*$")
    _DEFAULT_FONT_SIZE = 16.0
    _MINIMUM_READABLE_FONT_SIZE = 12.0
    _TEXT_PADDING = 20.0
    _LINE_HEIGHT = 1.5
    _WIDTH_SAFETY_FACTOR = 0.9

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
            raise TemplateRenderError("模板没有可用页面", code="TEMPLATE_DATA_INVALID")

        # 先按模板真实槽位容量拆页，后续版式选择就不需要把多条正文挤进单个文本框。
        semantic_slides = self._paginate_content_slides(source_slides, semantic_slides)
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
        for slide in rendered:
            self._validate_slide_text_bounds(slide, height)
        theme = template.get("theme") if isinstance(template.get("theme"), dict) else {}
        return {
            "schema_version": 1,
            "slides": rendered,
            "theme": copy.deepcopy(theme),
            "viewport_size": width,
            "viewport_ratio": height / width,
        }

    def _paginate_content_slides(
        self,
        source_slides: list[dict[str, Any]],
        semantic_slides: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """按内容模板的最大要点槽位拆页，完整保留 Agent 返回的项目顺序。"""
        content_templates = [
            slide for slide in source_slides if slide.get("type") == "content"
        ]
        max_item_slots = max(
            (self._slot_count(slide, "item") for slide in content_templates),
            default=0,
        )
        if max_item_slots <= 0:
            return copy.deepcopy(semantic_slides)
        paginated: list[dict[str, Any]] = []
        for semantic in semantic_slides:
            data = semantic.get("data") if isinstance(semantic.get("data"), dict) else None
            raw_items = data.get("items") if data is not None else None
            if (
                semantic.get("type") != "content"
                or not isinstance(raw_items, list)
            ):
                paginated.append(copy.deepcopy(semantic))
                continue

            # 单项页可以使用更宽的版式；项目拆分后再按新数量复算，直到版式容量稳定。
            target_count = min(max(1, len(raw_items)), max_item_slots)
            expanded_items = copy.deepcopy(raw_items)
            for _ in range(max_item_slots + 1):
                item_capacity = self._content_item_capacity(
                    content_templates,
                    target_count,
                    prefer_images=bool(self._semantic_images(semantic.get("images"))),
                )
                expanded_items = [
                    expanded
                    for item in raw_items
                    for expanded in self._split_content_item(item, item_capacity)
                ]
                next_count = min(max(1, len(expanded_items)), max_item_slots)
                if next_count == target_count:
                    break
                target_count = next_count
            if len(expanded_items) <= max_item_slots:
                page = copy.deepcopy(semantic)
                page["data"]["items"] = expanded_items
                paginated.append(page)
                continue

            title = self._text(data.get("title"))
            for offset in range(0, len(expanded_items), max_item_slots):
                page = copy.deepcopy(semantic)
                page_data = page["data"]
                page_data["items"] = copy.deepcopy(expanded_items[offset:offset + max_item_slots])
                if offset > 0 and title:
                    page_data["title"] = f"{title}（续）"
                paginated.append(page)
        return paginated

    def _content_item_capacity(
        self,
        content_templates: list[dict[str, Any]],
        count: int,
        *,
        prefer_images: bool,
    ) -> int:
        """返回指定项目数量最终会选中版式的最小可读正文容量。"""
        selected = self._select(
            content_templates,
            "content",
            {"items": [{"title": "容量占位"} for _ in range(count)]},
            0,
            prefer_images=prefer_images,
        )
        elements = selected.get("elements") if isinstance(selected.get("elements"), list) else []
        capacities = [
            self._slot_readable_capacity(element)
            for element in self._slots(elements, "item")
        ]
        return min(capacities, default=1)

    @classmethod
    def _split_content_item(cls, item: Any, capacity: int) -> list[Any]:
        """把单条超长正文切成可读片段，保持原字符顺序且不做静默截断。"""
        if not isinstance(item, dict):
            return [copy.deepcopy(item)]
        if item.get("kind") == "chart":
            return [copy.deepcopy(item)]
        body_key = "text" if cls._text(item.get("text")) else "content"
        body = cls._text(item.get(body_key))
        if not body:
            return [copy.deepcopy(item)]
        chunks = cls._split_weighted_text(body, capacity)
        if len(chunks) == 1:
            return [copy.deepcopy(item)]

        title = cls._text(item.get("title"))
        expanded: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks):
            part = copy.deepcopy(item)
            part[body_key] = chunk
            if index > 0 and title:
                part["title"] = f"{title}（续）"
            expanded.append(part)
        return expanded

    @classmethod
    def _split_weighted_text(cls, value: str, capacity: int) -> list[str]:
        """按中英文显示宽度切分字符串，切分结果连接后必须与原文完全一致。"""
        chunks: list[str] = []
        current: list[str] = []
        weight = 0.0
        limit = max(1, capacity)
        for char in value:
            char_weight = cls._character_weight(char)
            if current and weight + char_weight > limit:
                chunks.append("".join(current))
                current = []
                weight = 0.0
            current.append(char)
            weight += char_weight
        if current:
            chunks.append("".join(current))
        return chunks or [value]

    @classmethod
    def _slot_readable_capacity(cls, element: dict[str, Any]) -> int:
        """按最小可读字号估算正文槽位容量，不允许靠极小字号换取容量。"""
        usable_width = max(
            1.0,
            cls._number(element.get("width"), 300) - cls._TEXT_PADDING,
        )
        usable_height = max(
            1.0,
            cls._number(element.get("height"), 100) - cls._TEXT_PADDING,
        )
        lines = max(
            1,
            math.floor(
                usable_height
                / (cls._MINIMUM_READABLE_FONT_SIZE * cls._LINE_HEIGHT)
            ),
        )
        return max(
            1,
            math.floor(
                usable_width
                / cls._MINIMUM_READABLE_FONT_SIZE
                * lines
                * cls._WIDTH_SAFETY_FACTOR
            ),
        )

    def _load(self, template_id: str) -> dict[str, Any]:
        if not self._SAFE_TEMPLATE_ID.fullmatch(template_id):
            raise TemplateRenderError("模板标识无效", code="TEMPLATE_DATA_INVALID")
        cached = self._cache.get(template_id)
        if cached is not None:
            return cached
        path = (self.template_root / f"{template_id}.json").resolve()
        if path.parent != self.template_root or not path.is_file():
            raise TemplateRenderError("模板不存在", code="TEMPLATE_RESOURCE_MISSING")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise TemplateRenderError("模板数据损坏", code="TEMPLATE_DATA_INVALID") from None
        if not isinstance(value, dict):
            raise TemplateRenderError("模板数据损坏", code="TEMPLATE_DATA_INVALID")
        slides = value.get("slides") if isinstance(value.get("slides"), list) else []
        for slide in slides:
            elements = slide.get("elements") if isinstance(slide, dict) and isinstance(slide.get("elements"), list) else []
            for element in elements:
                source = element.get("src") if isinstance(element, dict) else None
                if not isinstance(source, str) or not source.startswith("/api/data/"):
                    continue
                filename = source.rsplit("/", 1)[-1]
                # 只验证由本模板目录提供的API资源；不请求外网，也不把原始路径写入错误。
                if not filename or Path(filename).name != filename or not (self.template_root / filename).is_file():
                    raise TemplateRenderError(
                        "模板资源缺失", code="TEMPLATE_RESOURCE_MISSING"
                    )
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
            raise TemplateRenderError("模板缺少内容版式", code="TEMPLATE_MISSING_SLOT")
        semantic_images = self._semantic_images(semantic.get("images"))
        selected = self._select(
            candidates,
            slide_type,
            data,
            index,
            prefer_images=bool(semantic_images),
        )
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

        # 空槽清理可能连带移除分组图片，因此必须在文字槽处理完成后再应用 Agent 配图。
        self._fill_images(elements, semantic_images)
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
        *,
        prefer_images: bool = False,
    ) -> dict[str, Any]:
        if slide_type == "content":
            requested_layout_kind = self._requested_layout_kind(data)
            if requested_layout_kind:
                matching_kind = [
                    slide for slide in candidates
                    if slide.get("layoutKind") == requested_layout_kind
                ]
                if matching_kind:
                    candidates = matching_kind
            else:
                # 年度数字属于显式语义版式，普通四项内容不能因为页序轮换而误选。
                ordinary_candidates = [
                    slide for slide in candidates
                    if slide.get("layoutKind") != "metrics"
                ]
                if ordinary_candidates:
                    candidates = ordinary_candidates
            count = max(1, len(self._content_items(data.get("items"))))
            scored = sorted(
                candidates,
                key=lambda slide: (self._content_layout_score(slide, count), str(slide.get("id", ""))),
            )
            best = self._content_layout_score(scored[0], count)
            peers = [slide for slide in scored if self._content_layout_score(slide, count) == best]
            if prefer_images:
                image_peers = [slide for slide in peers if self._image_count(slide) > 0]
                if image_peers:
                    peers = image_peers
            else:
                # 无配图时优先选择纯文字版式，避免向用户展示没有内容的图片占位框。
                text_peers = [slide for slide in peers if self._image_count(slide) == 0]
                if text_peers:
                    peers = text_peers
            return peers[index % len(peers)]
        if slide_type == "contents":
            count = len(self._string_items(data.get("items")))
            return min(
                candidates,
                key=lambda slide: (self._slot_distance(slide, "item", count), str(slide.get("id", ""))),
            )
        # 封面、章节和结束页固定使用同套首选版式，避免一份作品视觉语言漂移。
        return candidates[0]

    @staticmethod
    def _requested_layout_kind(data: dict[str, Any]) -> str | None:
        """从显式版式或数字项语义中识别生产版特殊内容布局。"""
        explicit = data.get("layoutKind")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()
        items = data.get("items")
        if isinstance(items, list) and any(
            isinstance(item, dict) and item.get("kind") in {"metric", "number", "stat"}
            for item in items
        ):
            return "metrics"
        return None

    @staticmethod
    def _semantic_images(value: Any) -> list[dict[str, Any]]:
        """只接受具有明确地址的 Agent 图片，忽略不完整图片描述。"""
        if not isinstance(value, list):
            return []
        return [
            copy.deepcopy(image)
            for image in value
            if isinstance(image, dict)
            and isinstance(image.get("src"), str)
            and image["src"].strip()
        ]

    @classmethod
    def _fill_images(cls, elements: list[dict[str, Any]], images: list[dict[str, Any]]) -> None:
        """只把 Agent 配图写入内容图片槽，避免覆盖背景和奖杯等装饰素材。"""
        image_slots = cls._image_slots(elements)
        for slot, source in zip(image_slots, images):
            slot["src"] = source["src"].strip()
            if isinstance(source.get("alt"), str) and source["alt"].strip():
                slot["alt"] = source["alt"].strip()

    @classmethod
    def _image_count(cls, slide: dict[str, Any]) -> int:
        elements = slide.get("elements") if isinstance(slide.get("elements"), list) else []
        return len(cls._image_slots(elements))

    @staticmethod
    def _image_slots(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """识别显式内容图片槽；未标注的历史模板继续沿用全部图片可替换的兼容行为。"""
        images = [element for element in elements if element.get("type") == "image"]
        # pageFigure/itemFigure 是历史PPTist分类，不代表“可替换/装饰”边界；
        # 只有新协议的 content/decoration 出现时才启用严格槽位模式。
        has_explicit_markers = any(
            element.get("imageType") in {"content", "decoration"}
            for element in images
        )
        if not has_explicit_markers:
            return images
        return [
            element for element in images
            if element.get("imageType") == "content"
        ]

    def _content_layout_score(self, slide: dict[str, Any], count: int) -> tuple[int, int]:
        item_slots = self._slot_count(slide, "item")
        content_slots = self._slot_count(slide, "content")
        if item_slots >= count:
            return (0, item_slots - count)
        # 多条内容优先保留独立要点结构；分页后正常不会选中容量不足的候选。
        if item_slots > 0:
            return (1, count - item_slots)
        if count == 1 and content_slots >= count:
            return (2, content_slots - count)
        if content_slots > 0:
            return (3, count - content_slots)
        return (4, count)

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
        fallback_text = self._text(data.get("text"))
        if (items or fallback_text) and not content_slots:
            raise TemplateRenderError("模板缺少内容槽位", code="TEMPLATE_MISSING_SLOT")
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
            body = fallback_text
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
        # 部分历史模板只依赖编辑器默认字号；渲染时必须显式补入字号，才能可靠计算容量。
        original = max(sizes) if sizes else self._DEFAULT_FONT_SIZE
        width = self._number(element.get("width"), 300)
        height = self._number(
            element.get("height"),
            original * max_lines * self._LINE_HEIGHT + self._TEXT_PADDING,
        )
        adapted = max(original, self._MINIMUM_READABLE_FONT_SIZE)
        while adapted > self._MINIMUM_READABLE_FONT_SIZE:
            if self._estimated_text_height(value, width, adapted) <= height:
                break
            adapted = max(self._MINIMUM_READABLE_FONT_SIZE, adapted - 0.5)
        adapted = round(adapted, 1)
        replaced = False
        for node in root.iter():
            style = node.get("style")
            if style and re.search(r"font-size\s*:\s*[0-9.]+px", style):
                node.set("style", re.sub(r"font-size\s*:\s*[0-9.]+px", f"font-size: {adapted}px", style))
                replaced = True
        if replaced:
            return

        # 没有字号声明时写到首个段落或 span，避免前端继续使用不可控的继承字号。
        target = next(
            (node for node in root.iterdescendants() if node.tag in {"p", "span"}),
            root,
        )
        style = target.get("style", "").strip()
        separator = "" if not style or style.endswith(";") else ";"
        target.set("style", f"{style}{separator} font-size: {adapted}px;".strip())

    def _validate_slide_text_bounds(self, slide: dict[str, Any], slide_height: float) -> None:
        """按前端排版规则估算语义文本高度，阻止明显越过页面底部的文档落库。"""
        elements = slide.get("elements") if isinstance(slide.get("elements"), list) else []
        for element in elements:
            if self._slot_type(element) is None:
                continue
            raw = self._element_text_html(element)
            if not raw:
                continue
            font_sizes = [
                float(value)
                for value in re.findall(r"font-size\s*:\s*([0-9.]+)px", raw)
            ]
            font_size = max(font_sizes, default=self._DEFAULT_FONT_SIZE)
            lines = [
                html.unescape(re.sub(r"<[^>]+>", "", part))
                for part in re.split(r"<br\s*/?>", raw, flags=re.IGNORECASE)
            ]
            plain_text = "\n".join(lines)
            estimated_height = self._estimated_text_height(
                plain_text,
                self._number(element.get("width"), 0),
                font_size,
            )
            declared_height = self._number(element.get("height"), 0)
            top = self._number(element.get("top"), 0)
            if estimated_height > declared_height + 1:
                raise TemplateRenderError(
                    "生成内容超出模板文本框容量",
                    code="TEMPLATE_TEXT_OVERFLOW",
                    context={
                        "slide_type": str(slide.get("type") or "unknown")[:32],
                        "layout_kind": str(slide.get("layoutKind") or "default")[:64],
                        "slot_type": str(self._slot_type(element) or "unknown")[:32],
                        "text_length": str(len(plain_text)),
                        "font_size": str(font_size),
                        "width": str(self._number(element.get("width"), 0)),
                        "height": str(declared_height),
                    },
                )
            if top + declared_height > slide_height + 1:
                raise TemplateRenderError(
                    "生成内容超出幻灯片页面边界",
                    code="TEMPLATE_TEXT_OVERFLOW",
                    context={
                        "slide_type": str(slide.get("type") or "unknown")[:32],
                        "layout_kind": str(slide.get("layoutKind") or "default")[:64],
                        "slot_type": str(self._slot_type(element) or "unknown")[:32],
                        "text_length": str(len(plain_text)),
                        "font_size": str(font_size),
                        "width": str(self._number(element.get("width"), 0)),
                        "height": str(declared_height),
                    },
                )

    @classmethod
    def _wrapped_line_count(cls, value: str, width: float, font_size: float) -> int:
        """按统一中英文宽度模型估算浏览器换行数。"""
        usable_width = max(1.0, width - cls._TEXT_PADDING)
        weighted_per_line = max(
            1.0,
            usable_width / font_size * cls._WIDTH_SAFETY_FACTOR,
        )
        return sum(
            max(1, math.ceil(cls._weighted_length(line) / weighted_per_line))
            for line in (value.splitlines() or [value])
        )

    @classmethod
    def _estimated_text_height(cls, value: str, width: float, font_size: float) -> float:
        """按前端内边距与行高估算文本元素的真实高度。"""
        return (
            cls._wrapped_line_count(value, width, font_size)
            * font_size
            * cls._LINE_HEIGHT
            + cls._TEXT_PADDING
        )

    @classmethod
    def _weighted_length(cls, value: str) -> float:
        """中文按全宽、ASCII 按约半宽计算显示长度。"""
        return sum(cls._character_weight(char) for char in value)

    @staticmethod
    def _character_weight(char: str) -> float:
        """返回单个字符的近似显示宽度权重，供分页与边界校验统一使用。"""
        return 1.0 if ord(char) > 255 else 0.56

    @staticmethod
    def _element_text_html(element: dict[str, Any]) -> str:
        """统一读取文本元素与带文字形状的 HTML 内容。"""
        if element.get("type") == "text" and isinstance(element.get("content"), str):
            return element["content"]
        text = element.get("text")
        if isinstance(text, dict) and isinstance(text.get("content"), str):
            return text["content"]
        return ""

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

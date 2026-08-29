#!/usr/bin/env python3
"""只读验证 PPTist 模板 JSON 的结构、库存、ID、槽位和路径。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONTRACT = 2
EXIT_ENVIRONMENT = 4
SAFE_TEMPLATE_ID = re.compile(r"^template_[1-9][0-9]*$")
DEFAULT_PAGE_TYPES = {"cover", "contents", "transition", "content", "end"}
FORBIDDEN_TEXT = (
    "lorem ipsum", "点击添加", "xxx", "file://", "data:image", ".codex-tmp",
    ".codex_tmp", "../", "..\\", "c:\\users\\", "/users/", "/home/",
)


def _emit(status: str, errors: list[str], warnings: list[str], details: dict[str, Any]) -> None:
    print(json.dumps({
        "script": "validate-template-json",
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }, ensure_ascii=False, indent=2))


def _resolve(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    return (candidate if candidate.is_absolute() else root / candidate).resolve()


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PY_YAML_MISSING") from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读验证 TrainPPTAgent 生产模板 JSON。")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--template-json", required=True)
    parser.add_argument("--spec", help="可选 READY_FOR_BUILD 规格，用于精确库存和画布校验")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"template_id": args.template_id}
    try:
        root = Path(args.project_root).resolve()
        template_path = _resolve(root, args.template_json)
        if not SAFE_TEMPLATE_ID.fullmatch(args.template_id):
            errors.append("模板 ID 必须匹配 template_<正整数>")
        if not template_path.is_file():
            errors.append("模板 JSON 不存在")
            _emit("FAIL", errors, warnings, details)
            return EXIT_CONTRACT
        try:
            template = json.loads(template_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _emit("FAIL", ["模板文件不是有效的 UTF-8 JSON"], warnings, details)
            return EXIT_CONTRACT
        if not isinstance(template, dict):
            _emit("FAIL", ["模板 JSON 顶层必须是对象"], warnings, details)
            return EXIT_CONTRACT

        if template.get("id") != args.template_id:
            errors.append("模板 JSON 的 id 与参数不一致")
        if not isinstance(template.get("title"), str) or not template.get("title", "").strip():
            errors.append("模板缺少可读 title")
        for key in ("width", "height"):
            value = template.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                errors.append(f"模板 {key} 必须为正数")
        if not isinstance(template.get("theme"), dict):
            errors.append("模板 theme 必须是对象")
        slides = template.get("slides")
        if not isinstance(slides, list) or not slides:
            errors.append("模板 slides 必须是非空数组")
            slides = []

        spec: dict[str, Any] = {}
        if args.spec:
            spec_path = _resolve(root, args.spec)
            if not spec_path.is_file():
                errors.append("规格文件不存在")
            else:
                spec = _load_yaml(spec_path)
                if spec.get("spec_version") != 1:
                    errors.append("仅支持 spec_version: 1")
                spec_template = spec.get("template") if isinstance(spec.get("template"), dict) else {}
                if spec_template.get("id") != args.template_id:
                    errors.append("规格 template.id 与参数不一致")
                canvas = spec_template.get("canvas") if isinstance(spec_template.get("canvas"), dict) else {}
                for key in ("width", "height"):
                    if key in canvas and template.get(key) != canvas.get(key):
                        errors.append(f"模板画布 {key} 与规格不一致")

        semantics = spec.get("semantics") if isinstance(spec.get("semantics"), dict) else {}
        declared_types = semantics.get("page_types")
        allowed_types = set(declared_types) if isinstance(declared_types, list) and declared_types else DEFAULT_PAGE_TYPES
        slide_ids: list[str] = []
        element_ids: list[str] = []
        referenced_assets: set[str] = set()
        image_roles = Counter()
        page_types = Counter()
        text_slots = Counter()

        for slide_index, slide in enumerate(slides):
            if not isinstance(slide, dict):
                errors.append(f"第 {slide_index + 1} 页不是对象")
                continue
            slide_id = slide.get("id")
            if not isinstance(slide_id, str) or not slide_id.strip():
                errors.append(f"第 {slide_index + 1} 页缺少 id")
            else:
                slide_ids.append(slide_id)
            slide_type = slide.get("type")
            if not isinstance(slide_type, str) or slide_type not in allowed_types:
                errors.append(f"页面 {slide_id or slide_index + 1} 的 type 未在规格中声明")
            else:
                page_types[slide_type] += 1
            elements = slide.get("elements")
            if not isinstance(elements, list):
                errors.append(f"页面 {slide_id or slide_index + 1} 的 elements 必须是数组")
                continue
            for element_index, element in enumerate(elements):
                if not isinstance(element, dict):
                    errors.append(f"页面 {slide_id or slide_index + 1} 存在非对象元素")
                    continue
                element_id = element.get("id")
                if not isinstance(element_id, str) or not element_id.strip():
                    errors.append(f"页面 {slide_id or slide_index + 1} 的第 {element_index + 1} 个元素缺少 id")
                else:
                    element_ids.append(element_id)
                if isinstance(element.get("textType"), str):
                    text_slots[element["textType"]] += 1
                if element.get("type") == "image":
                    role = element.get("imageType")
                    if role not in {"content", "decoration"}:
                        errors.append(f"图片元素 {element_id or element_index + 1} 缺少合法 imageType")
                    else:
                        image_roles[role] += 1
                    source = element.get("src")
                    if not isinstance(source, str) or not source.startswith("/api/data/"):
                        errors.append(f"图片元素 {element_id or element_index + 1} 必须使用 /api/data/ 资源")
                    else:
                        filename = source.rsplit("/", 1)[-1]
                        if not filename or Path(filename).name != filename:
                            errors.append(f"图片元素 {element_id or element_index + 1} 的资源文件名不安全")
                        elif not filename.startswith(f"{args.template_id}_asset_"):
                            errors.append(f"图片元素 {element_id or element_index + 1} 引用了其他模板命名空间")
                        else:
                            referenced_assets.add(filename)
                    if role == "content" and element.get("lock") is True:
                        errors.append(f"内容图片 {element_id or element_index + 1} 不应锁定")

        duplicate_slides = sorted(item for item, count in Counter(slide_ids).items() if count > 1)
        duplicate_elements = sorted(item for item, count in Counter(element_ids).items() if count > 1)
        if duplicate_slides:
            errors.append("页面 ID 不唯一")
        if duplicate_elements:
            errors.append("元素 ID 不唯一")

        metadata = template.get("metadata") if isinstance(template.get("metadata"), dict) else {}
        mvp_ids = metadata.get("mvpSlideIds")
        if not isinstance(mvp_ids, list) or not mvp_ids:
            errors.append("metadata.mvpSlideIds 必须是非空数组")
            mvp_ids = []
        if len(mvp_ids) != len(set(mvp_ids)):
            errors.append("metadata.mvpSlideIds 存在重复")
        missing_mvp = sorted(set(mvp_ids) - set(slide_ids))
        if missing_mvp:
            errors.append("metadata.mvpSlideIds 引用了不存在的页面")

        if spec:
            pages = spec.get("pages") if isinstance(spec.get("pages"), dict) else {}
            production = pages.get("production") if isinstance(pages.get("production"), dict) else {}
            expected_inventory = production.get("inventory")
            if isinstance(expected_inventory, dict):
                normalized_expected = {str(key): int(value) for key, value in expected_inventory.items()}
                if dict(page_types) != normalized_expected:
                    errors.append("生产页面库存与规格不一致")
            mvp = pages.get("mvp") if isinstance(pages.get("mvp"), dict) else {}
            expected_mvp_ids = mvp.get("slide_ids")
            if isinstance(expected_mvp_ids, list) and set(expected_mvp_ids) != set(mvp_ids):
                errors.append("MVP 页面集合与规格不一致")

        serialized = json.dumps(template, ensure_ascii=False).lower()
        forbidden_hits = sorted(value for value in FORBIDDEN_TEXT if value in serialized)
        if forbidden_hits:
            errors.append("模板包含占位文本、临时路径或内联图片")
        # 防止模板通过旧命名空间间接引用其他已存在资源。
        old_namespace = re.findall(r"template_[1-9][0-9]*_asset_", serialized)
        unexpected_namespaces = sorted(set(old_namespace) - {f"{args.template_id}_asset_"})
        if unexpected_namespaces:
            errors.append("模板包含其他模板的资源命名空间")

        details.update({
            "slides": len(slides),
            "elements": len(element_ids),
            "page_types": dict(page_types),
            "mvp_slides": len(mvp_ids),
            "text_slots": dict(text_slots),
            "image_roles": dict(image_roles),
            "referenced_assets": sorted(referenced_assets),
            "duplicate_slide_ids": duplicate_slides,
            "duplicate_element_ids": duplicate_elements,
            "forbidden_hits": forbidden_hits,
        })
        if not text_slots:
            warnings.append("模板未发现 textType 语义槽位")
        if errors:
            _emit("FAIL", errors, warnings, details)
            return EXIT_CONTRACT
        _emit("PASS", [], warnings, details)
        return EXIT_OK
    except RuntimeError as exc:
        if str(exc) == "PY_YAML_MISSING":
            _emit("INCONCLUSIVE", ["项目解释器缺少 PyYAML"], warnings, details)
            return EXIT_ENVIRONMENT
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"脚本异常：{type(exc).__name__}", file=sys.stderr)
        _emit("ERROR", ["脚本执行发生未知错误"], warnings, details)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

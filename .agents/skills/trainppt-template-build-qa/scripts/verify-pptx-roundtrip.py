#!/usr/bin/env python3
"""只读验证 PPTX 包结构、页数和可选的产品重导入摘要。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONTRACT = 2
EXIT_ENVIRONMENT = 4


def _emit(status: str, errors: list[str], warnings: list[str], details: dict[str, Any]) -> None:
    print(json.dumps({
        "script": "verify-pptx-roundtrip",
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }, ensure_ascii=False, indent=2))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_slides(value: Any) -> list[Any] | None:
    if isinstance(value, dict) and isinstance(value.get("slides"), list):
        return value["slides"]
    if isinstance(value, dict) and isinstance(value.get("data"), dict):
        slides = value["data"].get("slides")
        return slides if isinstance(slides, list) else None
    return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读验证 PPTX 和产品解析摘要。")
    parser.add_argument("--pptx", required=True, help="待验证 PPTX 路径")
    parser.add_argument("--expected-slides", type=int, help="预期页数")
    parser.add_argument("--roundtrip-json", help="产品 pptxtojson 或重导入导出的 JSON 摘要")
    parser.add_argument(
        "--require-product-roundtrip",
        action="store_true",
        help="要求提供产品解析 JSON；否则只验证标准 PPTX 包",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {}
    try:
        try:
            from pptx import Presentation
        except ImportError:
            _emit("INCONCLUSIVE", ["项目解释器缺少 python-pptx"], warnings, details)
            return EXIT_ENVIRONMENT

        pptx_path = Path(args.pptx).resolve()
        if not pptx_path.is_file():
            _emit("FAIL", ["PPTX 文件不存在"], warnings, details)
            return EXIT_CONTRACT
        if pptx_path.suffix.lower() != ".pptx":
            errors.append("文件扩展名必须是 .pptx")

        try:
            with zipfile.ZipFile(pptx_path) as archive:
                bad_member = archive.testzip()
                names = set(archive.namelist())
                required = {"[Content_Types].xml", "ppt/presentation.xml"}
                if bad_member:
                    errors.append("PPTX ZIP 中存在损坏成员")
                if not required.issubset(names):
                    errors.append("PPTX 缺少核心 OOXML 部件")
                slide_parts = sorted(
                    name for name in names
                    if re.fullmatch(r"ppt/slides/slide[1-9][0-9]*\.xml", name)
                )
        except zipfile.BadZipFile:
            _emit("FAIL", ["文件不是有效的 PPTX ZIP 包"], warnings, details)
            return EXIT_CONTRACT

        try:
            presentation = Presentation(str(pptx_path))
            slide_count = len(presentation.slides)
        except Exception:  # noqa: BLE001 - python-pptx 的解析异常统一映射为契约失败。
            _emit("FAIL", ["python-pptx 无法解析该文件"], warnings, details)
            return EXIT_CONTRACT

        if slide_count <= 0:
            errors.append("PPTX 不包含页面")
        if len(slide_parts) != slide_count:
            errors.append("PPTX 页面部件数与 presentation.xml 解析结果不一致")
        if args.expected_slides is not None:
            if args.expected_slides <= 0:
                errors.append("expected-slides 必须为正整数")
            elif slide_count != args.expected_slides:
                errors.append("PPTX 页数与预期不一致")

        product_roundtrip = {
            "provided": False,
            "parsed": False,
            "slides": None,
            "editable_elements": 0,
        }
        if args.roundtrip_json:
            roundtrip_path = Path(args.roundtrip_json).resolve()
            if not roundtrip_path.is_file():
                errors.append("产品重导入 JSON 不存在")
            else:
                product_roundtrip["provided"] = True
                try:
                    value = json.loads(roundtrip_path.read_text(encoding="utf-8"))
                    slides = _extract_slides(value)
                    if slides is None:
                        errors.append("产品重导入 JSON 缺少 slides 数组")
                    else:
                        product_roundtrip["parsed"] = True
                        product_roundtrip["slides"] = len(slides)
                        if len(slides) != slide_count:
                            errors.append("产品重导入页数与 PPTX 不一致")
                        editable = 0
                        for slide in slides:
                            if not isinstance(slide, dict):
                                continue
                            elements = slide.get("elements")
                            if isinstance(elements, list):
                                editable += sum(
                                    isinstance(element, dict) and element.get("type") in {"text", "image", "shape"}
                                    for element in elements
                                )
                        product_roundtrip["editable_elements"] = editable
                        if editable <= 0:
                            errors.append("产品重导入结果没有可编辑元素")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    errors.append("产品重导入 JSON 无法解析")
        elif args.require_product_roundtrip:
            errors.append("要求产品往返时必须提供 --roundtrip-json")
        else:
            warnings.append("未提供产品重导入 JSON；本次只证明标准 PPTX 包可解析")

        details.update({
            "bytes": pptx_path.stat().st_size,
            "sha256": _sha256(pptx_path),
            "slides": slide_count,
            "slide_parts": len(slide_parts),
            "structure_valid": not errors,
            "product_roundtrip": product_roundtrip,
        })
        if errors:
            _emit("FAIL", errors, warnings, details)
            return EXIT_CONTRACT
        _emit("PASS", [], warnings, details)
        return EXIT_OK
    except OSError as exc:
        print(f"环境文件错误：{type(exc).__name__}", file=sys.stderr)
        _emit("INCONCLUSIVE", ["环境无法读取 PPTX 或重导入文件"], warnings, details)
        return EXIT_ENVIRONMENT
    except Exception as exc:  # noqa: BLE001
        print(f"脚本异常：{type(exc).__name__}", file=sys.stderr)
        _emit("ERROR", ["脚本执行发生未知错误"], warnings, details)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

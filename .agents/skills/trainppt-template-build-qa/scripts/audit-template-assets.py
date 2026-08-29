#!/usr/bin/env python3
"""只读审计模板素材引用、尺寸、模式、Alpha、体积与哈希。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONTRACT = 2
EXIT_ENVIRONMENT = 4
SAFE_TEMPLATE_ID = re.compile(r"^template_[1-9][0-9]*$")


def _emit(status: str, errors: list[str], warnings: list[str], details: dict[str, Any]) -> None:
    print(json.dumps({
        "script": "audit-template-assets",
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }, ensure_ascii=False, indent=2))


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读审计 TrainPPTAgent 模板发布素材。")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--template-json", required=True)
    parser.add_argument("--spec", help="可选规格，用于逐项校验 manifest")
    parser.add_argument("--template-dir", default="backend/main_api/template")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"template_id": args.template_id, "assets": {}}
    try:
        try:
            from PIL import Image, UnidentifiedImageError
        except ImportError:
            _emit("INCONCLUSIVE", ["项目解释器缺少 Pillow"], warnings, details)
            return EXIT_ENVIRONMENT

        root = Path(args.project_root).resolve()
        template_dir = _resolve(root, args.template_dir)
        template_path = _resolve(root, args.template_json)
        if not SAFE_TEMPLATE_ID.fullmatch(args.template_id):
            errors.append("模板 ID 必须匹配 template_<正整数>")
        if not template_dir.is_dir():
            errors.append("模板目录不存在")
        if not template_path.is_file():
            errors.append("模板 JSON 不存在")
        if errors:
            _emit("FAIL", errors, warnings, details)
            return EXIT_CONTRACT

        template = json.loads(template_path.read_text(encoding="utf-8"))
        if not isinstance(template, dict) or template.get("id") != args.template_id:
            errors.append("模板 JSON 顶层或 id 无效")
            _emit("FAIL", errors, warnings, details)
            return EXIT_CONTRACT

        referenced: set[str] = set()
        for slide in template.get("slides", []):
            if not isinstance(slide, dict):
                continue
            for element in slide.get("elements", []):
                if not isinstance(element, dict) or element.get("type") != "image":
                    continue
                source = element.get("src")
                if not isinstance(source, str) or not source.startswith("/api/data/"):
                    errors.append("模板存在非 /api/data/ 图片引用")
                    continue
                filename = source.rsplit("/", 1)[-1]
                if Path(filename).name != filename or not filename.startswith(f"{args.template_id}_asset_"):
                    errors.append("模板存在不安全或跨命名空间的素材引用")
                    continue
                referenced.add(filename)

        published = {
            path.name for path in template_dir.glob(f"{args.template_id}_asset_*")
            if path.is_file()
        }
        missing = sorted(referenced - published)
        orphaned = sorted(published - referenced)
        if missing:
            errors.append("模板引用了不存在的发布素材")
        if orphaned:
            errors.append("发布目录存在目标模板孤立素材")

        spec: dict[str, Any] = {}
        manifest: dict[str, dict[str, Any]] = {}
        if args.spec:
            try:
                import yaml  # type: ignore
            except ImportError:
                _emit("INCONCLUSIVE", ["项目解释器缺少 PyYAML"], warnings, details)
                return EXIT_ENVIRONMENT
            spec_path = _resolve(root, args.spec)
            if not spec_path.is_file():
                errors.append("规格文件不存在")
            else:
                loaded = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
                spec = loaded if isinstance(loaded, dict) else {}
                items = spec.get("assets", {}).get("items") if isinstance(spec.get("assets"), dict) else None
                if not isinstance(items, list) or not items:
                    errors.append("规格 assets.items 必须是非空数组")
                else:
                    for item in items:
                        if not isinstance(item, dict) or not isinstance(item.get("filename"), str):
                            errors.append("素材 manifest 项缺少 filename")
                            continue
                        filename = item["filename"]
                        if filename in manifest:
                            errors.append("素材 manifest 文件名重复")
                        manifest[filename] = item
                    if set(manifest) != referenced:
                        errors.append("素材 manifest 与模板引用集合不一致")

        for filename in sorted(published | referenced):
            path = (template_dir / filename).resolve()
            if path.parent != template_dir or not path.is_file():
                continue
            record: dict[str, Any] = {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            item = manifest.get(filename, {})
            try:
                with Image.open(path) as image:
                    image.load()
                    record["size"] = [image.width, image.height]
                    record["mode"] = image.mode
                    record["format"] = image.format
                    alpha_extrema: list[int] | None = None
                    if "A" in image.getbands():
                        low, high = image.getchannel("A").getextrema()
                        alpha_extrema = [int(low), int(high)]
                    elif image.mode == "P" and "transparency" in image.info:
                        alpha_extrema = [0, 255]
                    record["alpha"] = alpha_extrema
            except (OSError, UnidentifiedImageError):
                errors.append(f"素材 {filename} 不是可解码图片")
                details["assets"][filename] = record
                continue

            dimensions = item.get("dimensions")
            if isinstance(dimensions, list) and len(dimensions) == 2:
                if record.get("size") != [int(dimensions[0]), int(dimensions[1])]:
                    errors.append(f"素材 {filename} 尺寸与规格不一致")
            expected_format = item.get("format")
            if isinstance(expected_format, str) and record.get("format", "").upper() != expected_format.upper():
                errors.append(f"素材 {filename} 格式与规格不一致")
            max_bytes = item.get("max_bytes")
            if isinstance(max_bytes, int) and not isinstance(max_bytes, bool) and record["bytes"] > max_bytes:
                errors.append(f"素材 {filename} 超过体积上限")
            if item.get("alpha_required") is True:
                alpha = record.get("alpha")
                if not isinstance(alpha, list) or alpha[0] >= 255:
                    errors.append(f"素材 {filename} 缺少真实透明像素")
            expected_hash = item.get("sha256")
            if isinstance(expected_hash, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
                if record["sha256"].lower() != expected_hash.lower():
                    errors.append(f"素材 {filename} SHA-256 与规格不一致")
            details["assets"][filename] = record

        cover_path = template_dir / f"{args.template_id}.jpg"
        cover_record: dict[str, Any] = {"exists": cover_path.is_file()}
        if not cover_path.is_file():
            errors.append("模板封面不存在")
        else:
            try:
                with Image.open(cover_path) as cover:
                    cover.load()
                    cover_record.update({
                        "size": [cover.width, cover.height],
                        "mode": cover.mode,
                        "format": cover.format,
                        "bytes": cover_path.stat().st_size,
                        "sha256": _sha256(cover_path),
                    })
                cover_spec = spec.get("template", {}).get("cover") if isinstance(spec.get("template"), dict) else None
                if isinstance(cover_spec, dict):
                    expected_size = [cover_spec.get("width"), cover_spec.get("height")]
                    if all(isinstance(value, (int, float)) for value in expected_size):
                        if cover_record.get("size") != [int(expected_size[0]), int(expected_size[1])]:
                            errors.append("模板封面尺寸与规格不一致")
                if cover_record.get("format") != "JPEG" or cover_record.get("mode") != "RGB":
                    errors.append("模板封面必须为 RGB JPEG")
            except (OSError, UnidentifiedImageError):
                errors.append("模板封面不是可解码图片")
        details.update({
            "referenced": sorted(referenced),
            "published": sorted(published),
            "missing": missing,
            "orphaned": orphaned,
            "cover": cover_record,
        })
        if not referenced:
            warnings.append("模板未引用外置素材")
        if errors:
            _emit("FAIL", errors, warnings, details)
            return EXIT_CONTRACT
        _emit("PASS", [], warnings, details)
        return EXIT_OK
    except (UnicodeDecodeError, json.JSONDecodeError):
        _emit("FAIL", ["模板或规格不是有效的 UTF-8 JSON/YAML"], warnings, details)
        return EXIT_CONTRACT
    except Exception as exc:  # noqa: BLE001
        print(f"脚本异常：{type(exc).__name__}", file=sys.stderr)
        _emit("ERROR", ["脚本执行发生未知错误"], warnings, details)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

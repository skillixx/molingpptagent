#!/usr/bin/env python3
"""只读检查参考 PPTX，并输出可供模板规划使用的结构化摘要。"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET


EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_CONTRACT = 2

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".svg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".wma", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".wmv", ".m4v", ".webm", ".mpeg", ".mpg"}

# Windows 控制台可能默认使用 GBK；机器可读 JSON 始终以 UTF-8 输出。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class ContractError(Exception):
    """表示输入文件或 OOXML 契约不满足。"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读提取参考 PPTX 的页面、字体和媒体结构。")
    parser.add_argument("--input", required=True, type=Path, help="参考 PPTX 文件路径。")
    parser.add_argument("--output", type=Path, help="可选 JSON 输出路径；未指定时不写文件。")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def natural_key(value: str) -> list[Any]:
    """让 slide2 排在 slide10 前，避免字典序误导页面顺序。"""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def read_xml(archive: zipfile.ZipFile, member: str) -> ET.Element:
    try:
        return ET.fromstring(archive.read(member))
    except KeyError as exc:
        raise ContractError(f"PPTX 缺少必需部件：{member}") from exc
    except ET.ParseError as exc:
        raise ContractError(f"XML 无法解析：{member}: {exc}") from exc


def resolve_target(source_member: str, target: str) -> str:
    """关系目标相对当前 OOXML 部件解析，统一为 ZIP 内正斜杠路径。"""
    base = str(PurePosixPath(source_member).parent)
    return posixpath.normpath(posixpath.join(base, target)).lstrip("/")


def read_relationships(archive: zipfile.ZipFile, source_member: str) -> dict[str, dict[str, str]]:
    source = PurePosixPath(source_member)
    rel_member = str(source.parent / "_rels" / f"{source.name}.rels")
    if rel_member not in archive.namelist():
        return {}

    root = read_xml(archive, rel_member)
    relationships: dict[str, dict[str, str]] = {}
    for relation in root.findall(f"{{{REL_NS}}}Relationship"):
        relation_id = relation.get("Id", "")
        target = relation.get("Target", "")
        target_mode = relation.get("TargetMode", "Internal")
        resolved = target if target_mode == "External" else resolve_target(source_member, target)
        relationships[relation_id] = {
            "type": relation.get("Type", ""),
            "target": resolved,
            "target_mode": target_mode,
        }
    return relationships


def ordered_slide_members(archive: zipfile.ZipFile) -> list[str]:
    presentation = read_xml(archive, "ppt/presentation.xml")
    relations = read_relationships(archive, "ppt/presentation.xml")
    members: list[str] = []
    for slide_id in presentation.findall(f".//{{{P_NS}}}sldId"):
        relation_id = slide_id.get(f"{{{R_NS}}}id")
        relation = relations.get(relation_id or "")
        if relation and relation["target"] in archive.namelist():
            members.append(relation["target"])

    if members:
        return members

    # 部分非标准生成器缺少关系顺序，退化为自然排序但保留警告。
    return sorted(
        [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)],
        key=natural_key,
    )


def classify_relation(relation_type: str, target: str) -> str:
    suffix = Path(target).suffix.lower()
    tail = relation_type.rsplit("/", 1)[-1].lower()
    if tail == "image" or suffix in IMAGE_EXTENSIONS:
        return "image"
    if tail == "chart":
        return "chart"
    if tail.startswith("diagram"):
        return "smartart"
    if tail in {"audio", "audiofile"} or suffix in AUDIO_EXTENSIONS:
        return "audio"
    if tail in {"video", "videofile"} or suffix in VIDEO_EXTENSIONS:
        return "video"
    if tail in {"oleobject", "package"} or target.startswith("ppt/embeddings/"):
        return "embedded_object"
    if tail == "notesslide":
        return "notes"
    if tail == "hyperlink":
        return "hyperlink"
    return "other"


def layout_hint(text_box_count: int, picture_count: int, table_count: int, chart_count: int) -> str:
    """仅按对象数量给出提示，不冒充渲染后的视觉判断。"""
    if chart_count or table_count:
        return "data-or-table"
    if picture_count >= 2 and text_box_count >= 2:
        return "multi-image-content"
    if picture_count == 1 and text_box_count >= 2:
        return "single-image-content"
    if picture_count == 0 and text_box_count <= 2:
        return "title-or-section"
    if picture_count == 0:
        return "text-content"
    return "mixed"


def inspect_slide(archive: zipfile.ZipFile, member: str, index: int) -> dict[str, Any]:
    root = read_xml(archive, member)
    text_values = [
        (node.text or "").strip()
        for node in root.findall(f".//{{{A_NS}}}t")
        if (node.text or "").strip()
    ]
    text_shapes = 0
    for shape in root.findall(f".//{{{P_NS}}}sp"):
        if shape.find(f".//{{{A_NS}}}t") is not None:
            text_shapes += 1

    relation_counts: Counter[str] = Counter()
    relation_targets: dict[str, list[str]] = {}
    for relation in read_relationships(archive, member).values():
        kind = classify_relation(relation["type"], relation["target"])
        relation_counts[kind] += 1
        relation_targets.setdefault(kind, []).append(relation["target"])

    picture_count = len(root.findall(f".//{{{P_NS}}}pic"))
    table_count = len(root.findall(f".//{{{A_NS}}}tbl"))
    chart_count = relation_counts["chart"]
    title = text_values[0][:160] if text_values else ""
    preview = " | ".join(text_values)[:500]

    return {
        "index": index,
        "member": member,
        "title_guess": title,
        "text_preview": preview,
        "text_runs": len(text_values),
        "text_characters": sum(len(value) for value in text_values),
        "text_shapes": text_shapes,
        "shapes": len(root.findall(f".//{{{P_NS}}}sp")),
        "groups": len(root.findall(f".//{{{P_NS}}}grpSp")),
        "pictures": picture_count,
        "tables": table_count,
        "relationship_counts": dict(sorted(relation_counts.items())),
        "relationship_targets": {key: sorted(value) for key, value in sorted(relation_targets.items())},
        "layout_hint": layout_hint(text_shapes, picture_count, table_count, chart_count),
        "layout_hint_is_heuristic": True,
    }


def collect_fonts(archive: zipfile.ZipFile) -> list[str]:
    fonts: set[str] = set()
    relevant_prefixes = ("ppt/slides/", "ppt/theme/", "ppt/slideMasters/", "ppt/slideLayouts/")
    for member in archive.namelist():
        if not member.endswith(".xml") or not member.startswith(relevant_prefixes):
            continue
        try:
            root = ET.fromstring(archive.read(member))
        except ET.ParseError:
            continue
        for node in root.iter():
            typeface = node.get("typeface")
            if typeface and typeface.strip() and not typeface.startswith("+"):
                fonts.add(typeface.strip())
    return sorted(fonts, key=str.casefold)


def media_inventory(archive: zipfile.ZipFile) -> dict[str, list[dict[str, Any]]]:
    inventory: dict[str, list[dict[str, Any]]] = {"images": [], "audio": [], "video": [], "other": []}
    for member in sorted((name for name in archive.namelist() if name.startswith("ppt/media/") and not name.endswith("/")), key=natural_key):
        suffix = Path(member).suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            bucket = "images"
        elif suffix in AUDIO_EXTENSIONS:
            bucket = "audio"
        elif suffix in VIDEO_EXTENSIONS:
            bucket = "video"
        else:
            bucket = "other"
        inventory[bucket].append({"member": member, "bytes": archive.getinfo(member).file_size, "extension": suffix})
    return inventory


def inspect_pptx(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ContractError(f"输入文件不存在或不是普通文件：{path}")
    if path.suffix.lower() != ".pptx":
        raise ContractError("输入文件扩展名必须是 .pptx。")

    try:
        archive = zipfile.ZipFile(path, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ContractError(f"输入文件不是有效 PPTX/ZIP：{exc}") from exc

    with archive:
        names = set(archive.namelist())
        required = {"[Content_Types].xml", "ppt/presentation.xml"}
        missing = sorted(required - names)
        if missing:
            raise ContractError(f"PPTX 缺少必需部件：{', '.join(missing)}")

        presentation = read_xml(archive, "ppt/presentation.xml")
        slide_size = presentation.find(f".//{{{P_NS}}}sldSz")
        cx = int(slide_size.get("cx", "0")) if slide_size is not None else 0
        cy = int(slide_size.get("cy", "0")) if slide_size is not None else 0
        slide_members = ordered_slide_members(archive)
        if not slide_members:
            raise ContractError("PPTX 不包含可读取的幻灯片。")

        slides = [inspect_slide(archive, member, index) for index, member in enumerate(slide_members, start=1)]
        media = media_inventory(archive)
        embedded = sorted(
            [
                {"member": name, "bytes": archive.getinfo(name).file_size}
                for name in names
                if name.startswith("ppt/embeddings/") and not name.endswith("/")
            ],
            key=lambda item: natural_key(item["member"]),
        )
        warnings: list[str] = []
        if not read_relationships(archive, "ppt/presentation.xml"):
            warnings.append("presentation 关系缺失，页面顺序使用文件名自然排序。")
        if not collect_fonts(archive):
            warnings.append("未发现显式字体名称；参考稿可能使用主题字体或生成器未写入字体属性。")

        return {
            "status": "PASS",
            "schema_version": 1,
            "input": {
                "path": str(path.resolve()),
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
            },
            "presentation": {
                "slide_count": len(slides),
                "size_emu": {"width": cx, "height": cy},
                "size_inches": {
                    "width": round(cx / 914400, 4) if cx else None,
                    "height": round(cy / 914400, 4) if cy else None,
                },
                "aspect_ratio": round(cx / cy, 6) if cx and cy else None,
                "notes_slide_count": len([name for name in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)]),
                "chart_part_count": len([name for name in names if re.fullmatch(r"ppt/charts/chart\d+\.xml", name)]),
                "smartart_part_count": len([name for name in names if name.startswith("ppt/diagrams/") and name.endswith(".xml")]),
                "embedded_object_count": len(embedded),
            },
            "fonts": collect_fonts(archive),
            "media": media,
            "embedded_objects": embedded,
            "slides": slides,
            "warnings": warnings,
        }


def emit(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)


def main() -> int:
    args = parse_args()
    try:
        emit(inspect_pptx(args.input), args.output)
        return EXIT_OK
    except ContractError as exc:
        print(f"输入或 PPTX 契约不满足：{exc}", file=sys.stderr)
        emit({"status": "FAIL", "error": {"code": "INPUT_OR_PPTX_CONTRACT", "message": str(exc)}}, args.output)
        return EXIT_CONTRACT
    except Exception as exc:  # pragma: no cover - 兜底仅用于保证机器可读失败输出
        print(f"脚本内部异常：{exc}", file=sys.stderr)
        emit({"status": "FAIL", "error": {"code": "INTERNAL_ERROR", "message": str(exc)}}, args.output)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())

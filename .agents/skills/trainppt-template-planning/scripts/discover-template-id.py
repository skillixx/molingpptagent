#!/usr/bin/env python3
"""联合扫描注册、模板文件、素材和专项测试，提出未冲突的模板候选 ID。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_CONTRACT = 2

TEMPLATE_ID_RE = re.compile(r"^template_([1-9]\d*)$")
REGISTRATION_RE = re.compile(r"[\"']id[\"']\s*:\s*[\"'](template_[1-9]\d*)[\"']")
FILE_ID_RE = re.compile(r"^template_([1-9]\d*)(?:$|[._])")
TEST_ID_RE = re.compile(r"^test_template_([1-9]\d*)\.py$")

# Windows 控制台可能默认使用 GBK；机器可读 JSON 始终以 UTF-8 输出。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class ContractError(Exception):
    """表示项目结构或候选 ID 不满足输入契约。"""

    def __init__(self, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="扫描 TrainPPTAgent 当前模板占用情况并提出候选 ID。")
    parser.add_argument("--project-root", required=True, type=Path, help="TrainPPTAgent 项目根目录。")
    parser.add_argument("--registration-file", default="backend/main_api/main.py", help="相对项目根目录的注册文件。")
    parser.add_argument("--template-dir", default="backend/main_api/template", help="相对项目根目录的模板目录。")
    parser.add_argument("--tests-dir", default="backend/main_api/tests", help="相对项目根目录的测试目录。")
    parser.add_argument("--minimum", type=int, default=1, help="候选编号最小值，默认 1。")
    parser.add_argument("--count", type=int, default=5, help="返回候选 ID 数量，默认 5。")
    parser.add_argument("--candidate", help="可选：验证指定 template_<N> 是否冲突。")
    parser.add_argument("--reserved", nargs="*", default=[], help="额外保留的模板 ID，可用空格或逗号分隔。")
    parser.add_argument("--output", type=Path, help="可选 JSON 输出路径；未指定时不写文件。")
    return parser.parse_args()


def parse_template_id(value: str) -> int:
    match = TEMPLATE_ID_RE.fullmatch(value.strip())
    if not match:
        raise ContractError(f"模板 ID 必须匹配 template_<正整数>：{value}")
    return int(match.group(1))


def relative_display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def add_source(sources: dict[int, list[dict[str, str]]], number: int, kind: str, path: Path, root: Path, detail: str = "") -> None:
    item = {"kind": kind, "path": relative_display(path, root)}
    if detail:
        item["detail"] = detail
    if item not in sources[number]:
        sources[number].append(item)


def scan_registration(path: Path, root: Path, sources: dict[int, list[dict[str, str]]], reserved: set[int]) -> list[str]:
    warnings: list[str] = []
    if not path.exists():
        warnings.append(f"注册文件不存在：{relative_display(path, root)}")
        return warnings

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="utf-8-sig").splitlines()

    for line_number, line in enumerate(lines, start=1):
        for match in REGISTRATION_RE.finditer(line):
            template_id = match.group(1)
            number = parse_template_id(template_id)
            # 注释中的注册项仍代表显式保留意图，候选选择必须避开。
            commented = line.lstrip().startswith("#")
            kind = "registration_commented" if commented else "registration_active"
            add_source(sources, number, kind, path, root, f"line {line_number}")
            if commented:
                reserved.add(number)
    return warnings


def scan_template_directory(path: Path, root: Path, sources: dict[int, list[dict[str, str]]]) -> list[str]:
    warnings: list[str] = []
    if not path.is_dir():
        warnings.append(f"模板目录不存在：{relative_display(path, root)}")
        return warnings

    for entry in path.iterdir():
        if not entry.is_file():
            continue
        match = FILE_ID_RE.match(entry.name)
        if not match:
            continue
        number = int(match.group(1))
        lower = entry.name.lower()
        if re.fullmatch(rf"template_{number}\.json", lower):
            kind = "template_json"
        elif re.fullmatch(rf"template_{number}\.(?:jpg|jpeg|png|webp)", lower):
            kind = "cover"
        elif lower.startswith(f"template_{number}_asset_"):
            kind = "asset"
        else:
            kind = "template_related_file"
        add_source(sources, number, kind, entry, root)
    return warnings


def scan_tests(path: Path, root: Path, sources: dict[int, list[dict[str, str]]]) -> list[str]:
    warnings: list[str] = []
    if not path.is_dir():
        warnings.append(f"测试目录不存在：{relative_display(path, root)}")
        return warnings

    for entry in path.iterdir():
        if not entry.is_file():
            continue
        match = TEST_ID_RE.fullmatch(entry.name)
        if match:
            add_source(sources, int(match.group(1)), "specialized_test", entry, root)
    return warnings


def parse_reserved(values: list[str]) -> set[int]:
    reserved: set[int] = set()
    for raw in values:
        for value in raw.split(","):
            value = value.strip()
            if value:
                reserved.add(parse_template_id(value))
    return reserved


def discover(args: argparse.Namespace) -> dict[str, Any]:
    root = args.project_root.resolve()
    if not root.is_dir():
        raise ContractError(f"项目根目录不存在：{root}")
    if args.minimum < 1:
        raise ContractError("--minimum 必须大于或等于 1。")
    if args.count < 1 or args.count > 100:
        raise ContractError("--count 必须在 1 到 100 之间。")

    registration_file = root / args.registration_file
    template_dir = root / args.template_dir
    tests_dir = root / args.tests_dir
    reserved = parse_reserved(args.reserved)
    explicit_reserved = set(reserved)
    sources: dict[int, list[dict[str, str]]] = defaultdict(list)
    warnings: list[str] = []
    warnings.extend(scan_registration(registration_file, root, sources, reserved))
    warnings.extend(scan_template_directory(template_dir, root, sources))
    warnings.extend(scan_tests(tests_dir, root, sources))

    if len(warnings) == 3:
        raise ContractError("注册文件、模板目录和测试目录均不可用，无法可靠发现候选 ID。", {"warnings": warnings})

    for number in explicit_reserved:
        add_source(sources, number, "explicit_reserved", root, root, "命令行 --reserved")

    unavailable = set(sources) | reserved
    candidates: list[str] = []
    number = args.minimum
    while len(candidates) < args.count:
        if number not in unavailable:
            candidates.append(f"template_{number}")
        number += 1

    occupied = [
        {
            "id": f"template_{number}",
            "number": number,
            "sources": sorted(items, key=lambda item: (item["kind"], item["path"], item.get("detail", ""))),
        }
        for number, items in sorted(sources.items())
    ]

    result: dict[str, Any] = {
        "status": "PASS",
        "schema_version": 1,
        "project_root": str(root),
        "scanned": {
            "registration_file": relative_display(registration_file, root),
            "template_dir": relative_display(template_dir, root),
            "tests_dir": relative_display(tests_dir, root),
        },
        "occupied": occupied,
        "reserved_ids": [f"template_{item}" for item in sorted(reserved)],
        "candidate_id": candidates[0],
        "candidate_status": "available_at_scan_time",
        "next_candidates": candidates,
        "warnings": warnings,
        "note": "候选 ID 不会被本脚本占用；实施开始前必须重新扫描。",
    }

    if args.candidate:
        candidate_number = parse_template_id(args.candidate)
        conflicts = sources.get(candidate_number, [])
        if candidate_number in reserved and not conflicts:
            conflicts = [{"kind": "reserved", "path": "", "detail": "保留编号"}]
        result["requested_candidate"] = args.candidate
        result["requested_candidate_available"] = not conflicts and candidate_number not in reserved
        result["requested_candidate_conflicts"] = conflicts
        if not result["requested_candidate_available"]:
            result["status"] = "FAIL"
            raise ContractError(f"指定候选 ID 已被占用或保留：{args.candidate}", result)
    return result


def emit(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)


def main() -> int:
    args = parse_args()
    try:
        emit(discover(args), args.output)
        return EXIT_OK
    except ContractError as exc:
        print(f"输入或模板 ID 契约不满足：{exc}", file=sys.stderr)
        payload = exc.payload or {"status": "FAIL"}
        payload.setdefault("status", "FAIL")
        payload["error"] = {"code": "INPUT_OR_ID_CONTRACT", "message": str(exc)}
        emit(payload, args.output)
        return EXIT_CONTRACT
    except Exception as exc:  # pragma: no cover - 兜底保证机器可读输出
        print(f"脚本内部异常：{exc}", file=sys.stderr)
        emit({"status": "FAIL", "error": {"code": "INTERNAL_ERROR", "message": str(exc)}}, args.output)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""将显式报告和 QA manifest 汇总为精简 evidence.json。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _qa_contract import evaluate_qa, find_sensitive, sanitize_qa_manifest


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONTRACT = 2
EXIT_PERMISSION = 3
SAFE_TEMPLATE_ID = re.compile(r"^template_[1-9][0-9]*$")
DEFAULT_CHECKS = (
    "development_spec", "template_json", "assets", "registration", "tests", "api", "pptx_roundtrip",
)


def _emit(status: str, errors: list[str], warnings: list[str], details: dict[str, Any]) -> None:
    print(json.dumps({
        "script": "collect-evidence",
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


def _safe_relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        # 外部参考文件只记录文件名，避免证据泄露用户本机目录。
        return path.name


def _parse_report(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError("--report 必须使用 name=path")
    name, path = value.split("=", 1)
    if name not in DEFAULT_CHECKS:
        raise ValueError(f"未知报告名称：{name}")
    if not path:
        raise ValueError("报告路径不能为空")
    return name, path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="汇总显式 QA 输入并写入限定 evidence.json。")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--template-json", required=True)
    parser.add_argument("--qa-manifest", help="真实 QA manifest；缺失时结论为 INCONCLUSIVE")
    parser.add_argument("--report", action="append", default=[], help="脚本报告，格式 name=path")
    parser.add_argument("--artifact", action="append", default=[], help="要记录哈希的截图或蒙太奇")
    parser.add_argument("--known-limitation", action="append", default=[])
    parser.add_argument("--output", required=True, help="必须位于 doc/assets/<template-id>_qa/")
    parser.add_argument("--force", action="store_true", help="显式允许覆盖已有 evidence.json")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"template_id": args.template_id}
    try:
        if not SAFE_TEMPLATE_ID.fullmatch(args.template_id):
            _emit("FAIL", ["模板 ID 必须匹配 template_<正整数>"], warnings, details)
            return EXIT_CONTRACT
        root = Path(args.project_root).resolve()
        spec_path = _resolve(root, args.spec)
        template_path = _resolve(root, args.template_json)
        output_path = _resolve(root, args.output)
        allowed_root = (root / "doc" / "assets" / f"{args.template_id}_qa").resolve()
        try:
            output_path.relative_to(allowed_root)
        except ValueError:
            _emit("BLOCKED", ["输出路径必须位于目标模板证据目录"], warnings, details)
            return EXIT_PERMISSION
        if output_path.name != "evidence.json":
            _emit("BLOCKED", ["第一版证据输出文件名必须为 evidence.json"], warnings, details)
            return EXIT_PERMISSION
        if output_path.exists() and not args.force:
            _emit("BLOCKED", ["证据文件已存在；需要显式 --force 才能覆盖"], warnings, details)
            return EXIT_PERMISSION
        if not spec_path.is_file() or not template_path.is_file():
            _emit("FAIL", ["规格或模板 JSON 不存在"], warnings, details)
            return EXIT_CONTRACT

        try:
            import yaml  # type: ignore
        except ImportError:
            _emit("INCONCLUSIVE", ["项目解释器缺少 PyYAML"], warnings, details)
            return 4
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        template = json.loads(template_path.read_text(encoding="utf-8"))
        if not isinstance(spec, dict) or not isinstance(template, dict):
            _emit("FAIL", ["规格或模板顶层不是对象"], warnings, details)
            return EXIT_CONTRACT
        if spec.get("status") != "READY_FOR_BUILD" or spec.get("spec_version") != 1:
            errors.append("规格必须为受支持的 READY_FOR_BUILD")
        if spec.get("template", {}).get("id") != args.template_id or template.get("id") != args.template_id:
            errors.append("规格、模板与参数 ID 不一致")

        reports: dict[str, Any] = {}
        for raw_report in args.report:
            name, value = _parse_report(raw_report)
            if name in reports:
                errors.append(f"报告重复：{name}")
                continue
            report_path = _resolve(root, value)
            if not report_path.is_file():
                warnings.append(f"报告缺失：{name}")
                continue
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                errors.append(f"报告无法解析：{name}")
                continue
            sensitive = find_sensitive(report)
            if sensitive:
                errors.append(f"报告包含敏感字段，拒绝写入：{name}")
                continue
            status = str(report.get("status", "INCONCLUSIVE")).upper() if isinstance(report, dict) else "INCONCLUSIVE"
            if status not in {"PASS", "FAIL", "INCONCLUSIVE"}:
                status = "FAIL" if status in {"ERROR", "BLOCKED"} else "INCONCLUSIVE"
            report_details = report.get("details") if isinstance(report, dict) and isinstance(report.get("details"), dict) else {}
            if name == "tests" and report_details.get("executed") is not True:
                status = "INCONCLUSIVE"
            summary: dict[str, Any] = {"script": report.get("script") if isinstance(report, dict) else None}
            # 只保留复核所需的精简字段，避免复制完整测试输出或业务正文。
            if name == "tests":
                summary.update({key: report_details.get(key) for key in ("executed", "exit_code", "duration_seconds", "scope", "tests")})
            elif name == "assets":
                summary.update({key: report_details.get(key) for key in ("assets", "cover", "missing", "orphaned")})
            elif name == "pptx_roundtrip":
                summary.update({key: report_details.get(key) for key in ("bytes", "sha256", "slides", "structure_valid", "product_roundtrip")})
            else:
                summary.update({key: report_details.get(key) for key in ("template_id", "spec_sha256", "slides", "elements", "page_types", "registration_count", "main_api", "frontend_proxy")})
            reports[name] = {
                "status": status,
                "source": _safe_relative(root, report_path),
                "sha256": _sha256(report_path),
                "summary": summary,
            }

        qa: dict[str, Any] = {}
        if args.qa_manifest:
            qa_path = _resolve(root, args.qa_manifest)
            if not qa_path.is_file():
                warnings.append("QA manifest 不存在")
            else:
                try:
                    loaded_qa = json.loads(qa_path.read_text(encoding="utf-8"))
                    if isinstance(loaded_qa, dict):
                        qa, qa_manifest_errors = sanitize_qa_manifest(loaded_qa)
                        errors.extend(qa_manifest_errors)
                    else:
                        errors.append("QA manifest 顶层必须是对象")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    errors.append("QA manifest 无法解析")
        else:
            warnings.append("未提供 QA manifest")

        artifact_records: list[dict[str, Any]] = []
        for raw_artifact in args.artifact:
            artifact_path = _resolve(root, raw_artifact)
            try:
                artifact_path.relative_to(root)
            except ValueError:
                errors.append("证据产物必须位于项目根目录内")
                continue
            if not artifact_path.is_file():
                errors.append("证据产物不存在")
                continue
            artifact_records.append({
                "path": _safe_relative(root, artifact_path),
                "bytes": artifact_path.stat().st_size,
                "sha256": _sha256(artifact_path),
            })

        page_types = Counter(
            slide.get("type") for slide in template.get("slides", [])
            if isinstance(slide, dict) and isinstance(slide.get("type"), str)
        )
        elements = sum(
            len(slide.get("elements", []))
            for slide in template.get("slides", [])
            if isinstance(slide, dict) and isinstance(slide.get("elements"), list)
        )
        reference_records: list[dict[str, Any]] = []
        for reference in spec.get("template", {}).get("reference_files", []):
            if isinstance(reference, dict):
                reference_records.append({
                    "path": Path(str(reference.get("path", ""))).name,
                    "sha256": reference.get("sha256"),
                })

        report_statuses = {name: reports.get(name, {}).get("status") for name in DEFAULT_CHECKS}
        explicit_report_fail = any(value == "FAIL" for value in report_statuses.values())
        missing_report = any(value != "PASS" for value in report_statuses.values())
        qa_status, qa_errors, qa_missing = evaluate_qa(qa, args.template_id)
        qa_issues = sorted(set(qa_errors + qa_missing))
        if errors or explicit_report_fail or qa_status == "FAIL":
            final_qa_status = "FAIL"
            implementation_status = "BLOCKED"
        elif missing_report or qa_status != "PASS":
            final_qa_status = "INCONCLUSIVE"
            implementation_status = "IN_PROGRESS"
        else:
            final_qa_status = "PASS"
            implementation_status = "READY_FOR_CONFIRMATION"

        evidence = {
            "evidence_schema_version": 1,
            "template_id": args.template_id,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "qa_status": final_qa_status,
            "implementation_status": implementation_status,
            "spec": {
                "path": _safe_relative(root, spec_path),
                "sha256": _sha256(spec_path),
                "reference_files": reference_records,
            },
            "implementation": {
                "template_json": {
                    "path": _safe_relative(root, template_path),
                    "bytes": template_path.stat().st_size,
                    "sha256": _sha256(template_path),
                },
                "page_types": dict(page_types),
                "slides": len(template.get("slides", [])),
                "elements": elements,
            },
            "checks": reports,
            "qa": qa,
            "artifacts": artifact_records,
            "known_limitations": list(dict.fromkeys(args.known_limitation)),
        }
        if find_sensitive(evidence):
            _emit("BLOCKED", ["汇总证据仍包含敏感字段"], warnings, details)
            return EXIT_PERMISSION

        # 输出目录与文件均由 --output 显式指定；临时文件也只创建在同一证据目录。
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        handle, temporary_name = tempfile.mkstemp(prefix=".evidence-", suffix=".tmp", dir=output_path.parent)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(encoded)
            os.replace(temporary_name, output_path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

        details.update({
            "output": _safe_relative(root, output_path),
            "output_sha256": _sha256(output_path),
            "qa_status": final_qa_status,
            "implementation_status": implementation_status,
            "report_statuses": report_statuses,
            "qa_issues": qa_issues,
        })
        if errors:
            warnings.extend(errors)
        _emit("PASS", [], warnings, details)
        return EXIT_OK
    except ValueError as exc:
        _emit("FAIL", [str(exc)], warnings, details)
        return EXIT_CONTRACT
    except (UnicodeDecodeError, json.JSONDecodeError):
        _emit("FAIL", ["输入文件不是有效的 UTF-8 JSON/YAML"], warnings, details)
        return EXIT_CONTRACT
    except Exception as exc:  # noqa: BLE001
        print(f"脚本异常：{type(exc).__name__}", file=sys.stderr)
        _emit("ERROR", ["脚本执行发生未知错误"], warnings, details)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

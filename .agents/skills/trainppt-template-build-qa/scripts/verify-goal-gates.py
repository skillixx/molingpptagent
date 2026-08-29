#!/usr/bin/env python3
"""只读判定模板是否达到 READY_FOR_CONFIRMATION，永不写 Goal。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from _qa_contract import evaluate_qa


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONTRACT = 2
SAFE_TEMPLATE_ID = re.compile(r"^template_[1-9][0-9]*$")
REQUIRED_CHECKS = {
    "development_spec", "template_json", "assets", "registration", "tests", "api", "pptx_roundtrip",
}


def _emit(decision: str, errors: list[str], missing: list[str], details: dict[str, Any]) -> None:
    print(json.dumps({
        "script": "verify-goal-gates",
        "status": "PASS" if decision == "READY_FOR_CONFIRMATION" else "FAIL" if decision == "BLOCKED" else "INCONCLUSIVE",
        "decision": decision,
        "errors": errors,
        "missing": missing,
        "details": details,
        "manual_confirmation_required": True,
        "goal_closed": False,
    }, ensure_ascii=False, indent=2))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读验证 evidence.json 的最终自动门禁。")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--project-root", help="可选项目根；提供后复核规格文件哈希")
    parser.add_argument("--expected-spec-sha256", help="规划交接时记录的规格 SHA-256")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    missing: list[str] = []
    details: dict[str, Any] = {"template_id": args.template_id}
    try:
        if not SAFE_TEMPLATE_ID.fullmatch(args.template_id):
            _emit("BLOCKED", ["模板 ID 无效"], [], details)
            return EXIT_CONTRACT
        evidence_path = Path(args.evidence).resolve()
        if not evidence_path.is_file():
            _emit("INCONCLUSIVE", [], ["evidence.json"], details)
            return EXIT_CONTRACT
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _emit("BLOCKED", ["证据不是有效的 UTF-8 JSON"], [], details)
            return EXIT_CONTRACT
        if not isinstance(evidence, dict):
            _emit("BLOCKED", ["证据顶层必须是对象"], [], details)
            return EXIT_CONTRACT
        if evidence.get("evidence_schema_version") != 1:
            errors.append("仅支持 evidence_schema_version: 1")
        if evidence.get("template_id") != args.template_id:
            errors.append("证据 template_id 与参数不一致")
        if evidence.get("qa_status") not in {"PASS", "FAIL", "INCONCLUSIVE"}:
            errors.append("qa_status 非法")
        if evidence.get("implementation_status") in {"DONE", "DONE_WITH_CONCERNS"}:
            errors.append("自动证据不得闭合 Goal")

        spec = evidence.get("spec") if isinstance(evidence.get("spec"), dict) else {}
        spec_hash = spec.get("sha256")
        if not isinstance(spec_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", spec_hash):
            missing.append("spec.sha256")
        if args.expected_spec_sha256 and isinstance(spec_hash, str):
            if spec_hash.lower() != args.expected_spec_sha256.lower():
                errors.append("证据规格哈希与规划交接值不一致")
        if args.project_root and isinstance(spec.get("path"), str):
            root = Path(args.project_root).resolve()
            spec_path = (root / spec["path"]).resolve()
            try:
                spec_path.relative_to(root)
            except ValueError:
                errors.append("证据规格路径越出项目根目录")
            else:
                if not spec_path.is_file():
                    missing.append("spec.file")
                elif isinstance(spec_hash, str) and _sha256(spec_path).lower() != spec_hash.lower():
                    errors.append("当前规格文件与证据哈希不一致")

        checks = evidence.get("checks") if isinstance(evidence.get("checks"), dict) else {}
        for name in sorted(REQUIRED_CHECKS):
            check = checks.get(name)
            if not isinstance(check, dict):
                missing.append(f"checks.{name}")
            elif check.get("status") != "PASS":
                if check.get("status") == "FAIL":
                    errors.append(f"checks.{name}")
                else:
                    missing.append(f"checks.{name}.pass")
            if name == "tests" and isinstance(check, dict):
                summary = check.get("summary") if isinstance(check.get("summary"), dict) else {}
                if summary.get("executed") is not True or summary.get("exit_code") != 0:
                    errors.append("checks.tests.execution")

        _, qa_errors, qa_missing = evaluate_qa(evidence.get("qa"), args.template_id)
        errors.extend(qa_errors)
        missing.extend(qa_missing)

        details.update({
            "evidence_sha256": _sha256(evidence_path),
            "recorded_qa_status": evidence.get("qa_status"),
            "recorded_implementation_status": evidence.get("implementation_status"),
            "checks_found": sorted(checks),
        })
        errors = sorted(set(errors))
        missing = sorted(set(missing))
        if errors or evidence.get("qa_status") == "FAIL" or evidence.get("implementation_status") == "BLOCKED":
            _emit("BLOCKED", errors or ["证据记录了失败状态"], missing, details)
            return EXIT_CONTRACT
        if missing or evidence.get("qa_status") != "PASS":
            _emit("INCONCLUSIVE", [], missing or ["qa_status.PASS"], details)
            return EXIT_CONTRACT
        if evidence.get("implementation_status") != "READY_FOR_CONFIRMATION":
            _emit("INCONCLUSIVE", [], ["implementation_status.READY_FOR_CONFIRMATION"], details)
            return EXIT_CONTRACT
        _emit("READY_FOR_CONFIRMATION", [], [], details)
        return EXIT_OK
    except Exception as exc:  # noqa: BLE001
        print(f"脚本异常：{type(exc).__name__}", file=sys.stderr)
        _emit("BLOCKED", ["脚本执行发生未知错误"], [], details)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

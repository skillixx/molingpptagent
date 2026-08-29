#!/usr/bin/env python3
"""只读验证开发规格、哈希、模板 ID 与当前运行授权。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONTRACT = 2
EXIT_PERMISSION = 3
EXIT_ENVIRONMENT = 4
SAFE_TEMPLATE_ID = re.compile(r"^template_[1-9][0-9]*$")


def _emit(status: str, *, errors: list[str], warnings: list[str], details: dict[str, Any]) -> None:
    """统一输出 JSON，避免诊断混入标准输出。"""
    print(json.dumps({
        "script": "validate-development-spec",
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


def _resolve(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    return (candidate if candidate.is_absolute() else root / candidate).resolve()


def _active_registration_count(path: Path, template_id: str) -> int:
    """忽略整行 Python 注释，只统计活动注册文本中的模板 ID。"""
    if not path.is_file():
        return 0
    active = "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    return len(re.findall(rf"['\"]{re.escape(template_id)}['\"]", active))


def _non_empty_dict(value: Any) -> bool:
    return isinstance(value, dict) and bool(value) and all(
        isinstance(item, int) and not isinstance(item, bool) and item > 0
        for item in value.values()
    )


def _git_changes(root: Path) -> dict[str, Any]:
    """只记录精简工作区摘要，避免大型未跟踪目录淹没门禁报告。"""
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=normal"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return {"available": False, "count": 0, "entries": []}
    lines = [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "available": True,
        "count": len(lines),
        "entries": lines[:100],
        "truncated": len(lines) > 100,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只读验证 READY_FOR_BUILD 规格；不会修改规格或项目文件。",
    )
    parser.add_argument("--project-root", required=True, help="TrainPPTAgent 项目根目录")
    parser.add_argument("--spec", required=True, help="机器可读 YAML 规格路径")
    parser.add_argument("--template-id", help="预期模板 ID；默认读取规格")
    parser.add_argument(
        "--mode",
        choices=("build", "repair", "test-only", "audit-evidence", "run-qa"),
        default="build",
    )
    parser.add_argument("--expected-spec-sha256", help="规划交接时记录的规格 SHA-256")
    parser.add_argument("--authorize-code-changes", action="store_true", help="当前消息明确授权代码修改")
    parser.add_argument("--authorize-image-generation", action="store_true", help="当前消息明确授权图片生成")
    parser.add_argument("--authorize-real-qa", action="store_true", help="当前消息明确授权真实 QA 副作用")
    parser.add_argument("--will-generate-images", action="store_true", help="本次 repair 确实需要重新生成图片")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"mode": args.mode}
    permission_errors: list[str] = []

    try:
        import yaml  # type: ignore
    except ImportError:
        _emit("INCONCLUSIVE", errors=["项目解释器缺少 PyYAML"], warnings=[], details=details)
        return EXIT_ENVIRONMENT

    try:
        root = Path(args.project_root).resolve()
        spec_path = _resolve(root, args.spec)
        if not root.is_dir():
            errors.append("项目根目录不存在")
        if not spec_path.is_file():
            errors.append("规格文件不存在")
        if errors:
            _emit("FAIL", errors=errors, warnings=warnings, details=details)
            return EXIT_CONTRACT

        raw = spec_path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            errors.append("规格必须使用 UTF-8 无 BOM")
        if b"\r\n" in raw:
            errors.append("规格必须使用 LF 换行")
        actual_spec_hash = hashlib.sha256(raw).hexdigest()
        details["spec_sha256"] = actual_spec_hash
        if args.expected_spec_sha256 and actual_spec_hash.lower() != args.expected_spec_sha256.lower():
            errors.append("规格 SHA-256 与规划交接值不一致")

        try:
            spec = yaml.safe_load(raw.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError):
            errors.append("规格不是有效的 UTF-8 YAML")
            spec = None
        if not isinstance(spec, dict):
            errors.append("规格顶层必须是对象")
            spec = {}

        if spec.get("spec_version") != 1:
            errors.append("仅支持 spec_version: 1")
        if spec.get("status") != "READY_FOR_BUILD":
            errors.append("规格状态必须为 READY_FOR_BUILD")

        template = spec.get("template") if isinstance(spec.get("template"), dict) else {}
        template_id = args.template_id or template.get("id")
        details["template_id"] = template_id
        if not isinstance(template_id, str) or not SAFE_TEMPLATE_ID.fullmatch(template_id):
            errors.append("模板 ID 必须匹配 template_<正整数>")
            template_id = ""
        elif template.get("id") != template_id:
            errors.append("参数模板 ID 与规格 template.id 不一致")
        if template.get("id_status") != "candidate":
            errors.append("开发前 template.id_status 必须为 candidate")
        if not isinstance(template.get("name"), str) or not template.get("name", "").strip():
            errors.append("规格缺少可读模板名称")

        pages = spec.get("pages") if isinstance(spec.get("pages"), dict) else {}
        mvp = pages.get("mvp") if isinstance(pages.get("mvp"), dict) else {}
        production = pages.get("production") if isinstance(pages.get("production"), dict) else {}
        if not _non_empty_dict(mvp.get("inventory")):
            errors.append("pages.mvp.inventory 必须是非空的正整数映射")
        if not _non_empty_dict(production.get("inventory")):
            errors.append("pages.production.inventory 必须是非空的正整数映射")

        assets = spec.get("assets") if isinstance(spec.get("assets"), dict) else {}
        asset_items = assets.get("items")
        if not isinstance(asset_items, list) or not asset_items:
            errors.append("assets.items 必须是非空数组")
            asset_items = []
        retry_limits = assets.get("retry_limits") if isinstance(assets.get("retry_limits"), dict) else {}
        # 同时接受规划契约的直观字段和早期 retry_limits 形状，避免共享契约无意义漂移。
        global_limit = assets.get("max_total_generation_attempts", retry_limits.get("global"))
        if asset_items and (not isinstance(global_limit, int) or isinstance(global_limit, bool) or global_limit <= 0):
            errors.append("assets.max_total_generation_attempts 必须是正整数")
        for index, item in enumerate(asset_items):
            if not isinstance(item, dict):
                errors.append(f"assets.items[{index}] 必须是对象")
                continue
            item_limit = item.get("max_attempts", retry_limits.get("per_item"))
            if not isinstance(item_limit, int) or isinstance(item_limit, bool) or item_limit <= 0:
                errors.append(f"assets.items[{index}].max_attempts 必须是正整数")

        qa = spec.get("qa") if isinstance(spec.get("qa"), dict) else {}
        for key in ("content_cases", "image_counts", "viewports", "affected_test_commands"):
            if not isinstance(qa.get(key), list) or not qa.get(key):
                errors.append(f"qa.{key} 必须是非空数组")
        if qa.get("export_roundtrip_required") is not True:
            errors.append("qa.export_roundtrip_required 必须为 true")

        planning_permissions = spec.get("planning_run_permissions")
        if not isinstance(planning_permissions, dict):
            errors.append("缺少 planning_run_permissions")
        else:
            enabled = sorted(key for key, value in planning_permissions.items() if value is not False)
            if enabled:
                errors.append("规划运行权限必须全部为 false")

        required_auth = spec.get("required_build_authorizations")
        if not isinstance(required_auth, dict):
            errors.append("缺少 required_build_authorizations")
            required_auth = {}
        if required_auth.get("final_manual_close") is not True:
            errors.append("required_build_authorizations.final_manual_close 必须为 true")

        # 参考文件允许位于项目外，但必须存在且与规划哈希完全一致。
        reference_results: list[dict[str, Any]] = []
        reference_files = template.get("reference_files")
        if not isinstance(reference_files, list) or not reference_files:
            errors.append("template.reference_files 必须是非空数组")
            reference_files = []
        for item in reference_files:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                errors.append("参考文件项必须包含 path 和 sha256")
                continue
            reference_path = _resolve(root, item["path"])
            expected_hash = item.get("sha256")
            result = {"path": str(reference_path), "exists": reference_path.is_file()}
            if not reference_path.is_file():
                errors.append("参考文件不存在")
            elif not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
                errors.append("参考文件 sha256 必须是 64 位十六进制")
            else:
                actual_hash = _sha256(reference_path)
                result["sha256_matches"] = actual_hash.lower() == expected_hash.lower()
                if not result["sha256_matches"]:
                    errors.append("参考文件 SHA-256 已变化")
            reference_results.append(result)
        details["reference_files"] = reference_results

        project = spec.get("project") if isinstance(spec.get("project"), dict) else {}
        template_dir = _resolve(root, project.get("template_dir", "backend/main_api/template"))
        registration_file = _resolve(root, project.get("registration_file", "backend/main_api/main.py"))
        tests_dir = root / "backend" / "main_api" / "tests"
        conflict_sources: list[str] = []
        if template_id:
            candidates = [
                template_dir / f"{template_id}.json",
                template_dir / f"{template_id}.jpg",
                tests_dir / f"test_{template_id}.py",
            ]
            conflict_sources.extend(str(path.relative_to(root)) for path in candidates if path.exists())
            conflict_sources.extend(
                str(path.relative_to(root)) for path in template_dir.glob(f"{template_id}_asset_*") if path.is_file()
            )
            registration_count = _active_registration_count(registration_file, template_id)
            if registration_count:
                conflict_sources.append(f"{registration_file.relative_to(root)}:registration({registration_count})")
            details["registration_count"] = registration_count
        details["id_conflicts"] = sorted(set(conflict_sources))
        existing_mode = args.mode in {"repair", "test-only", "audit-evidence", "run-qa"}
        if args.mode == "build" and conflict_sources:
            errors.append("候选模板 ID 已被占用；必须返回规划 Skill 更新规格")
        if existing_mode and template_id and not (template_dir / f"{template_id}.json").is_file():
            errors.append("当前模式要求目标模板 JSON 已存在")

        # 实时授权只能来自显式 CLI 标志，不能从规格字段自动推导。
        if args.mode in {"build", "repair"} and not args.authorize_code_changes:
            permission_errors.append("当前请求未显式授权代码修改")
        needs_images = args.mode == "build" and required_auth.get("image_generation") is True
        needs_images = needs_images or args.will_generate_images
        if needs_images and not args.authorize_image_generation:
            permission_errors.append("当前请求未显式授权图片生成")
        needs_real_qa = args.mode in {"build", "run-qa"} and required_auth.get("real_task_execution") is True
        if needs_real_qa and not args.authorize_real_qa:
            permission_errors.append("当前请求未显式授权真实 QA")

        details["git_changes"] = _git_changes(root)
        if not (root / ".git").exists():
            warnings.append("项目根目录未发现 .git，无法记录工作区改动")

        if permission_errors:
            _emit("BLOCKED", errors=permission_errors, warnings=warnings, details=details)
            return EXIT_PERMISSION
        if errors:
            _emit("FAIL", errors=errors, warnings=warnings, details=details)
            return EXIT_CONTRACT
        _emit("PASS", errors=[], warnings=warnings, details=details)
        return EXIT_OK
    except FileNotFoundError as exc:
        print(f"环境命令不可用：{exc}", file=sys.stderr)
        _emit("INCONCLUSIVE", errors=["环境命令不可用"], warnings=warnings, details=details)
        return EXIT_ENVIRONMENT
    except Exception as exc:  # noqa: BLE001 - 顶层必须稳定映射未知异常。
        print(f"脚本异常：{type(exc).__name__}", file=sys.stderr)
        _emit("ERROR", errors=["脚本执行发生未知错误"], warnings=warnings, details=details)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""验证 TrainPPTAgent 模板规划规格的结构、QA 闭环和规划权限。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover - 通过真实缺依赖环境触发
    yaml = None


EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_CONTRACT = 2
EXIT_PERMISSION = 3
EXIT_ENVIRONMENT = 4

TEMPLATE_ID_RE = re.compile(r"^template_([1-9]\d*)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_STATUSES = {"DRAFT", "READY_FOR_BUILD", "SUPERSEDED"}
RIGHTS_STATUSES = {"owned", "licensed", "public-domain", "generated-for-project", "unknown", "restricted"}
RIGHTS_ACTIONS = {"reuse", "redraw", "regenerate", "replace", "exclude", "redraw-and-regenerate"}
PLANNING_PERMISSION_KEYS = {
    "allow_image_generation",
    "allow_code_changes",
    "allow_git_commit",
    "allow_git_push",
    "allow_merge_main",
    "allow_service_restart",
    "allow_production_deploy",
}
BUILD_AUTHORIZATION_KEYS = {
    "image_generation",
    "code_changes",
    "real_task_execution",
    "final_manual_close",
}
FORBIDDEN_TOP_LEVEL_FIELDS = {
    "spec_sha256",
    "implementation_status",
    "qa_status",
    "goal_status",
    "evidence",
    "test_results",
    "task_id",
}

# Windows 控制台可能默认使用 GBK；机器可读 JSON 始终以 UTF-8 输出。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验模板规划 YAML 规格。")
    parser.add_argument("--spec", required=True, type=Path, help="待验证的 YAML 规格路径。")
    parser.add_argument("--mode", choices=("plan-only", "revise"), default="plan-only", help="规划模式。")
    parser.add_argument("--project-root", type=Path, help="可选：覆盖并核对规格中的项目根目录。")
    parser.add_argument("--output", type=Path, help="可选 JSON 输出路径；不得与规格路径相同。")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def mapping_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def duplicate_values(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def contains_template_marker(value: Any) -> bool:
    """只检查字符串值，避免把 JSON 相邻对象的花括号误判成模板变量。"""
    if isinstance(value, str):
        return "{{" in value or "}}" in value
    if isinstance(value, list):
        return any(contains_template_marker(item) for item in value)
    if isinstance(value, dict):
        return any(contains_template_marker(key) or contains_template_marker(item) for key, item in value.items())
    return False


def add_required_mapping(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict) or not value:
        errors.append(f"{key} 必须是非空映射。")
        return {}
    return value


def validate_project(data: dict[str, Any], status: str, override_root: Path | None, errors: list[str]) -> Path | None:
    project = add_required_mapping(data, "project", errors)
    if not project:
        return None

    for key in ("root", "template_dir", "registration_file", "renderer_file"):
        if not is_string(project.get(key)):
            errors.append(f"project.{key} 必须是非空字符串。")

    root_value = project.get("root")
    if override_root is not None:
        root = override_root.resolve()
        if is_string(root_value):
            try:
                declared = Path(str(root_value)).resolve()
                if declared != root:
                    errors.append(f"project.root 与 --project-root 不一致：{declared} != {root}")
            except OSError as exc:
                errors.append(f"project.root 无法解析：{exc}")
    elif is_string(root_value):
        root = Path(str(root_value)).resolve()
    else:
        return None

    if status == "READY_FOR_BUILD":
        if not root.is_dir():
            errors.append(f"READY_FOR_BUILD 的 project.root 必须存在：{root}")
        else:
            for key in ("template_dir", "registration_file", "renderer_file"):
                value = project.get(key)
                if is_string(value) and not (root / str(value)).exists():
                    errors.append(f"READY_FOR_BUILD 的 project.{key} 不存在：{root / str(value)}")
    return root


def validate_template(data: dict[str, Any], status: str, project_root: Path | None, errors: list[str], warnings: list[str]) -> None:
    template = add_required_mapping(data, "template", errors)
    if not template:
        return

    template_id = template.get("id")
    if not is_string(template_id) or not TEMPLATE_ID_RE.fullmatch(str(template_id)):
        errors.append("template.id 必须匹配 template_<正整数>。")
    if template.get("id_status") != "candidate":
        errors.append("template.id_status 必须为 candidate，规划规格不会占用模板 ID。")
    for key in ("name", "category"):
        if not is_string(template.get(key)):
            errors.append(f"template.{key} 必须是非空字符串。")

    requirements_summary = template.get("requirements_summary")
    references = template.get("reference_files")
    if not isinstance(references, list):
        errors.append("template.reference_files 必须是列表。")
        references = []
    if not is_string(requirements_summary) and not references:
        errors.append("template.requirements_summary 与 reference_files 至少提供一项有效输入。")

    for index, item in enumerate(references):
        prefix = f"template.reference_files[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} 必须是映射。")
            continue
        path_value = item.get("path")
        sha_value = item.get("sha256")
        rights_status = item.get("rights_status")
        planned_action = item.get("planned_action")
        if not is_string(path_value):
            errors.append(f"{prefix}.path 必须是非空字符串。")
            continue
        if rights_status not in RIGHTS_STATUSES:
            errors.append(f"{prefix}.rights_status 不受支持：{rights_status}")
        if planned_action not in RIGHTS_ACTIONS:
            errors.append(f"{prefix}.planned_action 不受支持：{planned_action}")
        if rights_status in {"unknown", "restricted"} and planned_action == "reuse":
            errors.append(f"{prefix} 的未知或受限素材不得规划为 reuse。")

        reference_path = Path(str(path_value))
        if not reference_path.is_absolute() and project_root is not None:
            reference_path = project_root / reference_path
        if reference_path.exists() and reference_path.is_file():
            actual_hash = file_sha256(reference_path)
            if not is_string(sha_value) or not SHA256_RE.fullmatch(str(sha_value)):
                errors.append(f"{prefix}.sha256 必须是 64 位小写十六进制。")
            elif str(sha_value) != actual_hash:
                errors.append(f"{prefix}.sha256 与文件原始字节不一致。")
        elif status == "READY_FOR_BUILD":
            errors.append(f"READY_FOR_BUILD 的参考文件必须存在：{reference_path}")
        else:
            warnings.append(f"DRAFT 参考文件当前不可用：{reference_path}")

    for key in ("canvas", "cover"):
        geometry = mapping_value(template.get(key))
        if not geometry:
            errors.append(f"template.{key} 必须是非空映射。")
            continue
        for axis in ("width", "height"):
            value = geometry.get(axis)
            if not is_number(value) or value <= 0:
                errors.append(f"template.{key}.{axis} 必须是正数。")


def validate_visual(data: dict[str, Any], errors: list[str]) -> None:
    visual = add_required_mapping(data, "visual", errors)
    if not visual:
        return
    if not is_string(visual.get("theme")):
        errors.append("visual.theme 必须是非空字符串。")
    for key in ("palette", "safe_zones"):
        if not isinstance(visual.get(key), list) or not visual.get(key):
            errors.append(f"visual.{key} 必须是非空列表。")
    if not isinstance(visual.get("fonts"), dict) or not visual.get("fonts"):
        errors.append("visual.fonts 必须是非空映射。")
    if not isinstance(visual.get("forbidden_content"), list):
        errors.append("visual.forbidden_content 必须是列表。")
    for key in ("logo_policy", "people_policy"):
        if not is_string(visual.get(key)):
            errors.append(f"visual.{key} 必须是非空字符串。")


def validate_inventory(value: Any, path: str, errors: list[str]) -> None:
    inventory = mapping_value(value)
    if not inventory:
        errors.append(f"{path} 必须是非空映射。")
        return
    total = 0
    for key, count in inventory.items():
        if not is_string(key) or not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append(f"{path}.{key} 必须是非负整数。")
        else:
            total += count
    if total <= 0:
        errors.append(f"{path} 的页面总数必须大于零。")


def validate_capacity(value: Any, path: str, errors: list[str]) -> None:
    values = list_value(value)
    if not values:
        errors.append(f"{path} 必须是非空列表。")
        return
    if any(not isinstance(item, int) or isinstance(item, bool) or item <= 0 for item in values):
        errors.append(f"{path} 只能包含正整数。")
    if len(values) != len(set(values)):
        errors.append(f"{path} 不能包含重复容量。")


def validate_pages(data: dict[str, Any], errors: list[str]) -> None:
    pages = add_required_mapping(data, "pages", errors)
    if not pages:
        return
    mvp = mapping_value(pages.get("mvp"))
    production = mapping_value(pages.get("production"))
    if not mvp:
        errors.append("pages.mvp 必须是非空映射。")
    else:
        validate_inventory(mvp.get("inventory"), "pages.mvp.inventory", errors)
        validate_capacity(mvp.get("contents_capacities"), "pages.mvp.contents_capacities", errors)
        validate_capacity(mvp.get("content_capacities"), "pages.mvp.content_capacities", errors)
    if not production:
        errors.append("pages.production 必须是非空映射。")
    else:
        validate_inventory(production.get("inventory"), "pages.production.inventory", errors)
    specialty = pages.get("specialty_layouts")
    if not isinstance(specialty, list):
        errors.append("pages.specialty_layouts 必须是列表。")
    else:
        ids: list[str] = []
        for index, item in enumerate(specialty):
            if not isinstance(item, dict):
                errors.append(f"pages.specialty_layouts[{index}] 必须是映射。")
                continue
            for key in ("id", "purpose", "selection_rule"):
                if not is_string(item.get(key)):
                    errors.append(f"pages.specialty_layouts[{index}].{key} 必须是非空字符串。")
            if is_string(item.get("id")):
                ids.append(str(item["id"]))
        duplicates = duplicate_values(ids)
        if duplicates:
            errors.append(f"专项版式 ID 重复：{duplicates}")


def validate_semantics(data: dict[str, Any], errors: list[str]) -> None:
    semantics = add_required_mapping(data, "semantics", errors)
    if not semantics:
        return
    for key in ("page_types", "text_types"):
        value = semantics.get(key)
        if not isinstance(value, list) or not value or any(not is_string(item) for item in value):
            errors.append(f"semantics.{key} 必须是非空字符串列表。")
    if semantics.get("content_image_type") != "content":
        errors.append("semantics.content_image_type 必须为 content。")
    if semantics.get("decoration_image_type") != "decoration":
        errors.append("semantics.decoration_image_type 必须为 decoration。")
    if semantics.get("overflow_policy") != "paginate-without-loss":
        errors.append("semantics.overflow_policy 必须为 paginate-without-loss。")
    if semantics.get("grouping_policy") != "content-images-independent":
        errors.append("semantics.grouping_policy 必须为 content-images-independent。")
    sizes = mapping_value(semantics.get("minimum_font_sizes"))
    if not sizes:
        errors.append("semantics.minimum_font_sizes 必须是非空映射。")
    elif any(not is_number(value) or value <= 0 for value in sizes.values()):
        errors.append("semantics.minimum_font_sizes 的值必须是正数。")


def validate_assets(data: dict[str, Any], errors: list[str]) -> int:
    assets = add_required_mapping(data, "assets", errors)
    if not assets:
        return 0
    if not is_string(assets.get("generator_preference")):
        errors.append("assets.generator_preference 必须是非空字符串。")
    total_attempts = assets.get("max_total_generation_attempts")
    if not isinstance(total_attempts, int) or isinstance(total_attempts, bool) or total_attempts <= 0:
        errors.append("assets.max_total_generation_attempts 必须是正整数。")

    items = assets.get("items")
    if not isinstance(items, list) or not items:
        errors.append("assets.items 必须是非空列表。")
        return 0
    ids: list[str] = []
    filenames: list[str] = []
    for index, item in enumerate(items):
        prefix = f"assets.items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} 必须是映射。")
            continue
        for key in ("id", "role", "filename", "format", "safe_zone", "rights_action"):
            if not is_string(item.get(key)):
                errors.append(f"{prefix}.{key} 必须是非空字符串。")
        if item.get("rights_action") not in RIGHTS_ACTIONS:
            errors.append(f"{prefix}.rights_action 不受支持：{item.get('rights_action')}")
        dimensions = item.get("dimensions")
        if (
            not isinstance(dimensions, list)
            or len(dimensions) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in dimensions)
        ):
            errors.append(f"{prefix}.dimensions 必须是两个正整数。")
        max_bytes = item.get("max_bytes")
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            errors.append(f"{prefix}.max_bytes 必须是正整数。")
        if not isinstance(item.get("alpha_required"), bool):
            errors.append(f"{prefix}.alpha_required 必须是布尔值。")
        constraints = item.get("prompt_constraints")
        if not isinstance(constraints, list) or not constraints or any(not is_string(value) for value in constraints):
            errors.append(f"{prefix}.prompt_constraints 必须是非空字符串列表。")
        attempts = item.get("max_attempts")
        if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts <= 0:
            errors.append(f"{prefix}.max_attempts 必须是正整数。")
        if is_string(item.get("id")):
            ids.append(str(item["id"]))
        if is_string(item.get("filename")):
            filenames.append(str(item["filename"]))
    for label, values in (("素材 ID", ids), ("素材文件名", filenames)):
        duplicates = duplicate_values(values)
        if duplicates:
            errors.append(f"{label} 重复：{duplicates}")
    return len(items)


def collect_case_ids(qa: dict[str, Any], errors: list[str]) -> set[str]:
    case_ids: list[str] = []
    for key in ("content_cases", "image_counts", "viewports"):
        items = qa.get(key)
        if not isinstance(items, list) or not items:
            errors.append(f"qa.{key} 必须是非空列表。")
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict) or not is_string(item.get("id")):
                errors.append(f"qa.{key}[{index}].id 必须是非空字符串。")
                continue
            case_ids.append(str(item["id"]))
            if key == "content_cases" and not is_string(item.get("purpose")):
                errors.append(f"qa.content_cases[{index}].purpose 必须是非空字符串。")
            if key == "image_counts":
                values = item.get("values")
                if not isinstance(values, list) or not values or any(
                    not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values
                ):
                    errors.append(f"qa.image_counts[{index}].values 必须是非空非负整数列表。")
            if key == "viewports":
                for axis in ("width", "height"):
                    value = item.get(axis)
                    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                        errors.append(f"qa.viewports[{index}].{axis} 必须是正整数。")
    duplicates = duplicate_values(case_ids)
    if duplicates:
        errors.append(f"QA 案例 ID 重复：{duplicates}")
    return set(case_ids)


def validate_completion_and_qa(data: dict[str, Any], errors: list[str]) -> tuple[int, int]:
    criteria = data.get("completion_criteria")
    if not isinstance(criteria, list) or not criteria:
        errors.append("completion_criteria 必须是非空列表。")
        criteria = []
    criterion_ids: list[str] = []
    for index, item in enumerate(criteria):
        if not isinstance(item, dict):
            errors.append(f"completion_criteria[{index}] 必须是映射。")
            continue
        for key in ("id", "description"):
            if not is_string(item.get(key)):
                errors.append(f"completion_criteria[{index}].{key} 必须是非空字符串。")
        if is_string(item.get("id")):
            criterion_ids.append(str(item["id"]))
    duplicates = duplicate_values(criterion_ids)
    if duplicates:
        errors.append(f"完成条件 ID 重复：{duplicates}")

    qa = add_required_mapping(data, "qa", errors)
    if not qa:
        return len(criteria), 0
    case_ids = collect_case_ids(qa, errors)
    if qa.get("export_roundtrip_required") is not True:
        errors.append("qa.export_roundtrip_required 必须为 true。")
    else:
        case_ids.add("export-roundtrip")
    commands = qa.get("affected_test_commands")
    if not isinstance(commands, list) or not commands or any(not is_string(item) for item in commands):
        errors.append("qa.affected_test_commands 必须是非空字符串列表。")

    coverage = qa.get("coverage_map")
    if not isinstance(coverage, dict):
        errors.append("qa.coverage_map 必须是映射。")
        coverage = {}
    criterion_set = set(criterion_ids)
    missing_criteria = sorted(criterion_set - set(coverage))
    extra_criteria = sorted(set(coverage) - criterion_set)
    if missing_criteria:
        errors.append(f"QA 未覆盖完成条件：{missing_criteria}")
    if extra_criteria:
        errors.append(f"qa.coverage_map 引用了未知完成条件：{extra_criteria}")
    for criterion_id, mapped_cases in coverage.items():
        if not isinstance(mapped_cases, list) or not mapped_cases or any(not is_string(item) for item in mapped_cases):
            errors.append(f"qa.coverage_map.{criterion_id} 必须是非空案例 ID 列表。")
            continue
        unknown_cases = sorted(set(mapped_cases) - case_ids)
        if unknown_cases:
            errors.append(f"qa.coverage_map.{criterion_id} 引用了未知案例：{unknown_cases}")
    return len(criteria), len(case_ids)


def validate_permissions(data: dict[str, Any], mode: str, errors: list[str]) -> None:
    permissions = data.get("planning_run_permissions")
    if not isinstance(permissions, dict):
        errors.append("planning_run_permissions 必须是映射。")
        return
    missing = sorted(PLANNING_PERMISSION_KEYS - set(permissions))
    extra = sorted(set(permissions) - PLANNING_PERMISSION_KEYS)
    if missing:
        errors.append(f"planning_run_permissions 缺少字段：{missing}")
    if extra:
        errors.append(f"planning_run_permissions 含未知字段：{extra}")
    for key in PLANNING_PERMISSION_KEYS:
        if permissions.get(key) is not False:
            errors.append(f"{mode} 下 planning_run_permissions.{key} 必须为 false。")

    authorizations = data.get("required_build_authorizations")
    if not isinstance(authorizations, dict):
        errors.append("required_build_authorizations 必须是映射。")
        return
    missing = sorted(BUILD_AUTHORIZATION_KEYS - set(authorizations))
    extra = sorted(set(authorizations) - BUILD_AUTHORIZATION_KEYS)
    if missing:
        errors.append(f"required_build_authorizations 缺少字段：{missing}")
    if extra:
        errors.append(f"required_build_authorizations 含未知字段：{extra}")
    for key in BUILD_AUTHORIZATION_KEYS:
        if authorizations.get(key) is not True:
            errors.append(f"required_build_authorizations.{key} 必须为 true，且实施时仍需实时授权。")


def validate_spec(path: Path, mode: str, override_root: Path | None) -> tuple[dict[str, Any], int]:
    if not path.exists() or not path.is_file():
        return {"status": "FAIL", "errors": [f"规格文件不存在：{path}"], "warnings": []}, EXIT_CONTRACT
    try:
        raw = path.read_bytes()
        data = yaml.safe_load(raw.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        return {"status": "FAIL", "errors": [f"规格不是有效 UTF-8：{exc}"], "warnings": []}, EXIT_CONTRACT
    except yaml.YAMLError as exc:
        return {"status": "FAIL", "errors": [f"YAML 无法解析：{exc}"], "warnings": []}, EXIT_CONTRACT
    if not isinstance(data, dict):
        return {"status": "FAIL", "errors": ["规格顶层必须是映射。"], "warnings": []}, EXIT_CONTRACT

    errors: list[str] = []
    permission_errors: list[str] = []
    warnings: list[str] = []
    if data.get("spec_version") != 1:
        errors.append("spec_version 必须为整数 1。")
    status = data.get("status")
    if status not in ALLOWED_STATUSES:
        errors.append(f"status 不受支持：{status}")
        status = "INVALID"
    for key in ("created_at", "updated_at"):
        if data.get(key) in (None, ""):
            errors.append(f"{key} 必填。")
    forbidden = sorted(FORBIDDEN_TOP_LEVEL_FIELDS & set(data))
    if forbidden:
        errors.append(f"规划规格不得包含实施或自引用字段：{forbidden}")

    project_root = validate_project(data, str(status), override_root, errors)
    validate_template(data, str(status), project_root, errors, warnings)
    validate_visual(data, errors)
    validate_pages(data, errors)
    validate_semantics(data, errors)
    asset_count = validate_assets(data, errors)
    criterion_count, qa_case_count = validate_completion_and_qa(data, errors)
    validate_permissions(data, mode, permission_errors)

    open_decisions = data.get("open_decisions")
    known_limits = data.get("known_limits")
    if not isinstance(open_decisions, list):
        errors.append("open_decisions 必须是列表。")
        open_decisions = []
    if not isinstance(known_limits, list):
        errors.append("known_limits 必须是列表。")
    if status == "READY_FOR_BUILD" and open_decisions:
        errors.append("READY_FOR_BUILD 的 open_decisions 必须为空。")

    if contains_template_marker(data):
        if status == "READY_FOR_BUILD":
            errors.append("READY_FOR_BUILD 规格仍包含双花括号模板变量。")
        else:
            warnings.append("DRAFT 规格仍包含双花括号模板变量。")

    all_errors = errors + permission_errors
    exit_code = EXIT_OK
    if permission_errors:
        exit_code = EXIT_PERMISSION
    elif errors:
        exit_code = EXIT_CONTRACT
    payload = {
        "status": "PASS" if not all_errors else "FAIL",
        "schema_version": 1,
        "spec": {
            "path": str(path.resolve()),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "declared_status": status,
            "declared_version": data.get("spec_version"),
        },
        "mode": mode,
        "summary": {
            "asset_count": asset_count,
            "completion_criterion_count": criterion_count,
            "qa_case_count_including_roundtrip": qa_case_count,
            "open_decision_count": len(open_decisions),
        },
        "errors": all_errors,
        "warnings": warnings,
    }
    return payload, exit_code


def emit(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)


def main() -> int:
    args = parse_args()
    if yaml is None:
        payload = {
            "status": "FAIL",
            "errors": ["缺少 PyYAML；请使用项目 .venv 解释器或安装 backend 依赖。"],
            "warnings": [],
        }
        print(payload["errors"][0], file=sys.stderr)
        emit(payload, args.output)
        return EXIT_ENVIRONMENT

    try:
        if args.output is not None and args.output.resolve() == args.spec.resolve():
            payload = {"status": "FAIL", "errors": ["--output 不得覆盖输入规格文件。"], "warnings": []}
            print(payload["errors"][0], file=sys.stderr)
            emit(payload, None)
            return EXIT_PERMISSION
        payload, exit_code = validate_spec(args.spec, args.mode, args.project_root)
        if exit_code != EXIT_OK:
            print("规划规格校验未通过。", file=sys.stderr)
        emit(payload, args.output)
        return exit_code
    except Exception as exc:  # pragma: no cover - 兜底保证机器可读输出
        print(f"脚本内部异常：{exc}", file=sys.stderr)
        emit({"status": "FAIL", "errors": [str(exc)], "warnings": []}, args.output)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())

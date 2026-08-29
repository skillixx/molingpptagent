"""QA manifest 的白名单、脱敏检查与门禁推导共享实现。"""

from __future__ import annotations

import re
from typing import Any


SENSITIVE_KEYS = {
    "authorization", "cookie", "database_url", "db_url", "password", "passwd", "secret", "token",
}
SENSITIVE_VALUE_RE = re.compile(
    r"(?i)(bearer\s+[a-z0-9._-]{12,}|sk-[a-z0-9]{16,}|gh[pousr]_[a-z0-9]{20,}|"
    r"-----begin .*private key-----|eyj[a-z0-9_-]{20,}\.[a-z0-9_-]{10,}\.[a-z0-9_-]{10,}|"
    r"[a-z][a-z0-9+.-]*://[^:/\s]+:[^@/\s]+@)"
)

QA_FIELDS: dict[str, set[str]] = {
    "e2e": {"status", "progress", "template_id", "declared_slide_count", "actual_slide_count", "page_types_covered"},
    "editor": {"text_saved", "text_persisted_after_reload", "content_image_replaced", "decorations_preserved"},
    "failure_feedback": {"visible", "button_recovered", "retry_available"},
    "runtime": {"template_unique", "template_json_ok", "cover_ok", "assets_ok"},
    "pptx": {"structure_valid", "slide_count_matches", "parsed_by_product", "reimported", "editable_after_reimport"},
}
RESPONSIVE_FIELDS = {"class", "viewport", "client_width", "scroll_width", "buttons_reachable", "feedback_visible"}


def find_sensitive(value: Any, prefix: str = "") -> list[str]:
    """同时检查危险键和危险字符串值，返回路径但不返回秘密原文。"""
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            child_path = f"{prefix}.{key}" if prefix else str(key)
            if (
                normalized in SENSITIVE_KEYS
                or normalized.endswith("_token")
                or normalized.endswith("_password")
                or normalized.endswith("_secret")
            ):
                hits.append(child_path)
            hits.extend(find_sensitive(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(find_sensitive(child, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        if SENSITIVE_VALUE_RE.search(value) or len(value) > 256 or "\n" in value or "\r" in value:
            hits.append(prefix or "value")
    return sorted(set(hits))


def sanitize_qa_manifest(value: Any) -> tuple[dict[str, Any], list[str]]:
    """仅复制 QA Schema 白名单字段，拒绝额外业务正文或敏感值。"""
    if not isinstance(value, dict):
        return {}, ["QA manifest 顶层必须是对象"]

    errors: list[str] = []
    allowed_top = set(QA_FIELDS) | {"responsive"}
    for key in value:
        if key not in allowed_top:
            errors.append(f"QA manifest 包含未允许字段：qa.{key}")

    clean: dict[str, Any] = {}
    for group, allowed in QA_FIELDS.items():
        raw_group = value.get(group)
        if raw_group is None:
            continue
        if not isinstance(raw_group, dict):
            errors.append(f"qa.{group} 必须是对象")
            continue
        unexpected = set(raw_group) - allowed
        errors.extend(f"QA manifest 包含未允许字段：qa.{group}.{key}" for key in sorted(unexpected))
        clean[group] = {key: raw_group[key] for key in allowed if key in raw_group}

    responsive = value.get("responsive")
    if responsive is not None:
        if not isinstance(responsive, list):
            errors.append("qa.responsive 必须是数组")
        else:
            clean_items: list[dict[str, Any]] = []
            for index, item in enumerate(responsive):
                if not isinstance(item, dict):
                    errors.append(f"qa.responsive[{index}] 必须是对象")
                    continue
                unexpected = set(item) - RESPONSIVE_FIELDS
                errors.extend(
                    f"QA manifest 包含未允许字段：qa.responsive[{index}].{key}" for key in sorted(unexpected)
                )
                clean_items.append({key: item[key] for key in RESPONSIVE_FIELDS if key in item})
            clean["responsive"] = clean_items

    sensitive = find_sensitive(clean, "qa")
    if sensitive:
        errors.extend(f"QA manifest 包含敏感或非精简值：{path}" for path in sensitive)
    return clean, sorted(set(errors))


def evaluate_qa(qa: Any, template_id: str) -> tuple[str, list[str], list[str]]:
    """用同一套规则供证据收集与最终 Goal 门禁使用。"""
    errors: list[str] = []
    missing: list[str] = []
    if not isinstance(qa, dict):
        return "INCONCLUSIVE", errors, ["qa"]

    e2e = qa.get("e2e")
    if not isinstance(e2e, dict):
        missing.append("qa.e2e")
    else:
        expected = {"status": "succeeded", "progress": 100, "template_id": template_id}
        for key, expected_value in expected.items():
            if key not in e2e:
                missing.append(f"qa.e2e.{key}")
            elif e2e[key] != expected_value:
                errors.append(f"qa.e2e.{key}")
        declared = e2e.get("declared_slide_count")
        actual = e2e.get("actual_slide_count")
        if declared is None or actual is None:
            missing.append("qa.e2e.slide_counts")
        elif not isinstance(declared, int) or declared <= 0 or actual != declared:
            errors.append("qa.e2e.slide_counts")
        if not isinstance(e2e.get("page_types_covered"), list) or not e2e.get("page_types_covered"):
            missing.append("qa.e2e.page_types_covered")

    for group, keys in {
        "editor": ("text_saved", "text_persisted_after_reload", "content_image_replaced", "decorations_preserved"),
        "failure_feedback": ("visible", "button_recovered", "retry_available"),
        "runtime": ("template_unique", "template_json_ok", "cover_ok", "assets_ok"),
        "pptx": ("structure_valid", "slide_count_matches", "parsed_by_product", "reimported", "editable_after_reimport"),
    }.items():
        group_value = qa.get(group)
        if not isinstance(group_value, dict):
            missing.append(f"qa.{group}")
            continue
        for key in keys:
            if key not in group_value:
                missing.append(f"qa.{group}.{key}")
            elif group_value[key] is not True:
                errors.append(f"qa.{group}.{key}")

    responsive = qa.get("responsive")
    required_classes = {"desktop", "laptop", "tablet", "mobile"}
    if not isinstance(responsive, list):
        missing.append("qa.responsive")
    else:
        classes = {item.get("class") for item in responsive if isinstance(item, dict)}
        missing.extend(f"qa.responsive.{item}" for item in sorted(required_classes - classes))
        for index, item in enumerate(responsive):
            if not isinstance(item, dict):
                errors.append(f"qa.responsive[{index}]")
                continue
            for key in ("viewport", "client_width", "scroll_width", "buttons_reachable", "feedback_visible"):
                if key not in item:
                    missing.append(f"qa.responsive[{index}].{key}")
            if isinstance(item.get("client_width"), (int, float)) and isinstance(item.get("scroll_width"), (int, float)):
                if item["scroll_width"] > item["client_width"]:
                    errors.append(f"qa.responsive[{index}].horizontal_overflow")
            if item.get("buttons_reachable") is False or item.get("feedback_visible") is False:
                errors.append(f"qa.responsive[{index}].interaction")

    status = "FAIL" if errors else "INCONCLUSIVE" if missing else "PASS"
    return status, sorted(set(errors)), sorted(set(missing))

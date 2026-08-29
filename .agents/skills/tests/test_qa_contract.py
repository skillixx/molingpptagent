"""开发 QA 证据白名单与共享门禁测试。"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / ".agents" / "skills" / "trainppt-template-build-qa" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _qa_contract import evaluate_qa, sanitize_qa_manifest  # noqa: E402


def _valid_qa() -> dict:
    return {
        "e2e": {
            "status": "succeeded",
            "progress": 100,
            "template_id": "template_14",
            "declared_slide_count": 5,
            "actual_slide_count": 5,
            "page_types_covered": ["cover", "contents", "transition", "content", "end"],
        },
        "editor": {
            "text_saved": True,
            "text_persisted_after_reload": True,
            "content_image_replaced": True,
            "decorations_preserved": True,
        },
        "failure_feedback": {"visible": True, "button_recovered": True, "retry_available": True},
        "runtime": {"template_unique": True, "template_json_ok": True, "cover_ok": True, "assets_ok": True},
        "pptx": {
            "structure_valid": True,
            "slide_count_matches": True,
            "parsed_by_product": True,
            "reimported": True,
            "editable_after_reimport": True,
        },
        "responsive": [
            {
                "class": name,
                "viewport": viewport,
                "client_width": width,
                "scroll_width": width,
                "buttons_reachable": True,
                "feedback_visible": True,
            }
            for name, viewport, width in (
                ("desktop", "1920x1080", 1920),
                ("laptop", "1366x768", 1366),
                ("tablet", "768x1024", 768),
                ("mobile", "390x844", 390),
            )
        ],
    }


def test_valid_manifest_is_sanitized_and_passes_shared_gate() -> None:
    clean, errors = sanitize_qa_manifest(_valid_qa())
    status, gate_errors, missing = evaluate_qa(clean, "template_14")
    assert errors == []
    assert status == "PASS"
    assert gate_errors == []
    assert missing == []


def test_manifest_rejects_unrecognized_business_content() -> None:
    manifest = _valid_qa()
    manifest["notes"] = "这里可能包含用户演示正文"
    _, errors = sanitize_qa_manifest(manifest)
    assert any("qa.notes" in error for error in errors)


def test_manifest_rejects_sensitive_value_even_under_allowed_key() -> None:
    manifest = _valid_qa()
    manifest["responsive"][0]["viewport"] = "Bearer abcdefghijklmnopqrstuvwxyz"
    _, errors = sanitize_qa_manifest(manifest)
    assert any("qa.responsive[0].viewport" in error for error in errors)


def test_evidence_scripts_use_the_same_gate_module() -> None:
    collect = (SCRIPTS / "collect-evidence.py").read_text(encoding="utf-8")
    verify = (SCRIPTS / "verify-goal-gates.py").read_text(encoding="utf-8")
    assert "from _qa_contract import" in collect
    assert "from _qa_contract import" in verify
    assert "def _qa_gate" not in collect
    assert "def _qa_gate" not in verify

"""仓库级 Skill 包结构与安全边界回归测试。"""

from __future__ import annotations

import re
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"

EXPECTED = {
    "trainppt-template-planning": {
        "references": {
            "planning-workflow.md",
            "reference-and-rights-audit.md",
            "spec-contract.md",
            "planning-review-checklist.md",
            "subagent-contracts.md",
        },
        "scripts": {
            "inspect-reference-pptx.py",
            "discover-template-id.py",
            "validate-planning-spec.py",
        },
        "assets": {
            "template-spec.yaml",
            "development-plan-template.md",
            "goal-template.md",
            "qa-plan-template.md",
        },
    },
    "trainppt-template-build-qa": {
        "references": {
            "build-workflow.md",
            "template-contract.md",
            "asset-policy.md",
            "qa-matrix.md",
            "evidence-schema.md",
            "subagent-contracts.md",
        },
        "scripts": {
            "_qa_contract.py",
            "validate-development-spec.py",
            "validate-template-json.py",
            "audit-template-assets.py",
            "verify-template-registration.ps1",
            "run-template-tests.ps1",
            "verify-template-api.ps1",
            "verify-pptx-roundtrip.py",
            "collect-evidence.py",
            "verify-goal-gates.py",
        },
    },
    "trainppt-safe-release": {
        "references": {
            "modes-and-authorization.md",
            "local-service-map.md",
            "production-release.md",
            "runtime-verification.md",
            "subagent-contracts.md",
        },
        "scripts": {
            "inventory-runtime.ps1",
            "verify-git-readiness.ps1",
            "verify-runtime.ps1",
        },
    },
}


def _frontmatter(skill_text: str) -> dict:
    """解析 SKILL.md 顶部 YAML，不依赖正文中的代码块。"""
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", skill_text, re.DOTALL)
    assert match, "SKILL.md 缺少有效 YAML frontmatter"
    payload = yaml.safe_load(match.group(1))
    assert isinstance(payload, dict)
    return payload


def test_skill_packages_match_declared_contract() -> None:
    """三个 Skill 必须提供规划中声明的公开文件表面。"""
    for skill_name, contract in EXPECTED.items():
        skill_dir = SKILLS_ROOT / skill_name
        skill_path = skill_dir / "SKILL.md"
        assert skill_path.is_file(), skill_path

        text = skill_path.read_text(encoding="utf-8")
        metadata = _frontmatter(text)
        assert metadata["name"] == skill_name
        assert len(str(metadata.get("description", ""))) >= 40
        assert "TODO" not in text

        ui_path = skill_dir / "agents" / "openai.yaml"
        ui = yaml.safe_load(ui_path.read_text(encoding="utf-8"))
        assert ui["interface"]["display_name"]
        assert 25 <= len(ui["interface"]["short_description"]) <= 64
        assert f"${skill_name}" in ui["interface"]["default_prompt"]
        assert ui.get("policy", {}).get("allow_implicit_invocation", True) is True

        for category, filenames in contract.items():
            actual = {path.name for path in (skill_dir / category).iterdir() if path.is_file()}
            assert filenames <= actual, f"{skill_name}/{category} 缺少 {filenames - actual}"
            if category == "references":
                for filename in filenames:
                    assert filename in text, f"{skill_name} 未路由 reference: {filename}"


def test_packages_have_no_scaffold_placeholders() -> None:
    """初始化脚手架的占位符不得进入可用 Skill。"""
    for skill_name in EXPECTED:
        for path in (SKILLS_ROOT / skill_name).rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md", ".yaml", ".yml", ".py", ".ps1"}:
                text = path.read_text(encoding="utf-8")
                assert "TODO" not in text, path
                assert "[TODO" not in text, path


def test_safe_release_has_no_mutating_automation_scripts() -> None:
    """第一版发布 Skill 只能提供只读盘点和验证脚本。"""
    scripts_dir = SKILLS_ROOT / "trainppt-safe-release" / "scripts"
    actual = {path.name for path in scripts_dir.iterdir() if path.is_file()}
    assert actual == EXPECTED["trainppt-safe-release"]["scripts"]
    forbidden = {"safe-merge.ps1", "restart-all.ps1", "deploy-production.ps1"}
    assert not (actual & forbidden)


def test_root_agents_file_stays_small_and_global() -> None:
    """AGENTS.md 只承载常驻规则，不复制模板阶段和端口快照。"""
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    bullets = [line for line in text.splitlines() if line.startswith("- ")]
    assert 8 <= len(bullets) <= 15
    assert "READY_FOR_CONFIRMATION" in text
    assert "强推" in text
    assert not re.search(r"\b(5778|6800|10001|10011|9100)\b", text)
    assert not re.search(r"\bG[0-9]+\b", text)

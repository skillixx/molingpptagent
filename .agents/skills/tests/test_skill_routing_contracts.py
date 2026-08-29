"""三个 Skill 的触发、权限与状态上限行为契约测试。"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS = REPO_ROOT / ".agents" / "skills"


def _skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def test_plan_only_route_blocks_implementation_side_effects() -> None:
    text = _skill("trainppt-template-planning")
    for phrase in ("只写", "不生成图片", "不修改代码", "不启动", "不 Commit"):
        assert phrase in text
    assert "READY_FOR_BUILD" in text


def test_build_route_requires_approved_spec_and_current_authorization() -> None:
    text = _skill("trainppt-template-build-qa")
    assert "status: READY_FOR_BUILD" in text
    assert "不能把规格里的未来授权需求当作实时授权" in text
    assert "trainppt-template-planning" in text


def test_automatic_qa_cannot_close_goal() -> None:
    text = _skill("trainppt-template-build-qa")
    assert "READY_FOR_CONFIRMATION" in text
    assert "只有用户明确确认" in text
    assert "Goal 闭合：仍等待用户确认" in text


def test_assess_mode_is_read_only() -> None:
    text = _skill("trainppt-safe-release")
    assert "`assess`: read-only" in text
    assert "Never force-push" in text
    assert "Keep the feature branch unless" in text


def test_commit_push_pr_and_merge_keep_separate_authority() -> None:
    text = _skill("trainppt-safe-release")
    for mode in ("commit-local", "push-branch", "open-pr", "merge-main"):
        assert f"`{mode}`" in text
    authorization = (SKILLS / "trainppt-safe-release" / "references" / "modes-and-authorization.md").read_text(encoding="utf-8")
    assert "Commit does not imply push" in authorization
    assert "Push does not imply PR or merge" in authorization


def test_production_actions_remain_separately_authorized() -> None:
    text = (SKILLS / "trainppt-safe-release" / "references" / "production-release.md").read_text(encoding="utf-8")
    for action in ("production backup", "database migration", "real billing enablement", "rollback"):
        assert action in text
    assert "README_PRODUCTION.md" in text

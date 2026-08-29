"""安全发布只读脚本的命令行行为测试。"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / ".agents" / "skills" / "trainppt-safe-release" / "scripts"
PWSH = shutil.which("pwsh")


def _run(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """通过公开 CLI 调用脚本，并保留退出码和 JSON 输出。"""
    assert PWSH is not None
    return subprocess.run(
        [PWSH, "-NoProfile", "-File", str(SCRIPTS / script), *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def _init_clean_repo(path: Path) -> Path:
    """创建不依赖当前工作树的最小 Git seam。"""
    path.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Skill Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "skill-test@example.invalid"], check=True)
    (path / "README.md").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "test: baseline"], check=True, capture_output=True)
    return path


@pytest.mark.skipif(PWSH is None, reason="当前环境没有 PowerShell 7")
def test_inventory_runtime_is_read_only_json() -> None:
    result = _run("inventory-runtime.ps1", "-ProjectRoot", str(REPO_ROOT))
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["status"] == "PASS"
    assert payload["mutations"] == []
    assert payload["project_root"] == str(REPO_ROOT)
    assert isinstance(payload["health"], list)


@pytest.mark.skipif(PWSH is None, reason="当前环境没有 PowerShell 7")
def test_git_readiness_accepts_identical_refs_without_mutation(tmp_path: Path) -> None:
    repo = _init_clean_repo(tmp_path / "clean-repo")
    result = _run(
        "verify-git-readiness.ps1",
        "-ProjectRoot",
        str(repo),
        "-BaseRef",
        "HEAD",
        "-FeatureRef",
        "HEAD",
        "-AllowMissingTestEvidence",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["status"] == "PASS"
    assert payload["base_is_ancestor"] is True
    assert "current_branch" in payload
    assert "test_evidence" in payload
    assert payload["mutations"] == []


@pytest.mark.skipif(PWSH is None, reason="当前环境没有 PowerShell 7")
def test_git_readiness_requires_test_evidence_by_default(tmp_path: Path) -> None:
    repo = _init_clean_repo(tmp_path / "missing-evidence")
    result = _run(
        "verify-git-readiness.ps1",
        "-ProjectRoot",
        str(repo),
        "-BaseRef",
        "HEAD",
        "-FeatureRef",
        "HEAD",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert "missing_test_evidence" in payload["blocking"]


@pytest.mark.skipif(PWSH is None, reason="当前环境没有 PowerShell 7")
def test_untracked_secret_is_not_hidden_by_placeholder_elsewhere(tmp_path: Path) -> None:
    repo = _init_clean_repo(tmp_path / "secret-repo")
    secret_value = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"
    key_name = "author" + "ization"
    (repo / ".env.production").write_text(f'example_note=true {key_name}="{secret_value}"\n', encoding="utf-8")
    result = _run(
        "verify-git-readiness.ps1",
        "-ProjectRoot",
        str(repo),
        "-BaseRef",
        "HEAD",
        "-FeatureRef",
        "HEAD",
        "-AllowDirty",
        "-AllowMissingTestEvidence",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert "credential_pattern" in payload["blocking"]
    assert secret_value not in result.stdout


@pytest.mark.skipif(PWSH is None, reason="当前环境没有 PowerShell 7")
def test_secret_scanner_does_not_flag_its_own_regex_source(tmp_path: Path) -> None:
    repo = _init_clean_repo(tmp_path / "regex-source")
    source_dir = repo / "scripts"
    source_dir.mkdir()
    shutil.copy2(SCRIPTS / "verify-git-readiness.ps1", source_dir / "verify-git-readiness.ps1")
    qa_contract = REPO_ROOT / ".agents" / "skills" / "trainppt-template-build-qa" / "scripts" / "_qa_contract.py"
    shutil.copy2(qa_contract, source_dir / "_qa_contract.py")
    result = _run(
        "verify-git-readiness.ps1",
        "-ProjectRoot",
        str(repo),
        "-BaseRef",
        "HEAD",
        "-FeatureRef",
        "HEAD",
        "-AllowDirty",
        "-AllowMissingTestEvidence",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0
    assert payload["credential_finding_count"] == 0


@pytest.mark.skipif(PWSH is None, reason="当前环境没有 PowerShell 7")
def test_inventory_runtime_rejects_missing_project(tmp_path: Path) -> None:
    result = _run("inventory-runtime.ps1", "-ProjectRoot", str(tmp_path / "missing"))
    payload = json.loads(result.stdout)
    assert result.returncode == 4
    assert payload["status"] == "INCONCLUSIVE"
    assert payload["mutations"] == []


@pytest.mark.skipif(PWSH is None, reason="当前环境没有 PowerShell 7")
def test_runtime_verifier_rejects_invalid_template_id_before_network() -> None:
    result = _run(
        "verify-runtime.ps1",
        "-ProjectRoot",
        str(REPO_ROOT),
        "-TemplateId",
        "template_bad",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 4
    assert payload["status"] == "INCONCLUSIVE"
    assert "TemplateId" in payload["error"]
    assert payload["mutations"] == []


def test_git_readiness_covers_all_worktree_layers() -> None:
    source = (SCRIPTS / "verify-git-readiness.ps1").read_text(encoding="utf-8")
    assert "git -C $root diff --cached" in source
    assert "git -C $root diff --unified=0" in source
    assert "git -C $root ls-files --others --exclude-standard" in source
    assert "-not $AllowDirty" in source
    assert "-not $AllowMissingTestEvidence" in source


def test_runtime_verification_is_complete_by_default() -> None:
    source = (SCRIPTS / "verify-runtime.ps1").read_text(encoding="utf-8")
    assert "AllowPartial" not in source
    assert "$unverified.Count -gt 0" in source
    assert '"persistent_worker"' in source
    assert '"database"' in source
    assert "release_identity" in source


def test_inventory_redacts_connection_and_auth_values() -> None:
    source = (SCRIPTS / "inventory-runtime.ps1").read_text(encoding="utf-8")
    for key in ("database[_-]?url", "cookie", "authorization", "bearer"):
        assert key in source.lower()

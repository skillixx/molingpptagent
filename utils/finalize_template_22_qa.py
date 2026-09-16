"""核对 template_22 正式证据并生成冻结候选清单与 G8 汇总。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPOSITORY_ROOT / "doc" / "assets" / "template_22_qa"
TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
REFERENCE_PATH = Path.home() / "Desktop" / "中国风格(5).pptx"
REFERENCE_SHA256 = "17cbc63f0d9d77b9d8b78018047feb10d0d284c150a5e761208cf4e0b683460e"

CANDIDATE_FILES = [
    "backend/main_api/main.py",
    "backend/main_api/template/template_22.json",
    "backend/main_api/template/template_22.jpg",
    "backend/main_api/template/template_22_asset_bg_cover_v1.jpg",
    "backend/main_api/template/template_22_asset_bg_content_v1.jpg",
    "backend/main_api/template/template_22_asset_bg_section_v1.jpg",
    "backend/main_api/template/template_22_asset_bg_end_v1.jpg",
    "backend/main_api/template/template_22_asset_scroll_roll_v1.png",
    "backend/main_api/template/template_22_asset_ink_title_frame_v1.png",
    "backend/main_api/template/template_22_asset_ink_circle_frame_v1.png",
    "backend/main_api/template/template_22_asset_ink_brush_band_v1.png",
    "backend/main_api/template/template_22_asset_petal_sweep_v1.png",
    "backend/main_api/tests/test_template_22.py",
    "doc/template_specs/template_22.yaml",
    "utils/build_peach_ink_template.mjs",
    "utils/process_peach_ink_template_assets.py",
]

EVIDENCE_TOOLS = [
    "utils/build_template_22_qa_document.py",
    "utils/run_template_22_handler_qa.py",
    "utils/verify_template_22_probe_browser.cjs",
    "utils/verify_template_22_browser.cjs",
    "utils/verify_template_22_runtime.cjs",
    "utils/verify_template_22_runtime.ps1",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(relative: str) -> dict[str, Any]:
    path = EVIDENCE_ROOT / relative
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"证据不是 JSON 对象：{relative}")
    return value


def file_record(relative: str) -> dict[str, Any]:
    path = REPOSITORY_ROOT / relative
    if not path.is_file():
        raise RuntimeError(f"候选文件不存在：{relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}


def combined_digest(records: list[dict[str, Any]]) -> str:
    """把路径纳入摘要，避免同内容文件互换后仍得到相同候选标识。"""

    combined = hashlib.sha256()
    for record in records:
        combined.update(record["path"].encode("utf-8"))
        combined.update(b"\0")
        combined.update(record["sha256"].encode("ascii"))
        combined.update(b"\n")
    return combined.hexdigest()


def run_checked(
    name: str,
    command: list[str],
    *,
    cwd: Path = REPOSITORY_ROOT,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """运行冻结候选的正式命令，并把实际命令和输出绑定到本次汇总。"""

    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    record = {
        "name": name,
        "command": command,
        "cwd": str(cwd),
        "exitCode": result.returncode,
        "output": output[-12000:],
    }
    if result.returncode != 0:
        raise RuntimeError(f"正式验收命令失败：{name}\n{output}")
    return record


def main() -> None:
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    if branch != "codex/template-22-peach-ink":
        raise RuntimeError(f"当前分支不是冻结候选分支：{branch}")
    if not REFERENCE_PATH.is_file() or sha256(REFERENCE_PATH) != REFERENCE_SHA256:
        raise RuntimeError("参考 PPT 不存在或 SHA-256 已变化")

    # 先冻结候选摘要，再运行所有正式命令；命令结束后再次计算并禁止候选漂移。
    candidate_records = [file_record(path) for path in CANDIDATE_FILES]
    candidate_digest = combined_digest(candidate_records)
    candidate_id = f"template_22-g8-{candidate_digest[:12]}"
    visual_review = read_json("visual-inspection.json")
    if visual_review.get("status") != "PASS" or visual_review.get("candidateSha256") != candidate_digest:
        raise RuntimeError("视觉检查证据未通过或未绑定当前候选 SHA-256")

    runtime_node = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    )
    playwright_package = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright"
    )
    node_executable = str(runtime_node if runtime_node.is_file() else (shutil.which("node") or "node"))
    npm_executable = shutil.which("npm.cmd") or "npm.cmd"
    pwsh_executable = shutil.which("pwsh") or "pwsh"
    browser_env = dict(os.environ)
    browser_env["PLAYWRIGHT_PACKAGE_PATH"] = str(playwright_package)

    formal_commands: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="template-22-final-") as temporary:
        temporary_root = Path(temporary)
        first_build = temporary_root / "production-first.json"
        second_build = temporary_root / "production-second.json"
        formal_commands.append(run_checked(
            "template-and-affected-regressions",
            [
                sys.executable,
                "-m",
                "pytest",
                "backend/main_api/tests/test_template_22.py",
                "backend/main_api/tests/test_template_renderer.py",
                "backend/main_api/tests/test_template_assets.py",
                "-q",
            ],
        ))
        formal_commands.append(run_checked(
            "frontend-type-check",
            [npm_executable, "run", "type-check"],
            cwd=REPOSITORY_ROOT / "frontend",
        ))
        formal_commands.append(run_checked(
            "production-build-first",
            [node_executable, "utils/build_peach_ink_template.mjs", "--stage", "production", str(first_build)],
        ))
        formal_commands.append(run_checked(
            "production-build-second",
            [node_executable, "utils/build_peach_ink_template.mjs", "--stage", "production", str(second_build)],
        ))
        production_bytes = (TEMPLATE_ROOT / "template_22.json").read_bytes()
        if first_build.read_bytes() != second_build.read_bytes() or first_build.read_bytes() != production_bytes:
            raise RuntimeError("两次生产构建或正式 template_22.json 不一致")
        formal_commands.append(run_checked(
            "real-handler-worker",
            [sys.executable, "utils/run_template_22_handler_qa.py"],
        ))
        formal_commands.append(run_checked(
            "probe-document",
            [
                sys.executable,
                "utils/build_template_22_qa_document.py",
                "--stage",
                "probe",
                "--output",
                "doc/assets/template_22_qa/probe-assets/probe-document.json",
            ],
        ))
        formal_commands.append(run_checked(
            "probe-browser",
            [node_executable, "utils/verify_template_22_probe_browser.cjs", "doc/assets/template_22_qa/probe-assets"],
            env=browser_env,
        ))
        formal_commands.append(run_checked(
            "g8-browser",
            [
                node_executable,
                "utils/verify_template_22_browser.cjs",
                "doc/assets/template_22_qa",
                "backend/main_api/template",
            ],
            env=browser_env,
        ))
        formal_commands.append(run_checked(
            "runtime-browser",
            [node_executable, "utils/verify_template_22_runtime.cjs", "doc/assets/template_22_qa/runtime"],
            env=browser_env,
        ))
        formal_commands.append(run_checked(
            "runtime-process-and-assets",
            [
                pwsh_executable,
                "-NoProfile",
                "-File",
                "utils/verify_template_22_runtime.ps1",
                "-RepositoryRoot",
                str(REPOSITORY_ROOT),
            ],
        ))

    refreshed_candidate_records = [file_record(path) for path in CANDIDATE_FILES]
    if combined_digest(refreshed_candidate_records) != candidate_digest:
        raise RuntimeError("正式验收过程中候选文件发生变化，必须重新冻结并重验")
    candidate_records = refreshed_candidate_records

    required_evidence = {
        "g0": "g0-baseline.json",
        "g1Rights": "reference-rights-audit.json",
        "g1Map": "reference-page-map.json",
        "g2": "probe-summary.json",
        "g3": "asset-summary.json",
        "g4": "g4-sample-summary.json",
        "g5": "g5-mvp-summary.json",
        "g6": "g6-test-summary.json",
        "g7": "g7-production-summary.json",
        "handler": "real-handler-summary.json",
        "browser": "browser-g8-summary.json",
        "runtimeBrowser": "runtime/runtime-summary.json",
        "runtimeProcess": "runtime/runtime-process-summary.json",
        "probeBrowser": "probe-assets/probe-browser-summary.json",
    }
    evidence = {name: read_json(path) for name, path in required_evidence.items()}
    for name in ("g2", "g3", "g4", "g5", "g6", "g7", "handler", "browser", "runtimeBrowser", "runtimeProcess", "probeBrowser"):
        if evidence[name].get("status") != "PASS":
            raise RuntimeError(f"正式证据未通过：{name}")

    template = json.loads((TEMPLATE_ROOT / "template_22.json").read_text(encoding="utf-8"))
    if len(template.get("slides", [])) != 18:
        raise RuntimeError("生产模板不是 18 页")
    if template.get("id") != "template_22":
        raise RuntimeError("生产模板 ID 不正确")
    if evidence["handler"].get("slideTypes") != {
        "cover": 1,
        "contents": 1,
        "transition": 1,
        "content": 3,
        "end": 1,
    }:
        raise RuntimeError("真实处理链没有覆盖约定的五种页面类型")
    if evidence["browser"].get("contentImageReplaced") is not True:
        raise RuntimeError("浏览器证据没有证明业务图片替换")
    if evidence["browser"].get("decorationProtected") is not True:
        raise RuntimeError("浏览器证据没有证明固定装饰保护")
    if evidence["browser"].get("missingTexts"):
        raise RuntimeError("PPTX 往返存在缺失文字")
    if evidence["browser"].get("expectedTextCount", 0) < 40:
        raise RuntimeError("PPTX 往返文字完整性检查范围不足")
    if not evidence["browser"].get("orderedTextChecks"):
        raise RuntimeError("PPTX 往返没有验证目录、正文、指标和行动项顺序")
    if evidence["browser"].get("contentImageBeforeExport", 0) < 1:
        raise RuntimeError("PPTX 往返没有验证业务图片")
    before_images = evidence["browser"].get("imageCountBeforeExportBySlide", [])
    after_images = evidence["browser"].get("roundtripImageCountBySlide", [])
    if len(before_images) <= 5 or len(after_images) <= 5 or before_images[5] != after_images[5]:
        raise RuntimeError("PPTX 往返前后图文页图片数量不一致")
    if evidence["browser"].get("contentImageGeometryRetained") is not True:
        raise RuntimeError("PPTX 往返没有保留业务图片槽位几何位置")
    replacement_inputs = evidence["probeBrowser"].get("replacementInputs", [])
    if {(item.get("name"), item.get("width"), item.get("height")) for item in replacement_inputs} != {
        ("landscape", 600, 450),
        ("portrait", 600, 900),
        ("square", 600, 600),
    }:
        raise RuntimeError("浏览器探针未覆盖真实横图、竖图和方图替换")
    if evidence["runtimeProcess"].get("candidateJsonSha256") != sha256(TEMPLATE_ROOT / "template_22.json"):
        raise RuntimeError("运行中服务没有返回当前候选 template_22.json")

    evidence_tool_records = [file_record(path) for path in EVIDENCE_TOOLS]
    test_output = next(item["output"] for item in formal_commands if item["name"] == "template-and-affected-regressions")
    passed_match = re.search(r"\b(\d+) passed\b", test_output)
    if passed_match is None:
        raise RuntimeError("正式测试输出未证明测试全部通过")
    passed_count = int(passed_match.group(1))

    manifest = {
        "schemaVersion": 1,
        "templateId": "template_22",
        "candidateId": candidate_id,
        "status": "FROZEN_READY_FOR_CONFIRMATION",
        "branch": branch,
        "repositoryRoot": str(REPOSITORY_ROOT),
        "baseCommit": head,
        "gitCommitCreated": False,
        "reference": {
            "path": str(REFERENCE_PATH),
            "sha256": REFERENCE_SHA256,
        },
        "candidateSha256": candidate_digest,
        "files": candidate_records,
        "evidenceTools": evidence_tool_records,
        "formalCommandEvidence": "formal-command-results.json",
    }
    g8_summary = {
        "schemaVersion": 1,
        "templateId": "template_22",
        "candidateId": candidate_id,
        "stage": "G8",
        "status": "PASS",
        "goalStatus": "READY_FOR_CONFIRMATION",
        "branch": branch,
        "repositoryRoot": str(REPOSITORY_ROOT),
        "baseCommit": head,
        "candidateSha256": candidate_digest,
        "productionSlideCount": 18,
        "productionAssetCount": 9,
        "checks": {
            "templateAndAffectedRegressionTests": f"{passed_count} passed (current candidate)",
            "frontendTypeCheck": "PASS (current candidate)",
            "deterministicProductionBuild": True,
            "realHandlerAndPersistentWorker": "PASS",
            "fixedMockUpstream": True,
            "isolatedTemporarySqlite": True,
            "realTextModelCalls": False,
            "realImageModelCalls": False,
            "fivePageTypesGenerated": True,
            "fourViewports": "PASS",
            "visualInspection": "PASS",
            "titleAndBodyEditing": "PASS",
            "contentImageReplacement": "PASS",
            "decorationProtection": "PASS",
            "jsonSaveReload": "PASS",
            "pptxExportReimport": "PASS",
            "expectedTextRetained": True,
            "expectedTextCount": evidence["browser"].get("expectedTextCount"),
            "projectOrderRetained": True,
            "contentImageRetainedAfterPptxReimport": True,
            "landscapePortraitSquareReplacement": "PASS",
            "centerCropRanges": "PASS",
            "invalidInputErrorCodes": "PASS",
            "templateRegistrationAndCover": "PASS",
            "branchRuntime": "PASS",
        },
        "urls": {
            "selector": "http://127.0.0.1:5778/app",
            "editor": "http://127.0.0.1:5778/editor",
            "api": "http://127.0.0.1:6800",
        },
        "knownLimitations": evidence["runtimeProcess"].get("knownLimitations", []),
        "humanConfirmationRequired": True,
        "goalComplete": False,
        "gitCommitPushPrMergeAuthorized": False,
    }
    progress = {
        "schemaVersion": 1,
        "templateId": "template_22",
        "candidateId": candidate_id,
        "branch": branch,
        "currentStage": "G8",
        "stages": {f"G{index}": "PASS" for index in range(9)},
        "goalStatus": "READY_FOR_CONFIRMATION",
        "humanConfirmation": "PENDING",
        "gitDelivery": "NOT_AUTHORIZED",
    }

    outputs = {
        "formal-command-results.json": {
            "schemaVersion": 1,
            "templateId": "template_22",
            "candidateId": candidate_id,
            "candidateSha256": candidate_digest,
            "status": "PASS",
            "commands": formal_commands,
        },
        "frozen-candidate-manifest.json": manifest,
        "g8-summary.json": g8_summary,
        "progress.json": progress,
    }
    for filename, value in outputs.items():
        (EVIDENCE_ROOT / filename).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(g8_summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

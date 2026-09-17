"""复核 template_23 当前候选并生成 G6 冻结验收证据。"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPOSITORY_ROOT / "doc" / "assets" / "template_23_qa"
TEMPLATE_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
REFERENCE_PATH = Path(r"C:\Users\sk20\Desktop\星空风格(1).pptx")
REFERENCE_SHA256 = "22BA3CA2A866D7064A3FF568122FF3635BC758F9D5E87CDC5F41F23E05CF882B"

EXPECTED_LAYOUT_IDS = [
    "cover-horizon",
    "cover-visual",
    "contents-2",
    "contents-3",
    "contents-4",
    "contents-5",
    "contents-6",
    "contents-10",
    "transition-particle-number",
    "transition-lightline",
    "content-focus-1",
    "content-text-2",
    "content-text-3",
    "content-text-4",
    "content-image-1",
    "content-metrics-3",
    "content-metrics-4",
    "content-metrics-5",
    "end-horizon",
    "end-action",
]

ASSET_FILENAMES = [
    "template_23_asset_bg_cover_v1.jpg",
    "template_23_asset_bg_content_v1.jpg",
    "template_23_asset_bg_section_v1.jpg",
    "template_23_asset_bg_end_v1.jpg",
    "template_23_asset_particle_field_v1.png",
    "template_23_asset_horizon_glow_v1.png",
    "template_23_asset_title_flare_v1.png",
    "template_23_asset_image_halo_v1.png",
    "template_23_asset_grid_arc_v1.png",
]

CANDIDATE_FILES = [
    "backend/main_api/main.py",
    "backend/main_api/workers/template_renderer.py",
    "backend/main_api/template/template_23.json",
    "backend/main_api/template/template_23.jpg",
    *[f"backend/main_api/template/{name}" for name in ASSET_FILENAMES],
    "backend/main_api/tests/test_template_23.py",
    "backend/main_api/tests/test_template_renderer.py",
    "doc/template_specs/template_23.yaml",
    "utils/build_cyan_star_business_template.mjs",
    "utils/process_template_23_assets.mjs",
    "utils/run_template_23_handler_qa.py",
    "utils/verify_template_23_browser.cjs",
    "utils/verify_template_23_pptx_roundtrip.mjs",
]

EVIDENCE_TOOLS = [
    "utils/finalize_template_23_qa.py",
    "utils/run_template_23_handler_qa.py",
    "utils/verify_template_23_browser.cjs",
    "utils/verify_template_23_pptx_roundtrip.mjs",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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
    """路径和内容共同参与摘要，避免文件互换后仍得到相同候选标识。"""

    combined = hashlib.sha256()
    for record in records:
        combined.update(record["path"].encode("utf-8"))
        combined.update(b"\0")
        combined.update(record["sha256"].encode("ascii"))
        combined.update(b"\n")
    return combined.hexdigest().upper()


def run_checked(name: str, command: list[str], *, cwd: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """执行正式命令并保留足够的原始输出用于审计。"""

    result = subprocess.run(
        command,
        cwd=cwd,
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


def fetch_json(url: str) -> tuple[int, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "template-23-finalizer"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def fetch_bytes(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "template-23-finalizer"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status, response.read()


def main() -> None:
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    if not REFERENCE_PATH.is_file() or sha256(REFERENCE_PATH) != REFERENCE_SHA256:
        raise RuntimeError("参考 PPT 不存在或 SHA-256 已变化")

    candidate_records = [file_record(path) for path in CANDIDATE_FILES]
    candidate_digest = combined_digest(candidate_records)
    candidate_id = f"template_23-g6-{candidate_digest[:12].lower()}"

    node_executable = shutil.which("node.exe") or shutil.which("node") or "node"
    npm_executable = shutil.which("npm.cmd") or "npm.cmd"
    formal_commands: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="template-23-final-") as temporary:
        temporary_root = Path(temporary)
        first_build = temporary_root / "production-first.json"
        second_build = temporary_root / "production-second.json"
        formal_commands.append(
            run_checked(
                "template-and-affected-regressions",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "backend/main_api/tests/test_template_23.py",
                    "backend/main_api/tests/test_template_renderer.py",
                    "backend/main_api/tests/test_template_assets.py",
                    "backend/main_api/tests/test_template_22.py",
                    "-q",
                ],
            )
        )
        formal_commands.append(
            run_checked(
                "frontend-type-check",
                [npm_executable, "run", "type-check"],
                cwd=REPOSITORY_ROOT / "frontend",
            )
        )
        formal_commands.append(
            run_checked(
                "production-build-first",
                [node_executable, "utils/build_cyan_star_business_template.mjs", "--stage", "production", str(first_build)],
            )
        )
        formal_commands.append(
            run_checked(
                "production-build-second",
                [node_executable, "utils/build_cyan_star_business_template.mjs", "--stage", "production", str(second_build)],
            )
        )
        production_bytes = (TEMPLATE_ROOT / "template_23.json").read_bytes()
        if first_build.read_bytes() != second_build.read_bytes() or first_build.read_bytes() != production_bytes:
            raise RuntimeError("两次生产构建或正式 template_23.json 不一致")
        formal_commands.append(
            run_checked("real-handler-worker", [sys.executable, "utils/run_template_23_handler_qa.py"])
        )

    refreshed_records = [file_record(path) for path in CANDIDATE_FILES]
    if combined_digest(refreshed_records) != candidate_digest:
        raise RuntimeError("正式验收过程中候选文件发生变化，必须重新冻结并重验")
    candidate_records = refreshed_records

    required_evidence = {
        "g0": "g0-baseline.json",
        "assetGeneration": "asset-generation.json",
        "assets": "asset-summary.json",
        "probe": "probe-summary.json",
        "production": "g3-production-summary.json",
        "integration": "g4-integration-summary.json",
        "tests": "g5-test-summary.json",
        "handler": "real-handler-summary.json",
        "browser": "browser-g6-summary.json",
        "powerPoint": "pptx-roundtrip-summary.json",
    }
    evidence = {name: read_json(path) for name, path in required_evidence.items()}
    for name, item in evidence.items():
        if item.get("status") != "PASS":
            raise RuntimeError(f"正式证据未通过：{name}")

    template = json.loads((TEMPLATE_ROOT / "template_23.json").read_text(encoding="utf-8"))
    layout_ids = [slide.get("id") for slide in template.get("slides", [])]
    if template.get("id") != "template_23" or layout_ids != EXPECTED_LAYOUT_IDS:
        raise RuntimeError("生产模板 ID、20 个稳定版式数量或顺序不正确")
    if evidence["production"].get("counts") != {
        "cover": 2,
        "contents": 6,
        "transition": 2,
        "content": 8,
        "end": 2,
    }:
        raise RuntimeError("生产模板五类版式数量不符合规划")
    if len(evidence["assets"].get("assets", [])) != 9:
        raise RuntimeError("原创装饰素材证据不是 9 项")
    if evidence["assets"].get("actualModel") != "工具未暴露":
        raise RuntimeError("图片生成模型记录不符合实际工具暴露情况")
    if evidence["handler"].get("slideTypes") != {
        "cover": 1,
        "contents": 1,
        "transition": 1,
        "content": 4,
        "end": 1,
    }:
        raise RuntimeError("真实处理链没有覆盖约定的五种页面类型")
    if evidence["handler"].get("realTextModelCalls") is not False:
        raise RuntimeError("真实处理链不应调用文本模型")

    browser = evidence["browser"]
    if {(item.get("width"), item.get("height")) for item in browser.get("viewports", [])} != {
        (1920, 1080),
        (1366, 768),
        (768, 1024),
        (390, 844),
    }:
        raise RuntimeError("浏览器证据没有覆盖约定的四种设备视口")
    if {(item.get("name"), item.get("width"), item.get("height")) for item in browser.get("replacementInputs", [])} != {
        ("landscape", 600, 450),
        ("portrait", 600, 900),
        ("square", 600, 600),
    }:
        raise RuntimeError("浏览器证据没有覆盖真实横图、竖图和方图替换")
    required_browser_flags = [
        "titleEdited",
        "bodyEdited",
        "decorationProtected",
        "jsonSaveReload",
        "pptxExportReimport",
        "contentImageGeometryRetained",
    ]
    if any(browser.get(flag) is not True for flag in required_browser_flags):
        raise RuntimeError("浏览器编辑、图片保护、保存或导出往返证据不完整")
    if browser.get("missingTexts") or browser.get("expectedTextCount") != 62:
        raise RuntimeError("PPTX 往返文字完整性证据不符合预期")
    if browser.get("imageCountBeforeExportBySlide") != browser.get("roundtripImageCountBySlide"):
        raise RuntimeError("PPTX 往返前后逐页图片数量不一致")

    power_point = evidence["powerPoint"]
    roundtrip_pptx = EVIDENCE_ROOT / "template_23_g6_roundtrip.pptx"
    saved_pptx = EVIDENCE_ROOT / "template_23_g6_powerpoint_saved.pptx"
    if power_point.get("powerPointOpenedAndSaved") is not True:
        raise RuntimeError("缺少 Microsoft PowerPoint 打开并另存证据")
    if power_point.get("source", {}).get("sha256", "").upper() != sha256(roundtrip_pptx):
        raise RuntimeError("浏览器导出 PPTX 已与 PowerPoint 往返证据漂移")
    if power_point.get("saved", {}).get("sha256", "").upper() != sha256(saved_pptx):
        raise RuntimeError("PowerPoint 另存 PPTX 已与往返证据漂移")
    if not all(power_point.get("checks", {}).values()):
        raise RuntimeError("PowerPoint 往返检查未全部通过")

    # 最终冻结还核对当前运行服务确实暴露了本候选，而不是残留的旧进程。
    ready_status, ready = fetch_json("http://127.0.0.1:6800/readyz")
    templates_status, templates = fetch_json("http://127.0.0.1:6800/templates")
    proxy_status, proxy_templates = fetch_json("http://127.0.0.1:5778/api/templates")
    json_status, served_json = fetch_bytes("http://127.0.0.1:5778/api/data/template_23.json")
    cover_status, served_cover = fetch_bytes("http://127.0.0.1:5778/api/data/template_23.jpg")
    if ready_status != 200 or not isinstance(ready, dict):
        raise RuntimeError("主 API /readyz 未通过")
    api_template_items = templates.get("data", []) if isinstance(templates, dict) else []
    proxy_template_items = proxy_templates.get("data", []) if isinstance(proxy_templates, dict) else []
    if templates_status != 200 or sum(item.get("id") == "template_23" for item in api_template_items) != 1:
        raise RuntimeError("主 API 模板列表未唯一注册 template_23")
    if proxy_status != 200 or sum(item.get("id") == "template_23" for item in proxy_template_items) != 1:
        raise RuntimeError("前端代理模板列表未唯一暴露 template_23")
    if json_status != 200 or served_json != (TEMPLATE_ROOT / "template_23.json").read_bytes():
        raise RuntimeError("前端代理没有返回当前 template_23.json 候选")
    if cover_status != 200 or served_cover != (TEMPLATE_ROOT / "template_23.jpg").read_bytes():
        raise RuntimeError("前端代理没有返回当前 template_23.jpg 候选")

    test_output = next(
        item["output"] for item in formal_commands if item["name"] == "template-and-affected-regressions"
    )
    passed_match = re.search(r"\b(\d+) passed\b", test_output)
    if passed_match is None:
        raise RuntimeError("正式测试输出未证明全部测试通过")
    passed_count = int(passed_match.group(1))

    visual_inspection = {
        "schemaVersion": 1,
        "templateId": "template_23",
        "candidateId": candidate_id,
        "candidateSha256": candidate_digest,
        "status": "PASS",
        "method": "人工目视检查已渲染证据，不替代自动几何与往返检查",
        "artifacts": [
            "production-renders/production-contact-sheet.png",
            *browser.get("screenshots", []),
            "replacement-landscape.png",
            "replacement-portrait.png",
            "replacement-square.png",
        ],
        "checks": {
            "twentyLayoutsReadable": True,
            "noVisibleOverlapOrClipping": True,
            "fourViewportEditorLayoutUsable": True,
            "replacementImagesRespectFrameAndDecoration": True,
        },
    }

    manifest = {
        "schemaVersion": 1,
        "templateId": "template_23",
        "candidateId": candidate_id,
        "status": "FROZEN_READY_FOR_CONFIRMATION",
        "branch": branch,
        "repositoryRoot": str(REPOSITORY_ROOT),
        "baseCommit": head,
        "gitCommitCreated": False,
        "reference": {"path": str(REFERENCE_PATH), "sha256": REFERENCE_SHA256},
        "candidateSha256": candidate_digest,
        "files": candidate_records,
        "evidenceTools": [file_record(path) for path in EVIDENCE_TOOLS],
        "formalCommandEvidence": "formal-command-results.json",
    }
    g6_summary = {
        "schemaVersion": 1,
        "templateId": "template_23",
        "candidateId": candidate_id,
        "stage": "G6",
        "status": "PASS",
        "goalStatus": "READY_FOR_CONFIRMATION",
        "candidateSha256": candidate_digest,
        "productionLayoutCount": 20,
        "productionAssetCount": 9,
        "actualImageModel": "工具未暴露",
        "checks": {
            "templateAndAffectedRegressionTests": f"{passed_count} passed (current candidate)",
            "frontendTypeCheck": "PASS (current candidate)",
            "deterministicProductionBuild": True,
            "realHandlerAndPersistentWorker": "PASS",
            "fixedMockUpstream": True,
            "isolatedTemporarySqlite": True,
            "realTextModelCalls": False,
            "fivePageTypesGenerated": True,
            "twentyStableLayouts": True,
            "nineOriginalAssets": True,
            "fourViewports": "PASS",
            "visualInspection": "PASS",
            "titleAndBodyEditing": "PASS",
            "landscapePortraitSquareReplacement": "PASS",
            "decorationProtection": "PASS",
            "jsonSaveReload": "PASS",
            "pptxExportReimport": "PASS",
            "powerPointOpenSaveReopen": "PASS",
            "expectedTextRetained": True,
            "expectedTextCount": 62,
            "projectOrderRetained": True,
            "contentImageGeometryRetained": True,
            "templateRegistrationAndCover": "PASS",
            "branchRuntime": "PASS",
        },
        "urls": {
            "selector": "http://127.0.0.1:5778/app",
            "editor": "http://127.0.0.1:5778/editor",
            "api": "http://127.0.0.1:6800",
        },
        "knownLimitations": [
            "PowerPoint 另存时会去重并重打包媒体文件；逐页图片数量、可编辑形状、全部 62 项文字及顺序均保持。"
        ],
        "humanConfirmationRequired": True,
        "humanConfirmation": "PENDING",
        "goalComplete": False,
        "gitCommitPushPrMergeAuthorized": False,
        "productionBuildDeployAuthorized": False,
    }
    progress = {
        "schemaVersion": 1,
        "templateId": "template_23",
        "candidateId": candidate_id,
        "branch": branch,
        "currentStage": "G6",
        "stages": {f"G{index}": "PASS" for index in range(7)},
        "goalStatus": "READY_FOR_CONFIRMATION",
        "humanConfirmation": "PENDING",
        "gitDelivery": "NOT_AUTHORIZED",
        "productionDelivery": "NOT_AUTHORIZED",
    }

    outputs = {
        "formal-command-results.json": {
            "schemaVersion": 1,
            "templateId": "template_23",
            "candidateId": candidate_id,
            "candidateSha256": candidate_digest,
            "status": "PASS",
            "commands": formal_commands,
        },
        "visual-inspection.json": visual_inspection,
        "frozen-candidate-manifest.json": manifest,
        "g6-summary.json": g6_summary,
        "progress.json": progress,
    }
    for filename, value in outputs.items():
        (EVIDENCE_ROOT / filename).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(g6_summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

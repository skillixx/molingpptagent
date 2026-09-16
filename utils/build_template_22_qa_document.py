"""使用固定数据生成 template_22 探针或生产 QA 文档。"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import mimetypes
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
# 从任意工作目录运行时都使用当前仓库代码，避免误导入其他环境中的同名包。
sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer


QA_ROOT = REPOSITORY_ROOT / "doc" / "assets" / "template_22_qa"
PROBE_ASSET_ROOT = QA_ROOT / "probe-assets"
BUILDER = REPOSITORY_ROOT / "utils" / "build_peach_ink_template.mjs"


def _data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _probe_document() -> dict[str, object]:
    """在隔离目录渲染探针，并把临时图片嵌入文档供浏览器离线验证。"""

    with tempfile.TemporaryDirectory(prefix="template22-probe-") as temporary:
        root = Path(temporary)
        template_path = root / "template_22.json"
        result = subprocess.run(
            ["node", str(BUILDER), "--stage", "probe", str(template_path)],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
        template = json.loads(template_path.read_text(encoding="utf-8"))
        for filename in template["metadata"]["probeAssetFiles"]:
            shutil.copyfile(PROBE_ASSET_ROOT / filename, root / filename)

        renderer = PresentationTemplateRenderer(root)
        semantic_slides = [
            {
                "type": "cover",
                "data": {"title": "桃夭墨韵商务汇报", "text": "探针编辑与导出验证"},
            },
            {
                "type": "content",
                "data": {
                    "title": "普通图文验证",
                    "items": [{"title": "完整标题", "text": "普通图文正文必须完整保留。"}],
                },
                "images": [{
                    "src": "https://example.invalid/rect-image.jpg",
                    "width": 1600,
                    "height": 900,
                }],
            },
            {
                "type": "content",
                "data": {
                    "title": "圆形图片验证",
                    "variant": "circle",
                    "items": [{"title": "圆形内容图", "text": "圆形换图和往返后仍需保持裁切。"}],
                },
                "images": [{
                    "src": "https://example.invalid/circle-image.jpg",
                    "width": 900,
                    "height": 1600,
                }],
            },
        ]
        document = renderer.render(
            template_id="template_22",
            semantic_slides=semantic_slides,
            task_id="template-22-fixed-probe",
            fallback_title="桃夭墨韵商务汇报",
        )
        embedded = copy.deepcopy(document)
        replacements = {
            f"/api/data/{filename}": _data_url(PROBE_ASSET_ROOT / filename)
            for filename in template["metadata"]["probeAssetFiles"]
        }
        content_url = _data_url(PROBE_ASSET_ROOT / "template_22_probe_content.jpg")
        for slide in embedded["slides"]:
            for element in slide.get("elements", []):
                if element.get("type") != "image":
                    continue
                source = element.get("src")
                element["src"] = replacements.get(source, content_url)
        return embedded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["probe"], default="probe")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    document = _probe_document()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output.resolve())


if __name__ == "__main__":
    main()

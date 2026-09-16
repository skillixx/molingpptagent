"""把图片生成输出规范化为 template_22 的发布素材。"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_ROOT = REPOSITORY_ROOT / "doc" / "assets" / "template_22_qa" / "originals"
OUTPUT_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
SUMMARY_PATH = REPOSITORY_ROOT / "doc" / "assets" / "template_22_qa" / "asset-summary.json"
SELECTOR_SOURCE = REPOSITORY_ROOT / "doc" / "assets" / "template_22_qa" / "sample-renders" / "cover-selector-source.png"
SELECTOR_OUTPUT = OUTPUT_ROOT / "template_22.jpg"

ASSETS = {
    "template_22_asset_bg_cover_v1.jpg": {
        "source": "template_22_asset_bg_cover_v1_original.png",
        "size": (1920, 1080),
        "mode": "RGB",
        "maxBytes": 450_000,
    },
    "template_22_asset_bg_content_v1.jpg": {
        "source": "template_22_asset_bg_content_v1_original.png",
        "size": (1920, 1080),
        "mode": "RGB",
        "maxBytes": 280_000,
    },
    "template_22_asset_bg_section_v1.jpg": {
        "source": "template_22_asset_bg_section_v1_original.png",
        "size": (1920, 1080),
        "mode": "RGB",
        "maxBytes": 350_000,
    },
    "template_22_asset_bg_end_v1.jpg": {
        "source": "template_22_asset_bg_end_v1_original.png",
        "size": (1920, 1080),
        "mode": "RGB",
        "maxBytes": 420_000,
    },
    "template_22_asset_scroll_roll_v1.png": {
        "source": "template_22_asset_scroll_roll_v1_original.png",
        "size": (1500, 900),
        "mode": "RGBA",
        "maxBytes": 900_000,
    },
    "template_22_asset_ink_title_frame_v1.png": {
        "source": "template_22_asset_ink_title_frame_v1_original.png",
        "size": (1200, 320),
        "mode": "RGBA",
        "maxBytes": 450_000,
    },
    "template_22_asset_ink_circle_frame_v1.png": {
        "source": "template_22_asset_ink_circle_frame_v1_original.png",
        "size": (900, 900),
        "mode": "RGBA",
        "maxBytes": 750_000,
    },
    "template_22_asset_ink_brush_band_v1.png": {
        "source": "template_22_asset_ink_brush_band_v1_original.png",
        "size": (1800, 360),
        "mode": "RGBA",
        "maxBytes": 650_000,
    },
    "template_22_asset_petal_sweep_v1.png": {
        "source": "template_22_asset_petal_sweep_v1_original.png",
        "size": (1200, 900),
        "mode": "RGBA",
        "maxBytes": 700_000,
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _save_jpeg(image: Image.Image, output: Path, max_bytes: int) -> int:
    """在既定体积内保留尽可能高的 JPEG 质量。"""

    selected_quality = 40
    for quality in range(92, 39, -2):
        image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
        if output.stat().st_size <= max_bytes:
            selected_quality = quality
            break
    else:
        image.save(output, format="JPEG", quality=selected_quality, optimize=True, progressive=True)
    if output.stat().st_size > max_bytes:
        raise RuntimeError(f"{output.name} 超过体积限制: {output.stat().st_size} > {max_bytes}")
    return selected_quality


def _save_png(image: Image.Image, output: Path, max_bytes: int) -> None:
    image.save(output, format="PNG", optimize=True, compress_level=9)
    if output.stat().st_size > max_bytes:
        raise RuntimeError(f"{output.name} 超过体积限制: {output.stat().st_size} > {max_bytes}")


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []
    for filename, contract in ASSETS.items():
        source = ORIGINAL_ROOT / str(contract["source"])
        output = OUTPUT_ROOT / filename
        target_size = tuple(contract["size"])
        max_bytes = int(contract["maxBytes"])
        with Image.open(source) as opened:
            if contract["mode"] == "RGB":
                normalized = ImageOps.fit(
                    opened.convert("RGB"),
                    target_size,
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
                quality = _save_jpeg(normalized, output, max_bytes)
                alpha_range = None
            else:
                rgba = opened.convert("RGBA")
                alpha_range = rgba.getchannel("A").getextrema()
                if alpha_range[0] == 255:
                    raise RuntimeError(f"{source.name} 没有真实透明像素")
                contained = ImageOps.contain(rgba, target_size, method=Image.Resampling.LANCZOS)
                normalized = Image.new("RGBA", target_size, (0, 0, 0, 0))
                position = (
                    (target_size[0] - contained.width) // 2,
                    (target_size[1] - contained.height) // 2,
                )
                normalized.alpha_composite(contained, position)
                _save_png(normalized, output, max_bytes)
                quality = None
                alpha_range = normalized.getchannel("A").getextrema()
        summary.append({
            "filename": filename,
            "source": str(source.relative_to(REPOSITORY_ROOT)).replace("\\", "/"),
            "size": list(target_size),
            "mode": str(contract["mode"]),
            "bytes": output.stat().st_size,
            "maxBytes": max_bytes,
            "jpegQuality": quality,
            "alphaRange": list(alpha_range) if alpha_range is not None else None,
            "sha256": _sha256(output),
        })

    selector_summary = None
    if SELECTOR_SOURCE.is_file():
        with Image.open(SELECTOR_SOURCE) as opened:
            selector = ImageOps.fit(
                opened.convert("RGB"),
                (960, 540),
                method=Image.Resampling.LANCZOS,
            )
            quality = _save_jpeg(selector, SELECTOR_OUTPUT, 150_000)
        selector_summary = {
            "filename": SELECTOR_OUTPUT.name,
            "size": [960, 540],
            "mode": "RGB",
            "bytes": SELECTOR_OUTPUT.stat().st_size,
            "maxBytes": 150_000,
            "jpegQuality": quality,
            "sha256": _sha256(SELECTOR_OUTPUT),
        }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps({
            "schemaVersion": 1,
            "templateId": "template_22",
            "status": "PASS",
            "generationTool": "built-in image generation",
            "requestedGenerator": "GPT2 图片模板",
            "actualModel": "工具未暴露",
            "assets": summary,
            "selectorCover": selector_summary,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(SUMMARY_PATH)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        raise

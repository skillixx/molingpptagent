"""把图片生成结果确定性处理为蓝菱商务汇报模板的发布素材。"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageOps


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPOSITORY_ROOT / "backend" / "main_api" / "template"
ASSETS = {
    "template_17_asset_bg_light_v1.jpg": {
        "source": "exec-3e5854d4-75ab-4f95-80d8-c964dbd823b8.png",
        "size": (1920, 1080),
        "mode": "RGB",
        "limit": 350_000,
    },
    "template_17_asset_world_map_dots_v1.png": {
        "source": "exec-bc6e3f9d-06ba-4d6c-9db7-8eb4b33e20f5.png",
        "size": (1600, 900),
        "mode": "RGBA",
        "limit": 650_000,
        "map": True,
    },
    "template_17_asset_cover_diamond_cluster_v1.png": {
        "source": "exec-9897cc24-ed3a-4fac-9825-e3a9c52204cb.png",
        "size": (1400, 1000),
        "mode": "RGBA",
        "limit": 1_000_000,
    },
    "template_17_asset_diamond_footer_v1.png": {
        "source": "exec-057e9197-f472-4b6b-b5f6-efd9b9c3db2f.png",
        "size": (1600, 520),
        "mode": "RGBA",
        "limit": 900_000,
    },
    "template_17_asset_diamond_corner_v1.png": {
        "source": "exec-2929b547-2fdc-457e-a060-434273c2b1da.png",
        "size": (900, 900),
        "mode": "RGBA",
        "limit": 700_000,
    },
}


def _fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """使用中心裁切保持比例，避免把生成的菱形拉伸变形。"""
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def _normalize_alpha(image: Image.Image) -> Image.Image:
    """确保透明素材同时包含全透明与全不透明像素。"""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    extrema = alpha.getextrema()
    if extrema == (0, 255):
        return rgba
    maximum = max(1, extrema[1])
    alpha = alpha.point(lambda value: min(255, round(value * 255 / maximum)))
    rgba.putalpha(alpha)
    return rgba


def _recolor_map(image: Image.Image) -> Image.Image:
    """把地图压成浅灰蓝点阵，避免在浅色背景上抢占正文层级。"""
    rgba = _normalize_alpha(image)
    alpha = rgba.getchannel("A")
    pixels = Image.new("RGBA", rgba.size, (188, 205, 221, 0))
    pixels.putalpha(alpha.point(lambda value: 255 if value >= 28 else 0))
    return pixels


def _save_jpeg(image: Image.Image, target: Path, limit: int) -> None:
    """逐级降低质量直到满足体积上限，同时保持 4:4:4 颜色。"""
    rgb = image.convert("RGB")
    for quality in range(88, 54, -3):
        rgb.save(target, "JPEG", quality=quality, optimize=True, progressive=True, subsampling=0)
        if target.stat().st_size <= limit:
            return
    raise RuntimeError(f"JPEG 无法压缩到限制内: {target.name} ({target.stat().st_size} > {limit})")


def process(generated_root: Path, output_root: Path) -> None:
    """按显式输入目录处理素材，避免工具绑定到单一机器会话路径。"""
    output_root.mkdir(parents=True, exist_ok=True)
    for filename, contract in ASSETS.items():
        source = generated_root / str(contract["source"])
        if not source.is_file():
            raise FileNotFoundError(source)
        target = output_root / filename
        with Image.open(source) as source_image:
            image = _fit(source_image, contract["size"])
            if contract["mode"] == "RGB":
                _save_jpeg(image, target, contract["limit"])
            else:
                image = _recolor_map(image) if contract.get("map") else _normalize_alpha(image)
                image.save(target, "PNG", optimize=True, compress_level=9)
                if target.stat().st_size > contract["limit"]:
                    raise RuntimeError(
                        f"PNG 超出体积限制: {target.name} ({target.stat().st_size} > {contract['limit']})"
                    )

        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        with Image.open(target) as released:
            alpha = released.getchannel("A").getextrema() if released.mode == "RGBA" else None
            print(
                f"{target.name}|size={released.size}|mode={released.mode}|alpha={alpha}|"
                f"bytes={target.stat().st_size}|sha256={digest}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="处理蓝菱商务汇报模板的图片生成输出")
    parser.add_argument("--generated-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    arguments = parser.parse_args()
    process(arguments.generated_root.resolve(), arguments.output_root.resolve())

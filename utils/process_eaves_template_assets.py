"""把 imagegen 原始输出标准化为 template_18 的发布素材。"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


ASSETS = {
    "template_18_asset_bg_cover_v1.jpg": (
        "template_18_asset_bg_cover_v1_original.png",
        (1920, 1080),
        "RGB",
        400_000,
    ),
    "template_18_asset_bg_section_v1.jpg": (
        "template_18_asset_bg_section_v1_original.png",
        (1920, 1080),
        "RGB",
        320_000,
    ),
    "template_18_asset_bg_end_v1.jpg": (
        "template_18_asset_bg_end_v1_original.png",
        (1920, 1080),
        "RGB",
        400_000,
    ),
    "template_18_asset_rooftile_band_v1.png": (
        "template_18_asset_rooftile_band_v1_original.png",
        (1800, 620),
        "RGBA",
        1_000_000,
    ),
    "template_18_asset_eaves_corner_v1.png": (
        "template_18_asset_eaves_corner_v1_original.png",
        (1200, 900),
        "RGBA",
        900_000,
    ),
    "template_18_asset_plum_branch_v1.png": (
        "template_18_asset_plum_branch_v1_final.png",
        (1600, 650),
        "RGBA",
        850_000,
    ),
    "template_18_asset_crane_pair_v1.png": (
        "template_18_asset_crane_pair_v1_original.png",
        (1100, 700),
        "RGBA",
        750_000,
    ),
    "template_18_asset_medallion_v1.png": (
        "template_18_asset_medallion_v1_transparent.png",
        (900, 900),
        "RGBA",
        600_000,
    ),
}


def _fit_rgba(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """等比缩放并居中到透明画布，避免拉伸建筑和花枝。"""

    converted = image.convert("RGBA")
    contained = ImageOps.contain(converted, size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
    canvas.alpha_composite(contained, offset)
    return canvas


def _save_jpeg(image: Image.Image, output: Path, size: tuple[int, int], limit: int) -> None:
    """以逐级质量压缩背景，达到体积门禁但不改变构图。"""

    prepared = ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS)
    for quality in range(88, 46, -4):
        prepared.save(output, "JPEG", quality=quality, optimize=True, progressive=True)
        if output.stat().st_size <= limit:
            return
    raise RuntimeError(f"JPEG 体积仍超限: {output.name} {output.stat().st_size}>{limit}")


def _save_png(image: Image.Image, output: Path, size: tuple[int, int], limit: int) -> None:
    """保留真实 Alpha；必要时减少不可见 RGB 噪声以提高 PNG 压缩率。"""

    prepared = _fit_rgba(image, size)
    alpha = prepared.getchannel("A")
    minimum, maximum = alpha.getextrema()
    if minimum != 0 or maximum <= 0:
        raise RuntimeError(f"透明素材缺少有效 Alpha 范围: {output.name} {(minimum, maximum)}")
    if maximum < 255:
        # 高质量缩放可能把完全不透明像素插值为 250～254；线性拉伸恢复发布契约的完整范围。
        alpha = alpha.point(lambda value: min(255, round(value * 255 / maximum)))
        prepared.putalpha(alpha)

    # 完全透明像素统一清零，避免隐藏色彩显著放大文件。
    pixels = prepared.load()
    for y in range(prepared.height):
        for x in range(prepared.width):
            red, green, blue, opacity = pixels[x, y]
            if opacity == 0:
                pixels[x, y] = (0, 0, 0, 0)

    prepared.save(output, "PNG", optimize=True, compress_level=9)
    if output.stat().st_size <= limit:
        return

    # 颜色量化后转回 RGBA，仍保留项目契约要求的 RGBA 模式。
    quantized = prepared.quantize(colors=128, method=Image.Quantize.FASTOCTREE).convert("RGBA")
    quantized_alpha = quantized.getchannel("A")
    quantized_minimum, quantized_maximum = quantized_alpha.getextrema()
    if quantized_minimum != 0 or quantized_maximum <= 0:
        raise RuntimeError(f"量化后 Alpha 无效: {output.name} {(quantized_minimum, quantized_maximum)}")
    if quantized_maximum < 255:
        quantized_alpha = quantized_alpha.point(
            lambda value: min(255, round(value * 255 / quantized_maximum))
        )
        quantized.putalpha(quantized_alpha)
    quantized.save(output, "PNG", optimize=True, compress_level=9)
    if output.stat().st_size > limit:
        raise RuntimeError(f"PNG 体积仍超限: {output.name} {output.stat().st_size}>{limit}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for output_name, (source_name, size, mode, limit) in ASSETS.items():
        source = args.original_dir / source_name
        output = args.output_dir / output_name
        if not source.is_file():
            raise FileNotFoundError(source)
        with Image.open(source) as image:
            if mode == "RGB":
                _save_jpeg(image, output, size, limit)
            else:
                if image.mode != "RGBA" or image.getchannel("A").getextrema() != (0, 255):
                    raise RuntimeError(f"原始素材不是真实 RGBA: {source.name} {image.mode}")
                _save_png(image, output, size, limit)
        print(f"{output.name}\t{output.stat().st_size}")


if __name__ == "__main__":
    main()

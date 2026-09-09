"""把 imagegen 原始输出标准化为 template_19 的发布素材。"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


ASSETS = {
    "template_19_asset_bg_cover_v1.jpg": (
        "template_19_asset_bg_cover_v1_original.png",
        (1920, 1080),
        "RGB",
        450_000,
    ),
    "template_19_asset_bg_content_v1.jpg": (
        "template_19_asset_bg_content_v1_original.png",
        (1920, 1080),
        "RGB",
        250_000,
    ),
    "template_19_asset_bg_section_v1.jpg": (
        "template_19_asset_bg_section_v1_original.png",
        (1920, 1080),
        "RGB",
        350_000,
    ),
    "template_19_asset_bg_end_v1.jpg": (
        "template_19_asset_bg_end_v1_original.png",
        (1920, 1080),
        "RGB",
        400_000,
    ),
    "template_19_asset_eucalyptus_corner_upper_v1.png": (
        "template_19_asset_eucalyptus_corner_v1_round2.png",
        (1400, 900),
        "RGBA",
        800_000,
    ),
    "template_19_asset_eucalyptus_corner_v1.png": (
        "template_19_asset_eucalyptus_corner_v1_round2.png",
        (1400, 900),
        "RGBA",
        800_000,
    ),
    "template_19_asset_eucalyptus_sweep_v1.png": (
        "template_19_asset_eucalyptus_sweep_v1_original.png",
        (1800, 650),
        "RGBA",
        950_000,
    ),
    "template_19_asset_fern_spray_v1.png": (
        "template_19_asset_fern_spray_v1_original.png",
        (1400, 950),
        "RGBA",
        850_000,
    ),
    "template_19_asset_leaf_medallion_v1.png": (
        "template_19_asset_leaf_medallion_v1_round2.png",
        (900, 900),
        "RGBA",
        600_000,
    ),
}


def _fit_rgba(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """等比缩放到透明画布，避免拉伸叶片和水彩笔触。"""

    converted = image.convert("RGBA")
    contained = ImageOps.contain(converted, size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
    canvas.alpha_composite(contained, offset)
    return canvas


def _save_jpeg(image: Image.Image, output: Path, size: tuple[int, int], limit: int) -> None:
    """在不改变构图比例的前提下压缩背景到发布体积。"""

    prepared = ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS)
    for quality in range(90, 42, -4):
        prepared.save(output, "JPEG", quality=quality, optimize=True, progressive=True)
        if output.stat().st_size <= limit:
            return
    raise RuntimeError(f"JPEG 体积仍超限: {output.name} {output.stat().st_size}>{limit}")


def _normalize_alpha(image: Image.Image) -> Image.Image:
    """把工具返回的 0～254 Alpha 拉伸到完整 0～255 发布范围。"""

    prepared = image.convert("RGBA")
    alpha = prepared.getchannel("A")
    minimum, maximum = alpha.getextrema()
    if minimum != 0 or maximum <= 0:
        raise RuntimeError(f"透明素材缺少有效 Alpha 范围: {(minimum, maximum)}")
    if maximum < 255:
        alpha = alpha.point(lambda value: min(255, round(value * 255 / maximum)))
        prepared.putalpha(alpha)
    return prepared


def _save_png(image: Image.Image, output: Path, size: tuple[int, int], limit: int) -> None:
    """保留真实 Alpha，并在必要时量化颜色控制发布体积。"""

    prepared = _normalize_alpha(_fit_rgba(image, size))
    pixels = prepared.load()
    for y in range(prepared.height):
        for x in range(prepared.width):
            red, green, blue, opacity = pixels[x, y]
            if opacity == 0:
                pixels[x, y] = (0, 0, 0, 0)
    prepared.save(output, "PNG", optimize=True, compress_level=9)
    if output.stat().st_size <= limit:
        return
    quantized = prepared.quantize(colors=128, method=Image.Quantize.FASTOCTREE).convert("RGBA")
    quantized.putalpha(prepared.getchannel("A"))
    quantized.save(output, "PNG", optimize=True, compress_level=9)
    if output.stat().st_size > limit:
        raise RuntimeError(f"PNG 体积仍超限: {output.name} {output.stat().st_size}>{limit}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--only-existing",
        action="store_true",
        help="技术探针阶段只处理已经生成的素材。",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    for output_name, (source_name, size, mode, limit) in ASSETS.items():
        source = args.original_dir / source_name
        if not source.is_file():
            if args.only_existing:
                continue
            raise FileNotFoundError(source)
        output = args.output_dir / output_name
        with Image.open(source) as image:
            if output_name == "template_19_asset_eucalyptus_corner_upper_v1.png":
                # 背景提取连续三轮未得到植物框 Alpha，使用已验证透明角景镜像为右上变体。
                image = ImageOps.flip(ImageOps.mirror(image.convert("RGBA")))
            if mode == "RGB":
                _save_jpeg(image, output, size, limit)
            else:
                _save_png(image, output, size, limit)
        processed += 1
        print(f"{output.name}\t{output.stat().st_size}")
    if processed == 0:
        raise RuntimeError("没有找到可处理的素材")


if __name__ == "__main__":
    main()

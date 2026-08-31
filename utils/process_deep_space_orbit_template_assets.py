"""把 image_gen 原图处理为 template_16 的确定性发布素材。

原始生成图不进入仓库；来源位置、提示词和哈希记录在
``doc/assets/template_16_qa/asset-generation.json``。此脚本用于持有原图的
开发者通过 ``--input-dir`` 重放一次性发布处理，生产运行只读取已提交素材。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


BACKGROUND_JOBS = {
    "raw-bg-space.png": ("template_16_asset_bg_space_dark_v1.jpg", (1920, 1080), 380_000),
}

OVERLAY_JOBS = {
    "raw-orbital-ring.png": ("template_16_asset_orbital_ring_v1.png", (1200, 1200), 900_000, "contain-center"),
    "raw-constellation-edge.png": ("template_16_asset_constellation_edge_v1.png", (1600, 900), 900_000, "cover-center"),
    "raw-nebula-glow.png": ("template_16_asset_nebula_glow_v1.png", (1200, 700), 700_000, "cover-right"),
}


def _cover(
    image: Image.Image,
    size: tuple[int, int],
    *,
    horizontal_alignment: float = 0.5,
) -> Image.Image:
    """按目标比例裁切，并允许右侧光效优先保留。"""
    target_ratio = size[0] / size[1]
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        crop_width = round(image.height * target_ratio)
        left = round((image.width - crop_width) * horizontal_alignment)
        left = min(max(0, left), image.width - crop_width)
        box = (left, 0, left + crop_width, image.height)
    else:
        crop_height = round(image.width / target_ratio)
        top = (image.height - crop_height) // 2
        box = (0, top, image.width, top + crop_height)
    return image.crop(box).resize(size, Image.Resampling.LANCZOS)


def _contain_center(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """等比缩放透明装饰，并保持大面积中央透明区。"""
    ratio = min(size[0] / image.width, size[1] / image.height)
    resized = image.resize(
        (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(
        resized,
        ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2),
    )
    return canvas


def _save_jpeg_under_budget(image: Image.Image, output: Path, max_bytes: int) -> None:
    """在不改变尺寸和 RGB 模式的前提下压缩 JPEG。"""
    rgb = image.convert("RGB")
    for quality in (90, 86, 82, 78, 74, 70, 66, 62, 58):
        rgb.save(output, "JPEG", quality=quality, optimize=True, progressive=True)
        if output.stat().st_size <= max_bytes:
            return
    raise RuntimeError(f"{output.name} 无法压缩到 {max_bytes} 字节以内")


def _save_rgba_under_budget(image: Image.Image, output: Path, max_bytes: int) -> None:
    """保留真实 Alpha，并用受控色阶压缩透明 PNG。"""
    rgba = image.convert("RGBA")
    for colors in (256, 192, 128, 96, 64, 48):
        candidate = rgba.quantize(colors=colors, method=Image.Quantize.FASTOCTREE).convert("RGBA")
        candidate.save(output, "PNG", optimize=True, compress_level=9)
        if output.stat().st_size <= max_bytes:
            alpha_min, alpha_max = candidate.getchannel("A").getextrema()
            if alpha_min < 255 and alpha_max > 0:
                return
    raise RuntimeError(f"{output.name} 无法在保留 Alpha 的同时压缩到 {max_bytes} 字节以内")


def build_assets(input_dir: Path, output_dir: Path) -> None:
    """生成四个发布素材，不生成或覆盖模板列表封面。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    for raw_name, (target_name, size, max_bytes) in BACKGROUND_JOBS.items():
        source = Image.open(input_dir / raw_name)
        target = _cover(source, size)
        _save_jpeg_under_budget(target, output_dir / target_name, max_bytes)

    for raw_name, (target_name, size, max_bytes, mode) in OVERLAY_JOBS.items():
        source = Image.open(input_dir / raw_name).convert("RGBA")
        if mode == "contain-center":
            target = _contain_center(source, size)
        elif mode == "cover-right":
            target = _cover(source, size, horizontal_alignment=1.0)
        else:
            target = _cover(source, size)
        _save_rgba_under_budget(target, output_dir / target_name, max_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(description="处理 template_16 的 image_gen 原图")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_assets(args.input_dir.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()

"""把 image_gen 原图处理为 template_15 的确定性发布素材。"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


BACKGROUND_JOBS = {
    "raw-bg-cover.png": ("template_15_asset_bg_cover_v1.jpg", (1920, 1080), 380_000),
    "raw-bg-section.png": ("template_15_asset_bg_section_v1.jpg", (1920, 1080), 340_000),
    "raw-bg-end.png": ("template_15_asset_bg_end_v1.jpg", (1920, 1080), 340_000),
}

OVERLAY_JOBS = {
    "raw-spectrum-footer.png": ("template_15_asset_spectrum_footer_v1.png", (1600, 520), 950_000, "crop-bottom"),
    "raw-horizon-glow.png": ("template_15_asset_horizon_glow_v1.png", (1600, 700), 850_000, "contain-bottom"),
    "raw-particle-field.png": ("template_15_asset_particle_field_v1.png", (1600, 900), 900_000, "cover"),
    "raw-product-stage.png": ("template_15_asset_product_stage_v1.png", (1200, 700), 800_000, "contain-bottom"),
}


def _cover(image: Image.Image, size: tuple[int, int], *, align_bottom: bool = False) -> Image.Image:
    """按目标比例裁切，底部装饰优先保留下沿。"""
    target_ratio = size[0] / size[1]
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        crop_width = round(image.height * target_ratio)
        left = (image.width - crop_width) // 2
        box = (left, 0, left + crop_width, image.height)
    else:
        crop_height = round(image.width / target_ratio)
        top = image.height - crop_height if align_bottom else (image.height - crop_height) // 2
        box = (0, top, image.width, top + crop_height)
    return image.crop(box).resize(size, Image.Resampling.LANCZOS)


def _contain_bottom(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """等比缩放透明装饰，并贴齐目标画布底部。"""
    ratio = min(size[0] / image.width, size[1] / image.height)
    resized = image.resize(
        (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((size[0] - resized.width) // 2, size[1] - resized.height))
    return canvas


def _save_jpeg_under_budget(image: Image.Image, output: Path, max_bytes: int) -> None:
    """在不改变尺寸和模式的前提下逐级降低 JPEG 质量。"""
    image = image.convert("RGB")
    for quality in (90, 86, 82, 78, 74, 70, 66):
        image.save(output, "JPEG", quality=quality, optimize=True, progressive=True)
        if output.stat().st_size <= max_bytes:
            return
    raise RuntimeError(f"{output.name} 无法压缩到 {max_bytes} 字节以内")


def _save_rgba_under_budget(image: Image.Image, output: Path, max_bytes: int) -> None:
    """保留真实 Alpha，并用受控色阶减少透明 PNG 体积。"""
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
    """生成发布素材和模板列表封面。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    for raw_name, (target_name, size, max_bytes) in BACKGROUND_JOBS.items():
        source = Image.open(input_dir / raw_name)
        target = _cover(source, size)
        _save_jpeg_under_budget(target, output_dir / target_name, max_bytes)

    for raw_name, (target_name, size, max_bytes, mode) in OVERLAY_JOBS.items():
        source = Image.open(input_dir / raw_name).convert("RGBA")
        if mode == "contain-bottom":
            target = _contain_bottom(source, size)
        elif mode == "crop-bottom":
            target = _cover(source, size, align_bottom=True)
        else:
            target = _cover(source, size)
        _save_rgba_under_budget(target, output_dir / target_name, max_bytes)

    # 列表封面与封面背景保持同一视觉来源，避免引入未审计的额外素材。
    cover_background = Image.open(output_dir / "template_15_asset_bg_cover_v1.jpg")
    cover = _cover(cover_background, (960, 540))
    _save_jpeg_under_budget(cover, output_dir / "template_15.jpg", 250_000)


def main() -> None:
    parser = argparse.ArgumentParser(description="处理 template_15 的 image_gen 原图")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_assets(args.input_dir.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()

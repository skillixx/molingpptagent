"""把已生成的抽象油彩原图机械处理为 template_20 的发布素材。

本脚本只执行裁切、缩放、压缩和透明底移除，不程序化绘制视觉内容。
所有油彩形态均来自内置图片生成工具的原始输出。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / "doc" / "assets" / "template_20_qa" / "originals"
TARGET = ROOT / "backend" / "main_api" / "template"


@dataclass(frozen=True)
class RasterAsset:
    source: str
    target: str
    size: tuple[int, int]
    max_bytes: int
    kind: str
    anchor: str = "center"
    remove_generated_matte: bool = False


ASSETS = (
    RasterAsset("bg-cover-source.png", "template_20_asset_bg_cover_v1.jpg", (1920, 1080), 450_000, "jpeg"),
    RasterAsset("bg-content-source.png", "template_20_asset_bg_content_v1.jpg", (1920, 1080), 280_000, "jpeg"),
    RasterAsset("bg-section-source.png", "template_20_asset_bg_section_v1.jpg", (1920, 1080), 380_000, "jpeg"),
    RasterAsset("bg-end-source.png", "template_20_asset_bg_end_v1.jpg", (1920, 1080), 420_000, "jpeg"),
    RasterAsset("teal-brush-band-source.png", "template_20_asset_teal_brush_band_v1.png", (1800, 520), 900_000, "png"),
    RasterAsset("orange-brush-sweep-source.png", "template_20_asset_orange_brush_sweep_v1.png", (1500, 420), 700_000, "png"),
    RasterAsset(
        "yellow-highlight-source-round3.png",
        "template_20_asset_yellow_highlight_v1.png",
        (1200, 260),
        450_000,
        "png",
        remove_generated_matte=True,
    ),
    RasterAsset("paint-corner-source.png", "template_20_asset_paint_corner_v1.png", (1200, 900), 850_000, "png", "bottom-right"),
    RasterAsset("pigment-speckles-source.png", "template_20_asset_pigment_speckles_v1.png", (1600, 900), 650_000, "png", "bottom-right"),
)


def save_jpeg(source: Path, target: Path, size: tuple[int, int], max_bytes: int) -> None:
    """按目标画布居中裁切，并逐级降低质量直到满足发布体积。"""

    with Image.open(source) as image:
        prepared = ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS)
        for quality in range(90, 45, -2):
            prepared.save(target, "JPEG", quality=quality, optimize=True, progressive=True)
            if target.stat().st_size <= max_bytes:
                return
    raise RuntimeError(f"JPEG 无法压缩到目标体积：{target}")


def remove_gray_matte(image: Image.Image) -> Image.Image:
    """按色彩饱和度移除生成器误画的灰色棋盘底，保留黄色油彩本体。"""

    rgb = image.convert("RGB")
    saturation = rgb.convert("HSV").getchannel("S")
    # 棋盘底接近无彩色；用软阈值形成抗锯齿 Alpha，不重新绘制油彩轮廓。
    alpha = saturation.point(lambda value: max(0, min(255, (value - 18) * 5)))
    alpha = alpha.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    rgba = rgb.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    """返回非透明内容边界；空图显式失败，避免发布无内容素材。"""

    alpha = image.getchannel("A")
    bbox = ImageChops.multiply(alpha, alpha).getbbox()
    if bbox is None:
        raise RuntimeError("透明素材未检测到有效油彩内容")
    return bbox


def save_png(asset: RasterAsset, source: Path, target: Path) -> None:
    """保持真实 Alpha，将生成素材缩放并锚定到精确发布画布。"""

    with Image.open(source) as image:
        original = remove_gray_matte(image) if asset.remove_generated_matte else image.convert("RGBA")
        original = original.crop(alpha_bbox(original))

        margin_x = max(12, round(asset.size[0] * 0.025))
        margin_y = max(12, round(asset.size[1] * 0.04))
        base_limit = (asset.size[0] - margin_x * 2, asset.size[1] - margin_y * 2)
        # 个别厚涂纹理的无损 PNG 略大；逐级缩小画布内素材，保持发布画布和 RGBA 契约不变。
        for scale in (1.0, 0.96, 0.92, 0.88, 0.84, 0.80, 0.76, 0.72, 0.68):
            prepared = original.copy()
            prepared.thumbnail(
                (round(base_limit[0] * scale), round(base_limit[1] * scale)),
                Image.Resampling.LANCZOS,
            )
            canvas = Image.new("RGBA", asset.size, (0, 0, 0, 0))
            if asset.anchor == "bottom-right":
                position = (asset.size[0] - margin_x - prepared.width, asset.size[1] - margin_y - prepared.height)
            else:
                position = ((asset.size[0] - prepared.width) // 2, (asset.size[1] - prepared.height) // 2)
            canvas.alpha_composite(prepared, position)
            canvas.save(target, "PNG", optimize=True, compress_level=9)
            if target.stat().st_size <= asset.max_bytes:
                return

    raise RuntimeError(f"PNG 无法压缩到目标体积：{target.name}={target.stat().st_size}>{asset.max_bytes}")


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for asset in ASSETS:
        source = ORIGINALS / asset.source
        target = TARGET / asset.target
        if not source.is_file():
            raise FileNotFoundError(source)
        if asset.kind == "jpeg":
            save_jpeg(source, target, asset.size, asset.max_bytes)
        else:
            save_png(asset, source, target)
        print(f"{target.name}\t{target.stat().st_size}")


if __name__ == "__main__":
    main()

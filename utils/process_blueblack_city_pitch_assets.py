"""把图片工具原始结果规范为项目 JPEG，并保留真实来源和转换记录。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {'cover': 'city_cover', 'contents': 'nebula_contents', 'building': 'building_section',
          'meeting': 'meeting_section', 'end': 'city_end'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset', choices=ASSETS, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--prompt', required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    target = ROOT / 'backend/main_api/template' / f'template_25_asset_bg_{ASSETS[args.asset]}_v1.jpg'
    with Image.open(source) as image:
        original_size = image.size
        # 只进行成品尺寸和编码规范化，不改写生成图中的视觉内容。
        rgb = ImageOps.exif_transpose(image).convert('RGB')
        ImageOps.fit(rgb, (1920, 1080), method=Image.Resampling.LANCZOS).save(target, 'JPEG', quality=94, subsampling=0)
    manifest_path = ROOT / 'doc/assets/template_25_qa/asset-generation.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {
        'templateId': 'template_25', 'tool': 'image_gen.imagegen', 'requestedMethod': 'GPT2 图片模板',
        'actualModel': '工具未暴露', 'assets': {},
    }
    manifest['assets'][args.asset] = {
        'source': str(source), 'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'originalSize': original_size, 'prompt': args.prompt, 'file': target.name,
        'size': [1920, 1080], 'mode': 'RGB', 'format': 'JPEG', 'imageType': 'decoration',
        'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size,
        'visualCheck': '原始输出已查看；待检查实际页面叠字效果',
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()

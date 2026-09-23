"""仅缩放、转码并保留生成素材，不绘制或替换原始视觉内容。"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_27_qa'
TARGET = ROOT / 'backend/main_api/template'


def main():
    manifest = json.loads((QA / 'asset-generation.json').read_text(encoding='utf-8'))
    originals = QA / 'source-images'
    originals.mkdir(parents=True, exist_ok=True)
    results = []
    for row in manifest['assets']:
        source = Path(row['source'])
        archived = originals / f"{row['id']}.png"
        # 原始生成文件单独留存，正式资源不依赖用户目录中的临时位置。
        if source.exists():
            shutil.copy2(source, archived)
        im = Image.open(archived)
        size = (1200, 1200) if row['id'] == 'A5' else (1600, 600) if row['id'] == 'A6' else (1920, 1080)
        destination = TARGET / row['file']
        if row['file'].endswith('.png'):
            if im.mode != 'RGBA' or im.getchannel('A').getextrema()[0] != 0:
                raise ValueError(f"{row['id']} 缺少真实透明通道")
            image = ImageOps.fit(im, size, method=Image.Resampling.LANCZOS)
            image.save(destination, optimize=True)
            alpha = image.getchannel('A')
            transparency = sum(alpha.histogram()[:16]) / (size[0] * size[1])
        else:
            image = ImageOps.fit(im.convert('RGB'), size, method=Image.Resampling.LANCZOS)
            image.save(destination, quality=92, optimize=True, subsampling=0)
            transparency = None
        results.append({'id': row['id'], 'file': row['file'], 'size': list(size), 'mode': image.mode,
                        'transparentFraction': transparency, 'bytes': destination.stat().st_size,
                        'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                        'sourceCopy': str(archived.relative_to(ROOT)).replace('\\', '/')})
    (QA / 'asset-inspection.json').write_text(json.dumps({'assets': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()

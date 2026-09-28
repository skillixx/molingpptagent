"""提取蓝紫霓虹原稿中的可复用资源，生成独立素材与测试照片，不改原稿。"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_30_qa'
TARGET = ROOT / 'backend/main_api/template'
SOURCE = Path('C:/Users/sk20/Desktop/产品发布 (6).pptx')


def main():
    QA.mkdir(parents=True, exist_ok=True)
    raw = QA / 'source-images'
    raw.mkdir(exist_ok=True)
    fixtures = QA / 'fixtures'
    fixtures.mkdir(exist_ok=True)
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    records = []
    with zipfile.ZipFile(SOURCE) as archive:
        def source_image(name):
            data = archive.read('ppt/media/' + name)
            (raw / name).write_bytes(data)
            return Image.open(io.BytesIO(data))

        # 直接遵循原稿的裁切范围，不将宽图拉伸成 16:9。
        for name, key, crop in [('image1.png', 'cover', (0.04819, 0, 0.93708, 1)),
                                ('image4.jpeg', 'directory', (0.11111, 0, 1, 1))]:
            image = source_image(name).convert('RGB')
            w, h = image.size
            image = image.crop(tuple(round(value * (w if i % 2 == 0 else h)) for i, value in enumerate(crop)))
            image = image.resize((1920, 1080), Image.Resampling.LANCZOS)
            filename = f'template_30_asset_bg_{key}_v1.jpg'
            image.save(TARGET / filename, quality=93)
            records.append({'file': filename, 'source': 'ppt/media/' + name, 'method': '原稿裁切与等比输出'})

        for name, key in [('image8.png', 'monitor'), ('image14.png', 'laptop')]:
            image = source_image(name).convert('RGBA')
            filename = f'template_30_asset_{key}_frame_v1.png'
            image.save(TARGET / filename)
            records.append({'file': filename, 'source': 'ppt/media/' + name, 'method': '保留原始设备框及透明通道'})

        # 原稿章节装饰的左半部分是无字城市与手掌；右侧固定 5G 字样不进入通用素材。
        city = source_image('image6.png').convert('RGBA')
        city = city.crop((0, 0, round(city.width * 0.48), city.height))
        bbox = city.getchannel('A').getbbox()
        if bbox:
            city = city.crop(bbox)
        city.save(TARGET / 'template_30_asset_city_platform_v1.png')
        records.append({'file': 'template_30_asset_city_platform_v1.png', 'source': 'ppt/media/image6.png',
                        'method': '提取左侧无字城市装饰，舍弃右侧固定 5G 字样'})
        (raw / 'image32.emf').write_bytes(archive.read('ppt/media/image32.emf'))
        for index, name in enumerate(['image9.jpeg', 'image10.jpeg', 'image13.jpeg', 'image15.jpeg', 'image33.jpeg'], 1):
            image = source_image(name).convert('RGB')
            image.thumbnail((1280, 1200))
            image.save(fixtures / f'business-{index}.jpg', quality=92)
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != digest:
        raise RuntimeError('原稿发生意外变化')
    (QA / 'source-asset-records.json').write_text(json.dumps({'source': str(SOURCE), 'sourceSha256': digest,
        'assets': records, 'pending': ['content-background-generation', 'data-sculpture-generation', 'phone-emf-conversion']},
        ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'assets': len(records), 'fixtures': 5, 'sourceUnchanged': True}))


if __name__ == '__main__':
    main()

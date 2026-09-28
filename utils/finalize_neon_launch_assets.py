"""将实际生成结果与提取素材组装为模板资源，并记录真实尺寸与来源。"""
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_30_qa'
TARGET = ROOT / 'backend/main_api/template'


def main():
    generated = QA / 'generated'
    # 保留生成工具的原始分辨率；不机械放大后声称获得更高清晰度。
    with Image.open(generated / 'content-background.png') as image:
        image.convert('RGB').save(TARGET / 'template_30_asset_bg_content_v1.jpg', quality=95)
    for source, target in [('data-sculpture.png', 'data_sculpture_v1.png'), ('city-clean.png', 'city_platform_v1.png'),
                           ('laptop-clean.png', 'laptop_frame_v1.png')]:
        with Image.open(generated / source) as image:
            if image.mode != 'RGBA' or image.getchannel('A').getextrema()[0] != 0:
                raise ValueError(f'{source} 没有真实透明通道')
        shutil.copyfile(generated / source, TARGET / ('template_30_asset_' + target))
    records = []
    reused = {'bg_cover_v1.jpg': '原稿 image1.png，原裁切', 'bg_directory_v1.jpg': '原稿 image4.jpeg，原裁切',
              'monitor_frame_v1.png': '原稿 image8.png',
              'phone_frame_v1.png': '原稿 image32.emf，经 GDI+ 转换'}
    for file in sorted(TARGET.glob('template_30_asset_*')):
        key = file.name.removeprefix('template_30_asset_')
        with Image.open(file) as image:
            record = {'file': file.name, 'path': str(file.resolve()), 'width': image.width, 'height': image.height, 'mode': image.mode,
                      'format': image.format, 'bytes': file.stat().st_size,
                      'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                      'source': reused.get(key, 'image_gen 生成／原稿装饰编辑'),
                      'actualModel': '不适用' if key in reused else '工具未暴露'}
            if image.mode == 'RGBA':
                record['alphaRange'] = list(image.getchannel('A').getextrema())
        records.append(record)
    (QA / 'asset-inspection.json').write_text(json.dumps({'generationCalls': 4, 'assets': records,
        'notes': ['正文背景与雕塑采用工具实际输出尺寸，按最终显示效果验收；没有放大像素伪称高清。',
                  '城市原稿提取存在断边残片，已用图片编辑工具清理；原始提取记录保留。',
                  '原稿笔记本框含 MacBook 字样，已用图片编辑工具清除并保留设备轮廓。']},
        ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'assetCount': len(records), 'generationCalls': 4}))


if __name__ == '__main__':
    main()

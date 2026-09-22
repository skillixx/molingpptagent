"""用固定语义输入经过真实渲染器，生成覆盖全部版式的可编辑验收样例。"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer

QA = ROOT / 'doc/assets/template_26_qa'
TEMPLATES = ROOT / 'backend/main_api/template'


def build_document():
    template = json.loads((TEMPLATES / 'template_26.json').read_text(encoding='utf-8'))
    sample_images = []
    for index in range(1, 5):
        filename = QA / f'sample-images/S{index}.jpg'
        with Image.open(filename) as image:
            width, height = image.size
        # 示例图片仅嵌入验收文档，正式模板不引用 QA 目录或大块 Base64。
        sample_images.append({'src': 'data:image/jpeg;base64,' + base64.b64encode(filename.read_bytes()).decode('ascii'),
                              'width': width, 'height': height, 'alt': f'AI 生成的安全业务展示样例 {index}，非真实业务记录'})
    semantic = []
    names = ['业务资产', '风险识别', '访问控制', '应急响应', '持续监测', '协同治理']
    for page in template['slides']:
        kind, identity = page['type'], page['id']
        data = {'title': '网络安全项目计划书', 'text': '固定内容验收样例，图片及指标仅用于模板展示。'}
        if page.get('variantKey'):
            data['variant'] = page['variantKey']
        if identity == 'cover-long-title':
            data['title'] = '面向企业业务持续发展的网络安全风险治理体系建设与实施保障项目计划'
        if kind == 'contents':
            data = {'items': names[:int(identity.rsplit('-', 1)[1])]}
        elif kind == 'transition':
            data.update(title='安全建设目标', text='从业务边界、关键资产与实施行动出发。')
        elif kind == 'content':
            count = page['allowedItemCounts'][0]
            data = {'title': {'process': '四步实施路径', 'metrics': '安全运行指标（示例）', 'hub-spoke': '安全治理体系'}.get(page.get('layoutKind'), '业务安全能力建设'),
                    'items': [{'title': names[i], 'text': f'围绕{names[i]}明确责任与实施行动，建立可持续的安全保障机制。'} for i in range(count)]}
            if page.get('variantKey'):
                data['variant'] = page['variantKey']
            if page.get('layoutKind'):
                data['layoutKind'] = page['layoutKind']
            if page.get('layoutKind') == 'metrics':
                data['items'] = [{'title': name, 'value': value, 'unit': unit, 'text': '固定示例数据，仅用于验证。'}
                                 for name, value, unit in zip(['覆盖比例', '响应时长', '处置数量', '演练频率'], ['96', '15', '120', '4'], ['%', '分钟', '项', '次/年'])]
            if page.get('layoutKind') == 'hub-spoke':
                for item in data['items']:
                    item['text'] = f'{item["title"]}形成协同能力，共同支撑中心主题。'
        elif kind == 'end':
            data.update(title='感谢您的观看' if identity == 'end-thanks' else '交流与后续行动', text='此文档为模板验收样例')
            if identity == 'end-action':
                data['items'] = [{'title': '行动一', 'text': '梳理关键业务资产'}, {'title': '行动二', 'text': '明确项目实施安排'}, {'title': '联系', 'text': 'security@example.invalid'}]
        entry = {'type': kind, 'data': data}
        slots = [e for e in page['elements'] if e.get('imageType') == 'content']
        if slots:
            entry['images'] = sample_images[:len(slots)]
        semantic.append(entry)
    result = PresentationTemplateRenderer(TEMPLATES).render(template_id='template_26', semantic_slides=semantic,
                                                            task_id='template26-all-layouts', fallback_title='网络安全')
    actual = [s['templateSlideId'] for s in result['slides']]
    expected = [s['id'] for s in template['slides']]
    if actual != expected:
        raise RuntimeError(f'版式覆盖不符合规划：{actual}')
    document = {**result, 'width': 1000, 'height': 562.5, 'metadata': {'buildStage': 'all-layouts-fixed-data', 'sampleImages': 'AI生成的虚构展示样例'}}
    (QA / 'semantic-input.json').write_text(json.dumps(semantic, ensure_ascii=False, indent=2), encoding='utf-8')
    (QA / 'production-document.json').write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    mvp_ids = set(template['metadata']['mvpSlideIds'])
    mvp = {**document, 'slides': [s for s in result['slides'] if s['templateSlideId'] in mvp_ids]}
    (QA / 'mvp-document.json').write_text(json.dumps(mvp, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'slides': len(actual), 'mvpSlides': len(mvp['slides']), 'allLayoutsCovered': True}))


if __name__ == '__main__':
    build_document()

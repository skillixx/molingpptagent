"""固定语义输入经过真实渲染器，生成全部版式和容量压力样例，不调用业务模型。"""
from __future__ import annotations

import base64
import copy
import json
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer

QA = ROOT / 'doc/assets/template_30_qa'
TEMPLATES = ROOT / 'backend/main_api/template'


def items(count):
    titles = ['理解真实需求', '定义产品能力', '验证应用价值', '协同实施交付', '持续优化体验', '形成长期服务']
    return [{'title': titles[i % 6], 'text': f'第{i + 1}项完整正文，展示实际应用价值。'} for i in range(count)]


def main():
    photos = []
    for i in range(1, 6):
        file = QA / 'fixtures' / f'business-{i}.jpg'
        with Image.open(file) as image:
            width, height = image.size
        photos.append({'src': 'data:image/jpeg;base64,' + base64.b64encode(file.read_bytes()).decode(),
                       'width': width, 'height': height})
    template = json.loads((TEMPLATES / 'template_30.json').read_text(encoding='utf-8'))
    semantics = []
    catalogue = []
    for index, page in enumerate(template['slides']):
        kind, identity = page['type'], page['id']
        variant = (page.get('variantAliases') or [page.get('variantKey')])[0]
        data = {'title': '蓝紫霓虹·科技产品发布', 'text': '产品能力与应用场景\n汇报人：产品团队\n日期：2026年9月'}
        if variant:
            data['variant'] = variant
        if kind == 'cover' and identity == 'cover-long-title':
            data['title'] = '面向数字化业务持续发展与团队协作的产品能力建设及应用成果发布'
        elif kind == 'contents':
            data['items'] = ['项目背景', '产品能力', '应用场景', '实施路径', '阶段成果', '未来计划'][:int(identity[-1])]
        elif kind == 'transition':
            data.update(title='从真实需求出发', text='明确目标，连接产品能力与应用场景。')
        elif kind == 'end':
            data.update(title='感谢您的关注', text='让科技创造更多可能\n产品团队期待与您交流')
        elif kind == 'content':
            count = page['allowedItemCounts'][0]
            data = {'title': '科技连接真实场景', 'items': items(count),
                    **({'variant': variant} if variant else {}),
                    **({'layoutKind': page['layoutKind']} if page.get('layoutKind') else {})}
            if page.get('layoutKind') == 'metrics':
                for i, entry in enumerate(data['items']):
                    entry.update(value=['33', '89', '17'][i], unit='%')
            if identity == 'content-swot-4':
                for entry, title in zip(data['items'], ['优势：技术积累', '不足：交付周期', '机会：场景拓展', '挑战：市场变化']):
                    entry['title'] = title
        semantic = {'type': kind, 'data': data}
        if any(e.get('imageType') == 'content' for e in page['elements']):
            semantic['images'] = [photos[index % len(photos)]]
        semantics.append(semantic)
        catalogue.append({'id': identity, 'sourceLayout': page.get('sourceLayout'), 'isBaseLayout': page['isBaseLayout'],
            'type': kind, 'variant': data.get('variant'), 'layoutKind': data.get('layoutKind'),
            'itemCount': len(data.get('items', [])), 'imageCount': len(semantic.get('images', []))})
    renderer = PresentationTemplateRenderer(TEMPLATES)

    def render(source, identity):
        try:
            document = renderer.render(template_id='template_30', semantic_slides=source, task_id=identity,
                                       fallback_title='蓝紫霓虹科技产品发布')
        except Exception as error:
            raise RuntimeError(f'{identity}: {getattr(error, "context", {})}') from error
        document.update(width=1000, height=562.5, title='蓝紫霓虹·科技产品发布',
                        metadata={'buildStage': 'fixed-semantic-candidate', 'baseLayoutCount': 22})
        return document

    result = render(semantics, 'template30-inventory')
    expected = [page['id'] for page in template['slides']]
    if [page['templateSlideId'] for page in result['slides']] != expected:
        raise RuntimeError('实际选版没有按顺序覆盖全部候选版式')
    long_items = [{'title': f'第{i}项面向产品业务持续发展和团队协作的完整行动目标与实施路径说明',
                   'text': f'保留行动{i}的完整内容。'} for i in range(1, 5)]
    long_metrics = copy.deepcopy(semantics[12])
    long_metrics['data']['items'][0]['text'] = '完整记录性能指标的测量条件与适用范围。' * 25
    cases = [('all-layouts', semantics),
             ('long-cover', [semantics[22]]),
             ('long-item-titles', [{'type': 'content', 'data': {'title': '原始信息完整保留', 'items': long_items}}]),
             ('long-body', [{'type': 'content', 'data': {'title': '详细实施计划', 'items': [{'title': '实施安排', 'text': '完整保留需求说明、实施计划和各项交付安排。' * 35}]}}]),
             ('long-directory', [{'type': 'contents', 'data': {'items': [f'第{i}章项目建设目标与协作成果说明' for i in range(1, 14)]}}]),
             ('image-long-body', [{'type': 'content', 'data': {'title': '图文内容完整保留', 'items': [{'title': '业务场景', 'text': '保留关联图片与完整业务说明。' * 26}]}, 'images': [photos[0]]}]),
             ('overflow-metrics', [long_metrics])]
    stress = [{'name': name, 'document': render(source, 'template30-' + name)} for name, source in cases]
    for filename, data in [('semantic-input.json', semantics), ('production-document.json', result),
                           ('stress-documents.json', stress), ('layout-catalogue.json', catalogue)]:
        (QA / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'baseLayouts': 22, 'totalLayouts': len(result['slides']),
                      'stressPages': sum(len(entry['document']['slides']) for entry in stress)}))


if __name__ == '__main__':
    main()

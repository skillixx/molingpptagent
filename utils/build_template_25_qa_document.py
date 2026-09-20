"""固定数据覆盖全部 24 个模板版式，通过真实渲染器产生编辑器验证输入。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer


def main():
    template_root = ROOT / 'backend/main_api/template'
    template = json.loads((template_root / 'template_25.json').read_text(encoding='utf-8'))
    semantic = []
    for page in template['slides']:
        kind, identity = page['type'], page['id']
        data = {'title': '城市创新服务融资路演', 'text': '固定数据版式演示，图片和数字仅用于模板验证。'}
        if page.get('variantKey'):
            data['variant'] = page['variantKey']
        if identity == 'cover-city-long-title':
            data['title'] = '面向未来城市绿色产业升级的智能服务平台商业发展与融资合作计划'
        if kind == 'contents':
            count = int(identity.split('-')[-1])
            data = {'items': ['项目概况', '团队介绍', '行业与市场', '产品特色', '财务计划', '风险对策'][:count]}
        elif kind == 'transition':
            data['title'] = '项目概况' if identity.endswith('building') else '团队与协作'
            data['text'] = '从目标到行动'
        elif kind == 'content':
            count = page['allowedItemCounts'][0]
            data = {'title': {'process': '四步实施路径', 'timeline': '发展里程碑', 'metrics': '关键指标（示例）', 'compare': '双项方案对比'}.get(page.get('layoutKind'), '项目价值与行动'),
                    'items': [{'title': f'业务要点{i}', 'text': f'第{i}项说明：以实际业务需求为基础，明确交付目标与实施安排。'} for i in range(1, count + 1)]}
            if page.get('variantKey'):
                data['variant'] = page['variantKey']
            if page.get('layoutKind'):
                data['layoutKind'] = page['layoutKind']
            if page.get('layoutKind') == 'metrics':
                for i, item in enumerate(data['items']):
                    item.update(value=f'{(i + 1) * 20}%', text='固定示例数据，仅用于验证。')
            if page.get('layoutKind') == 'timeline':
                for date, item in zip(['2026.01', '2026.06', '2026.12'], data['items']):
                    item['title'] = date
        elif kind == 'end':
            data['title'] = '感谢观看' if identity == 'end-thanks' else '期待与您交流合作'
            data['text'] = '本演示仅用于模板验证'
            if identity == 'end-contact':
                data['items'] = [{'title': '联系人', 'text': '示例负责人'}, {'title': '邮箱', 'text': 'pitch@example.invalid'}]
        entry = {'type': kind, 'data': data}
        slots = [e for e in page['elements'] if e.get('imageType') == 'content']
        if slots:
            # 用已生成图片验证槽位，业务图来源仅为测试输入，不冒充真实客户材料。
            files = template['metadata']['assetFiles']
            entry['images'] = [{'src': f'/api/data/{files[i % len(files)]}', 'width': 1920, 'height': 1080} for i in range(len(slots))]
        semantic.append(entry)
    rendered = PresentationTemplateRenderer(template_root).render(template_id='template_25', semantic_slides=semantic,
                                                                  task_id='pitch-all-layouts-fixed', fallback_title='融资路演')
    expected_ids = [s['id'] for s in template['slides']]
    actual_ids = [s['templateSlideId'] for s in rendered['slides']]
    if actual_ids != expected_ids:
        raise RuntimeError(f'版式覆盖与规划不符：{actual_ids}')
    output = ROOT / 'doc/assets/template_25_qa'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'semantic-input.json').write_text(json.dumps(semantic, ensure_ascii=False, indent=2), encoding='utf-8')
    document = {**rendered, 'width': 1000, 'height': 562.5, 'metadata': {'buildStage': 'all-layouts-fixed'}}
    (output / 'production-document.json').write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'slides': len(actual_ids), 'allLayoutsCovered': True}))


if __name__ == '__main__':
    main()

"""生成覆盖全部库存的固定语义稿，并实际调用公共模板渲染器。"""
from __future__ import annotations

import base64
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer

QA = ROOT / 'doc/assets/template_27_qa'
TEMPLATES = ROOT / 'backend/main_api/template'


def make_items(count):
    titles = ['明确项目目标', '梳理实施路径', '建立协作机制', '验证实际成果', '持续优化体验']
    bodies = ['围绕实际需求定义预期结果，明确本阶段需要解决的问题。', '把目标拆解为可执行步骤，记录负责人、时间安排与交付物。',
              '同步信息与进展，及时处理依赖，让各方保持一致理解。', '结合真实使用场景检查成果，保留有效证据并修正问题。', '收集反馈，延续有效做法，让后续工作更清晰。']
    return [{'title': titles[i % len(titles)], 'text': bodies[i % len(bodies)]} for i in range(count)]


def main():
    generation = json.loads((QA / 'business-image-generation.json').read_text(encoding='utf-8'))
    source = QA / 'source-images/business.png'
    if Path(generation['source']).exists():
        shutil.copy2(generation['source'], source)
    photo = Image.open(source).convert('RGB')
    fixture_dir = QA / 'fixtures'
    fixture_dir.mkdir(exist_ok=True)
    photos = []
    # 同一张已生成业务照片做机械裁切，用于验证横竖比例；不冒充六张正式装饰。
    for i, (w, h) in enumerate([(1000, 700), (700, 1000), (900, 900), (1200, 600)]):
        dest = fixture_dir / f'business-{i + 1}.jpg'
        ImageOps.fit(photo, (w, h), centering=(i / 3, 0.5)).save(dest, quality=87)
        photos.append({'src': 'data:image/jpeg;base64,' + base64.b64encode(dest.read_bytes()).decode(), 'width': w, 'height': h})
    template = json.loads((TEMPLATES / 'template_27.json').read_text(encoding='utf-8'))
    semantic = []
    for layout in template['slides']:
        identity, kind = layout['id'], layout['type']
        data = {}
        extra = {}
        if kind == 'cover':
            data = {'title': '蓝紫光斑·唯美清新' if identity == 'cover-ring' else '面向未来业务持续发展与团队协作的项目建设目标实施路径及阶段成果汇报',
                    'text': '项目介绍与阶段成果汇报', 'variant': layout['variantKey']}
        elif kind == 'contents':
            count = int(identity.rsplit('-', 1)[1])
            data = {'items': ['项目背景', '建设目标', '实施路径', '协作安排', '阶段成果', '下一步计划'][:count]}
        elif kind == 'transition':
            data = {'title': '让灵感成为行动', 'text': '从共同目标出发，将想法落实为清晰的行动与可检查的成果。'}
        elif kind == 'end':
            data = {'title': '感谢您的关注', 'text': '期待下一次共同创造'}
        else:
            count = layout['allowedItemCounts'][0]
            data = {'title': '让想法清晰呈现', 'items': make_items(count)}
            if identity.startswith('content-image-'):
                data['title'] = '协作空间的设计与体验'
                data['items'] = [{'title': t, 'text': body} for t, body in zip(['自然采光', '共享空间', '舒适材料', '细节体验'],
                    ['让自然光进入工作区域，营造明亮舒适的协作环境。', '开放而有秩序的空间，让讨论与专注都能找到合适的位置。',
                     '木质材料与柔和织物，形成温暖而平静的日常体验。', '从座位、动线和交流距离入手，让空间真正服务于人。'])][:count]
                extra['images'] = photos[:count]
                if 'variantKey' in layout:
                    data['variant'] = layout['variantKey']
            if layout.get('layoutKind'):
                data['layoutKind'] = layout['layoutKind']
                if layout['layoutKind'] == 'metrics':
                    data['title'] = '用数字记录每一份进展'
                    data['items'] = [{'title': title, 'value': value, 'unit': unit, 'text': body} for title, value, unit, body in [
                        ('满意度', 96, '%', '固定演示数据，用于验证独立数值与单位。'), ('协作场景', 24, '项', '覆盖讨论、展示与安静工作的不同需要。'),
                        ('实施周期', 8, '周', '根据项目安排推进每个阶段。'), ('检查覆盖', 100, '%', '为交付结果提供清晰的检查依据。')]]
                elif layout['layoutKind'] == 'timeline':
                    data['title'] = '让每个阶段都有明确方向'
                    data['items'] = [{'title': title, 'text': body} for title, body in [('第1周·调研', '确认需求与边界。'), ('第2周·设计', '形成方案与样例。'),
                        ('第3周·实施', '完成约定的建设。'), ('第4周·验证', '检查结果并修正。'), ('第5周·交付', '整理材料与说明。')]]
                else:
                    data['title'] = '从目标走向成果'
        semantic.append({'type': kind, 'data': data, **extra})
    (QA / 'semantic-input.json').write_text(json.dumps(semantic, ensure_ascii=False, indent=2), encoding='utf-8')
    result = PresentationTemplateRenderer(TEMPLATES).render(template_id='template_27', semantic_slides=semantic,
        task_id='template-27-inventory', fallback_title='唯美清新')
    expected = [s['id'] for s in template['slides']]
    actual = [s.get('templateSlideId') for s in result['slides']]
    if actual != expected:
        raise RuntimeError(f'选版路径没有完整覆盖库存：{actual}')
    result.update(width=1000, height=562.5, title='蓝紫光斑·唯美清新', metadata={'buildStage': 'fixed-semantic-acceptance'})
    (QA / 'production-document.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'slides': len(actual), 'selectedLayouts': actual}, ensure_ascii=False))


if __name__ == '__main__':
    main()

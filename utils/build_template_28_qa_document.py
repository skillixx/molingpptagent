"""用固定内容经真实渲染器生成十八版式样例，不调用模型或生产服务。"""
from __future__ import annotations

import base64
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.main_api.workers.template_renderer import PresentationTemplateRenderer

QA = ROOT / 'doc/assets/template_28_qa'
TEMPLATES = ROOT / 'backend/main_api/template'


def items(count):
    titles = ['明确项目目标', '梳理实施路径', '建立协作机制', '验证实际成果']
    bodies = ['围绕实际需求定义预期结果，明确本阶段需要解决的问题。',
              '把目标拆解为可执行步骤，记录负责人、时间安排与交付物。',
              '同步信息与进展，及时处理依赖，让各方保持一致理解。',
              '结合实际使用场景检查成果，保留有效证据并修正问题。']
    return [{'title': titles[i % 4], 'text': bodies[i % 4]} for i in range(count)]


def main():
    fixtures = QA / 'fixtures'
    fixtures.mkdir(exist_ok=True)
    photos = []
    # 复用已有本地验收图片，不重新生成业务素材，也不纳入五张正式装饰。
    for i in range(1, 5):
        source = ROOT / f'doc/assets/template_27_qa/fixtures/business-{i}.jpg'
        target = fixtures / source.name
        if not target.exists():
            shutil.copy2(source, target)
        with Image.open(target) as im:
            width, height = im.size
        photos.append({'src': 'data:image/jpeg;base64,' + base64.b64encode(target.read_bytes()).decode(),
                       'width': width, 'height': height})
    renderer = PresentationTemplateRenderer(TEMPLATES)
    template = json.loads((TEMPLATES / 'template_28.json').read_text(encoding='utf-8'))
    semantic = []
    for page in template['slides']:
        kind, identity = page['type'], page['id']
        extra = {}
        if kind == 'cover':
            data = {'title': '青绿几何·清新商务' if identity == 'cover-geometric' else '面向未来业务持续发展与团队协作的项目建设目标实施路径及阶段成果汇报',
                    'text': '项目介绍与阶段成果汇报\n汇报人：项目组　日期：2026年9月', 'variant': page['variantKey']}
        elif kind == 'contents':
            data = {'items': ['项目背景', '建设目标', '实施路径', '协作安排', '阶段成果', '下一步计划'][:int(identity[-1])]}
        elif kind == 'transition':
            data = {'title': '从共同目标出发', 'text': '将每一步行动落到具体任务，让项目进展清晰可见。'}
        elif kind == 'end':
            data = {'title': '感谢您的关注', 'text': '项目组期待与您共同推进下一阶段工作'}
        else:
            count = page['allowedItemCounts'][0]
            data = {'title': '让想法清晰呈现', 'items': items(count)}
            if identity.startswith('content-image-'):
                data['title'] = '协作空间的设计与体验'
                data['items'] = [{'title': title, 'text': body} for title, body in zip(
                    ['自然采光', '共享空间', '舒适材料', '细节体验'],
                    ['让自然光进入工作区域，营造明亮舒适的协作环境。', '开放而有秩序的空间，让讨论与专注都能找到合适的位置。',
                     '木质材料与柔和织物，形成温暖而平静的日常体验。', '从座位、动线和交流距离入手，让空间真正服务于人。'])][:count]
                extra['images'] = photos[:count]
                if page.get('variantKey'):
                    data['variant'] = page['variantKey']
        semantic.append({'type': kind, 'data': data, **extra})
    (QA / 'semantic-input.json').write_text(json.dumps(semantic, ensure_ascii=False, indent=2), encoding='utf-8')

    def render(source, task_id):
        document = renderer.render(template_id='template_28', semantic_slides=source, task_id=task_id, fallback_title='青绿几何')
        document.update(width=1000, height=562.5, title='青绿几何·清新商务', metadata={'buildStage': 'fixed-semantic-acceptance'})
        return document

    result = render(semantic, 'template-28-inventory')
    if [s['templateSlideId'] for s in result['slides']] != [s['id'] for s in template['slides']]:
        raise RuntimeError('实际选版未按顺序覆盖十八个版式')
    (QA / 'production-document.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    long_titles = [{'title': f'第{i}项面向未来业务发展与项目协作的完整行动目标及实施路径说明', 'text': f'执行行动{i}。'} for i in range(4)]
    cases = [
        ('all-layouts', semantic),
        ('cover-supplementary-info', [{'type': 'cover', 'data': {'title': '长期协作计划', 'text': '项目建设与成果汇报\n汇报人：示例项目组\n日期：2026年9月'}}]),
        ('four-original-long-titles', [{'type': 'content', 'data': {'title': '完整标题保留', 'items': long_titles}}]),
        ('long-body', [{'type': 'content', 'data': {'title': '详细实施安排', 'items': [{'title': '实施步骤', 'text': '完整保留需求说明、实施计划和各项交付安排。' * 35}]}}]),
        ('long-directory', [{'type': 'contents', 'data': {'items': [f'第{i}章项目建设目标与协作成果的完整说明' for i in range(1, 14)]}}]),
        ('four-images-long-titles', [{'type': 'content', 'data': {'title': '图文信息完整保留', 'items': long_titles}, 'images': photos}]),
    ]
    stress = [{'name': name, 'document': render(source, f'template28-{name}')} for name, source in cases]
    (QA / 'stress-documents.json').write_text(json.dumps(stress, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'slides': len(result['slides']), 'stressPages': sum(len(x['document']['slides']) for x in stress)}))


if __name__ == '__main__':
    main()

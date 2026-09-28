"""通过真实渲染器检查蓝紫霓虹模板的内容保真与可编辑槽位。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

import pytest

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer

ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / 'utils/build_neon_technology_launch_template.mjs'

# 预期来自开发说明中的 L01—L22，不能从构建器输出反推相同结果。
INVENTORY = [
    ('L01', 'cover-neon', 'cover', 0, 0, None),
    ('L02', 'contents-4', 'contents', 4, 0, None),
    ('L03', 'transition-neon', 'transition', 0, 0, None),
    ('L04', 'content-city-3', 'content', 3, 0, None),
    ('L05', 'content-monitor-3', 'content', 3, 1, None),
    ('L06', 'content-circles-3', 'content', 3, 0, None),
    ('L07', 'content-image-note-1', 'content', 1, 1, None),
    ('L08', 'content-swot-4', 'content', 4, 0, 'compare'),
    ('L09', 'content-image-left-3', 'content', 3, 1, None),
    ('L10', 'content-sculpture-2', 'content', 2, 0, None),
    ('L11', 'content-cross-4', 'content', 4, 0, 'hub-spoke'),
    ('L12', 'content-icon-columns-4', 'content', 4, 0, 'process'),
    ('L13', 'content-metrics-image-3', 'content', 3, 1, 'metrics'),
    ('L14', 'content-fan-4', 'content', 4, 0, 'hub-spoke'),
    ('L15', 'content-steps-4', 'content', 4, 0, 'process'),
    ('L16', 'content-laptop-1', 'content', 1, 1, None),
    ('L17', 'content-positioning-3', 'content', 3, 0, 'positioning'),
    ('L18', 'content-phone-6', 'content', 6, 1, None),
    ('L19', 'content-compare-image-4', 'content', 4, 1, 'compare'),
    ('L20', 'content-ring-image-5', 'content', 5, 1, 'hub-spoke'),
    ('L21', 'content-cycle-4', 'content', 4, 0, 'process'),
    ('L22', 'end-neon', 'end', 0, 0, None),
]


def build_renderer(directory):
    """测试只替代文件读取边界，不替代真实选版与文字填充逻辑。"""
    subprocess.run(['node', str(BUILDER), str(directory / 'template_30.json')],
                   check=True, capture_output=True)
    template = json.loads((directory / 'template_30.json').read_text(encoding='utf-8'))
    for name in template['metadata']['assetFiles']:
        (directory / name).write_bytes(b'unit-test-resource')
    return PresentationTemplateRenderer(directory)


def plain(element):
    return unescape(re.sub('<[^>]+>', '', element.get('content', '').replace('<br>', '\n')))


def semantic_for(entry):
    source, identity, kind, count, image_count, layout = entry
    data = {'title': '科技连接真实场景', 'text': '发布主题与团队介绍', 'variant': source}
    if kind == 'contents':
        data['items'] = ['项目背景', '产品能力', '实施路径', '未来计划']
        data.pop('variant')
    elif kind == 'content':
        data['items'] = [{'title': f'主题{i + 1}', 'text': f'第{i + 1}项完整正文，展示实际应用价值。'} for i in range(count)]
        if layout:
            data['layoutKind'] = layout
        if layout == 'metrics':
            for i, item in enumerate(data['items']):
                item.update(value=str((i + 1) * 17), unit='%')
    elif kind == 'transition':
        data.pop('variant')
    result = {'type': kind, 'data': data}
    if image_count:
        result['images'] = [{'src': 'https://example.invalid/scene.jpg', 'width': 1200, 'height': 800}]
    return result


def test_cover_fills_editable_title_and_complete_supplementary_information(tmp_path):
    renderer = build_renderer(tmp_path)
    details = '产品发布与场景说明\n汇报人：产品团队\n日期：2026年9月'
    document = renderer.render(template_id='template_30', task_id='neon-cover-test', fallback_title='默认标题',
        semantic_slides=[{'type': 'cover', 'data': {'title': '智联未来', 'text': details}}])
    page = document['slides'][0]
    assert page['templateSlideId'] == 'cover-neon'
    assert [plain(e) for e in page['elements'] if e.get('textType') == 'title'] == ['智联未来']
    contents = '\n'.join(plain(e) for e in page['elements'] if e.get('textType') == 'content')
    assert all(line in contents for line in details.splitlines())
    assert all(e.get('type') == 'text' for e in page['elements'] if e.get('textType'))


def test_all_twenty_two_planned_layouts_are_reachable_with_real_semantic_input(tmp_path):
    renderer = build_renderer(tmp_path)
    for entry in INVENTORY:
        pages = renderer.render(template_id='template_30', semantic_slides=[semantic_for(entry)],
                                task_id='all-neon-layouts', fallback_title='科技发布')['slides']
        assert len(pages) == 1, entry[0]
        assert pages[0]['templateSlideId'] == entry[1], entry[0]
        body = ''.join(plain(e) for e in pages[0]['elements'])
        for i in range(entry[3] if entry[2] == 'content' else 0):
            assert f'第{i + 1}项完整正文' in body, entry[0]
        if entry[2] == 'content':
            assert [plain(e) for e in pages[0]['elements'] if e.get('textType') == 'item'] == [
                item['text'] for item in semantic_for(entry)['data']['items']
            ], entry[0]


@pytest.mark.parametrize('has_image,expected', [(True, 'content-compare-image-4'), (False, 'content-text-4')])
def test_compare_variant_uses_its_own_image_capacity_and_falls_back_losslessly(tmp_path, has_image, expected):
    """显式版式不能被同类其他版式的图片容量影响；缺图时保留四项正文降级。"""
    renderer = build_renderer(tmp_path)
    semantic = semantic_for(INVENTORY[18])
    if not has_image:
        semantic.pop('images')
    pages = renderer.render(template_id='template_30', semantic_slides=[semantic],
                            task_id='compare-capacity', fallback_title='对比说明')['slides']
    assert len(pages) == 1
    assert pages[0]['templateSlideId'] == expected
    bodies = [plain(e) for e in pages[0]['elements'] if e.get('textType') == 'item']
    assert bodies == [item['text'] for item in semantic['data']['items']]


def test_alternating_steps_keep_each_number_title_and_body_bound_to_the_same_item(tmp_path):
    renderer = build_renderer(tmp_path)
    semantic = semantic_for(INVENTORY[14])
    page = renderer.render(template_id='template_30', semantic_slides=[semantic], task_id='step-order', fallback_title='流程')['slides'][0]
    # 流程编号按从左到右阅读，上下交替的标题仍须对应同一步骤。
    titles = sorted((e for e in page['elements'] if e.get('textType') == 'itemTitle'), key=lambda e: e['left'])
    bodies = sorted((e for e in page['elements'] if e.get('textType') == 'item'), key=lambda e: e['left'])
    assert [plain(e) for e in titles] == ['主题1', '主题2', '主题3', '主题4']
    assert [plain(e) for e in bodies] == [x['text'] for x in semantic['data']['items']]


@pytest.mark.parametrize('variant', [None, 'L16'])
def test_one_long_image_item_preserves_body_and_uses_text_continuations(tmp_path, variant):
    renderer = build_renderer(tmp_path)
    body = '保留关联图片与完整业务说明。' * 26
    data = {'title': '图文内容完整保留', 'items': [{'title': '业务场景', 'text': body}]}
    if variant:
        data['variant'] = variant
    semantic = {'type': 'content', 'data': data,
                'images': [{'src': 'https://example.invalid/only-image.jpg', 'width': 800, 'height': 1200}]}
    pages = renderer.render(template_id='template_30', semantic_slides=[semantic],
                            task_id='long-image-item', fallback_title='图文')['slides']
    assert len(pages) > 1
    assert ''.join(plain(e) for p in pages for e in p['elements'] if e.get('textType') == 'item') == body
    images = [e for p in pages for e in p['elements'] if e.get('imageType') == 'content']
    assert [e['src'] for e in images] == ['https://example.invalid/only-image.jpg']
    assert len([e for e in pages[0]['elements'] if e.get('textType') == 'item']) == 1


def test_real_api_exposes_the_neon_template_and_full_inventory():
    """用隔离配置访问真实模板 API，防止只有构建文件却没有用户入口。"""
    environment = {key: os.environ[key] for key in ('PATH', 'PATHEXT', 'SYSTEMROOT', 'TEMP', 'TMP', 'WINDIR') if key in os.environ}
    environment.update(APP_ENV='test', PERSISTENCE_ENABLED='false', SSO_ENABLED='false', BILLING_ENABLED='false',
        STORAGE_ENABLED='false', TASK_WORKER_ENABLED='false', RELEASE_CHANNEL='test', RELEASE_COMMIT='template-30-test')
    code = (
        "import json,dotenv;dotenv.load_dotenv=lambda *a,**k:False;import main;"
        "from fastapi.testclient import TestClient;client=TestClient(main.app);"
        "items=client.get('/templates').json()['data'];response=client.get('/data/template_30.json');"
        "print(json.dumps({'entry':[x for x in items if x['id']=='template_30'],'status':response.status_code,"
        "'slides':len(response.json()['slides'])}))"
    )
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT / 'backend/main_api', env=environment,
                            capture_output=True, text=True, check=True, timeout=25)
    actual = json.loads(result.stdout.strip().splitlines()[-1])
    assert actual == {'entry': [{'id': 'template_30', 'name': '蓝紫霓虹·科技产品发布', 'cover': '/api/data/template_30.jpg'}],
                      'status': 200, 'slides': 39}


def test_four_long_original_titles_remain_on_one_page_and_preserve_order(tmp_path):
    renderer = build_renderer(tmp_path)
    source = [{'title': f'第{i}项面向产品业务持续发展与团队协作的完整行动目标和实施路径说明',
               'text': f'保留原始正文{i}。'} for i in range(1, 5)]
    pages = renderer.render(template_id='template_30', semantic_slides=[{'type': 'content',
        'data': {'title': '原始标题保真', 'items': source}}], task_id='long-titles', fallback_title='科技')['slides']
    assert len(pages) == 1 and pages[0]['templateSlideId'] == 'content-text-4'
    bodies = [plain(e) for e in pages[0]['elements'] if e.get('textType') == 'item']
    assert all(item['title'] in body and item['text'] in body for item, body in zip(source, bodies, strict=True))


@pytest.mark.parametrize('count', [1, 2, 4, 6, 7, 13])
def test_directory_keeps_every_entry_and_continuous_numbers(tmp_path, count):
    renderer = build_renderer(tmp_path)
    names = [f'第{i}章项目目标与实施说明' for i in range(1, count + 1)]
    pages = renderer.render(template_id='template_30', semantic_slides=[{'type': 'contents', 'data': {'items': names}}],
        task_id='contents-order', fallback_title='目录')['slides']
    assert [plain(e) for p in pages for e in p['elements'] if e.get('textType') == 'item'] == names
    assert [plain(e) for p in pages for e in p['elements'] if e.get('textType') == 'itemNumber'] == [f'{i:02}' for i in range(1, count + 1)]


def test_overflowing_metrics_keep_value_unit_title_and_body_when_using_ordinary_pages(tmp_path):
    renderer = build_renderer(tmp_path)
    semantic = semantic_for(INVENTORY[12])
    semantic['data']['items'][0]['text'] = '完整记录性能指标的测量条件与适用范围。' * 25
    pages = renderer.render(template_id='template_30', semantic_slides=[semantic], task_id='metric-fallback', fallback_title='指标')['slides']
    joined = ''.join(plain(e) for p in pages for e in p['elements'])
    assert '17%' in joined and '34%' in joined and '51%' in joined
    bodies = ''.join(plain(e) for p in pages for e in p['elements'] if e.get('textType') == 'item')
    assert bodies.count('完整记录性能指标的测量条件与适用范围。') == 25
    assert all(f'主题{i}' in joined for i in range(1, 4))


def test_explicit_circle_layout_with_long_body_falls_back_without_losing_content(tmp_path):
    renderer = build_renderer(tmp_path)
    semantic = semantic_for(INVENTORY[5])
    semantic['data']['items'][0]['text'] = '保留项目详细说明与实施过程。' * 35
    pages = renderer.render(template_id='template_30', semantic_slides=[semantic], task_id='circle-overflow', fallback_title='说明')['slides']
    bodies = ''.join(plain(e) for p in pages for e in p['elements'] if e.get('textType') == 'item')
    assert bodies == ''.join(item['text'] for item in semantic['data']['items'])
    assert all(p['templateSlideId'].startswith('content-text-') for p in pages)


@pytest.mark.parametrize('count,with_image,expected', [
    (3, False, {'content-city-3', 'content-circles-3'}),
    (2, False, {'content-sculpture-2'}),
    (3, True, {'content-monitor-3', 'content-image-left-3'}),
    (1, True, {'content-image-note-1', 'content-laptop-1'}),
    (6, True, {'content-phone-6'}),
])
def test_default_semantic_generation_reaches_source_layouts_without_manual_variant(tmp_path, count, with_image, expected):
    renderer = build_renderer(tmp_path)
    semantic = {'type': 'content', 'data': {'title': '科技产品能力',
        'items': [{'title': f'主题{i + 1}', 'text': f'第{i + 1}项完整正文。'} for i in range(count)]}}
    if with_image:
        semantic['images'] = [{'src': 'https://example.invalid/default.jpg', 'width': 1200, 'height': 800}]
    pages = renderer.render(template_id='template_30', semantic_slides=[semantic] * 12,
                            task_id='default-source-layouts', fallback_title='科技')['slides']
    assert len(pages) == 12
    assert expected.issubset({page['templateSlideId'] for page in pages})
    for page in pages:
        assert [plain(e) for e in page['elements'] if e.get('textType') == 'item'] == [x['text'] for x in semantic['data']['items']]


def test_published_asset_dimensions_and_alpha_match_the_inspection_record():
    from PIL import Image
    import hashlib
    report = json.loads((ROOT / 'doc/assets/template_30_qa/asset-inspection.json').read_text(encoding='utf-8'))
    assert len(report['assets']) == 8
    for record in report['assets']:
        file = ROOT / 'backend/main_api/template' / record['file']
        with Image.open(file) as image:
            assert image.size == (record['width'], record['height'])
            if record['file'].endswith('.png'):
                assert image.mode == 'RGBA' and image.getchannel('A').getextrema() == (0, 255)
        assert hashlib.sha256(file.read_bytes()).hexdigest() == record['sha256']

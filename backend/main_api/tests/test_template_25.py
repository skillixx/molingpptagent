"""融资路演模板：通过构建器与真实渲染入口检查交付行为，测试资源隔离。"""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from html import unescape
from pathlib import Path

import pytest

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError

ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / 'utils/build_blueblack_city_pitch_template.mjs'


@pytest.fixture
def renderer(tmp_path):
    subprocess.run(['node', str(BUILDER), str(tmp_path / 'template_25.json')], check=True, capture_output=True)
    template = json.loads((tmp_path / 'template_25.json').read_text(encoding='utf-8'))
    # 渲染器只检查资源存在，隔离目录中的空文件不作为真实图片验收证据。
    for name in template['metadata']['assetFiles']:
        (tmp_path / name).write_bytes(b'fixture-only')
    return PresentationTemplateRenderer(tmp_path)


def render(renderer, kind, data, **extra):
    return renderer.render(template_id='template_25', semantic_slides=[{'type': kind, 'data': data, **extra}],
                           task_id='pitch-fixed-data', fallback_title='融资路演')['slides']


def plain(e):
    return unescape(re.sub('<[^>]+>', '', str(e.get('content', '')).replace('<br>', '\n')))


def test_long_cover_title_selects_fitting_layout_without_losing_text(renderer):
    """长标题应选大标题区，而不是由首张封面的容量直接拒绝。"""
    title = '面向未来城市绿色产业升级的智能服务平台商业发展与融资合作计划'
    result = render(renderer, 'cover', {'title': title, 'text': '完整的项目说明'})
    assert result[0]['templateSlideId'] == 'cover-city-long-title'
    texts = ''.join(plain(e) for e in result[0]['elements']).replace('\n', '')
    assert title in texts


@pytest.mark.parametrize('layout,count', [('process', 3), ('timeline', 4), ('metrics', 3), ('compare', 3)])
def test_unsupported_special_capacity_falls_back_without_losing_values(renderer, layout, count):
    """规划允许容量不符时保序降级，指标的独立 value 字段也必须保留。"""
    items = [{'title': f'要点{i}', 'text': f'完整说明{i}', **({'kind': 'metric', 'value': f'{i}万元'} if layout == 'metrics' else {})}
             for i in range(1, count + 1)]
    result = render(renderer, 'content', {'title': '专项布局容量', 'layoutKind': layout, 'items': items})
    assert all(s['templateSlideId'].startswith('content-text-') for s in result)
    texts = ''.join(plain(e) for s in result for e in s['elements'])
    assert all(item['title'] in texts and item['text'] in texts for item in items)
    if layout == 'metrics':
        assert all(item['value'] in texts for item in items)
    assert [texts.index(item['title']) for item in items] == sorted(texts.index(item['title']) for item in items)


def test_builder_inventory_determinism_and_canvas(tmp_path):
    first = tmp_path / 'first.json'
    second = tmp_path / 'second.json'
    for output in (first, second):
        subprocess.run(['node', str(BUILDER), str(output)], check=True, capture_output=True)
    assert first.read_bytes() == second.read_bytes()
    template = json.loads(first.read_text(encoding='utf-8'))
    # 开发文档是页面库存的独立来源，避免将构建器自身的 metadata 当成期望值。
    spec = (ROOT / 'doc/蓝黑城市融资路演PPT模板开发说明.md').read_text(encoding='utf-8-sig')
    expected_ids = re.findall(r'^\| \d+ \| `([^`]+)` \|', spec, re.M)
    assert len(expected_ids) == 24
    assert [s['id'] for s in template['slides']] == expected_ids
    assert Counter(s['type'] for s in template['slides']) == {'cover': 2, 'contents': 5, 'transition': 2, 'content': 13, 'end': 2}
    ids = [e['id'] for s in template['slides'] for e in s['elements']]
    assert len(ids) == len(set(ids))
    for s in template['slides']:
        for e in s['elements']:
            assert e['left'] >= 0 and e['top'] >= 0, e['id']
            if e['type'] != 'line':
                assert e['left'] + e['width'] <= 1000, e['id']
                assert e['top'] + e['height'] <= 562.5, e['id']
            if e.get('textType') in {'item', 'content'}:
                assert e['minimumFontSize'] >= 16


@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 6, 7, 13])
def test_directory_preserves_order_and_numbers(renderer, count):
    values = [f'目录主题{i:02d}' for i in range(1, count + 1)]
    result = render(renderer, 'contents', {'items': values})
    actual = [plain(e) for s in result for e in s['elements'] if e.get('textType') == 'item']
    numbers = [plain(e) for s in result for e in s['elements'] if e.get('textType') == 'itemNumber']
    assert actual == values
    assert numbers == [f'{i:02d}' for i in range(1, count + 1)]


@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 9])
def test_plain_content_preserves_original_item_order(renderer, count):
    items = [{'title': f'要点{i}', 'text': f'正文内容编号{i}。'} for i in range(count)]
    result = render(renderer, 'content', {'title': '融资业务说明', 'items': items})
    assert all(s['templateSlideId'].startswith('content-text-') for s in result)
    assert [plain(e) for s in result for e in s['elements'] if e.get('textType') == 'item'] == [x['text'] for x in items]


def test_four_long_item_titles_do_not_create_single_item_pages(renderer):
    items = [{'title': f'第{i}项面向未来城市的智能服务平台价值与商业应用完整说明', 'text': f'行动内容{i}。'} for i in range(4)]
    result = render(renderer, 'content', {'title': '完整标题保留验证', 'items': items})
    assert len(result) == 1
    assert result[0]['templateSlideId'] == 'content-text-4'
    body = ''.join(plain(e) for e in result[0]['elements'] if e.get('textType') == 'item')
    assert all(x['title'] in body and x['text'] in body for x in items)


def test_long_body_is_losslessly_paginated(renderer):
    body = '完整原文需要跨页保留所有字词和顺序。' * 100
    result = render(renderer, 'content', {'title': '长正文验证', 'items': [{'title': '完整说明', 'text': body}]})
    assert len(result) > 1
    assert ''.join(plain(e) for s in result for e in s['elements'] if e.get('textType') == 'item') == body


@pytest.mark.parametrize('count', [1, 2, 3, 4])
@pytest.mark.parametrize('size', [(1200, 800), (800, 1200), (1000, 1000)])
def test_business_images_bind_in_order_and_preserve_source_aspect(renderer, count, size):
    items = [{'title': f'案例{i}', 'text': f'图片对应说明{i}'} for i in range(count)]
    sources = [{'src': f'https://example.invalid/image-{i}.jpg', 'width': size[0], 'height': size[1]} for i in range(count)]
    result = render(renderer, 'content', {'title': '业务图片', 'items': items}, images=sources)
    assert len(result) == 1
    pictures = [e for e in result[0]['elements'] if e.get('imageType') == 'content']
    assert [e['src'] for e in pictures] == [s['src'] for s in sources]
    for e in pictures:
        lo, hi = e['clip']['range']
        assert 0 <= lo[0] < hi[0] <= 100 and 0 <= lo[1] < hi[1] <= 100
        cropped_ratio = size[0] * (hi[0] - lo[0]) / (size[1] * (hi[1] - lo[1]))
        assert cropped_ratio == pytest.approx(e['width'] / e['height'])


def test_mismatched_image_count_is_not_silently_accepted(renderer):
    with pytest.raises(TemplateRenderError):
        render(renderer, 'content', {'title': '数量不匹配', 'items': [{'title': '一', 'text': '说明'}, {'title': '二', 'text': '说明'}]},
               images=[{'src': 'https://example.invalid/a.jpg', 'width': 1200, 'height': 800}])


@pytest.mark.parametrize('kind,count', [('process', 4), ('timeline', 3), ('metrics', 4), ('compare', 2)])
def test_supported_special_layout_preserves_text_and_values(renderer, kind, count):
    items = [{'title': f'主题{i}', 'text': f'实际说明{i}', **({'value': f'{i + 1}万元'} if kind == 'metrics' else {})} for i in range(count)]
    result = render(renderer, 'content', {'title': '专项内容', 'layoutKind': kind, 'items': items})
    assert len(result) == 1
    assert result[0]['templateSlideId'] == f'content-{kind}-{count}'
    texts = ''.join(plain(e) for e in result[0]['elements'])
    assert all(x['title'] in texts and x['text'] in texts for x in items)
    if kind == 'metrics':
        assert all(x['value'] in texts for x in items)


def test_transition_rotation_and_end_contacts(renderer):
    pages = renderer.render(template_id='template_25', semantic_slides=[{'type': 'transition', 'data': {'title': f'章节{i}', 'text': '章节导语'}} for i in range(1, 7)], task_id='sections', fallback_title='章节')['slides']
    assert [s['templateSlideId'] for s in pages] == ['transition-building', 'transition-meeting'] * 3
    assert [plain(e) for s in pages for e in s['elements'] if e.get('textType') == 'partNumber'] == ['01','02','03','04','05','06']
    contacts = [{'title': '联系人', 'text': '项目负责人'}, {'title': '邮箱', 'text': 'pitch@example.invalid'}]
    end = render(renderer, 'end', {'title': '期待合作', 'items': contacts})[0]
    assert end['templateSlideId'] == 'end-contact'
    text = ''.join(plain(e) for e in end['elements'])
    assert all(x['title'] in text and x['text'] in text for x in contacts)


def test_legacy_template_does_not_opt_into_new_fallback(renderer):
    source = renderer.template_root / 'template_25.json'
    template = json.loads(source.read_text(encoding='utf-8'))
    template.pop('unsupportedLayoutPolicy')
    for s in template['slides']:
        s.pop('fitTitleBeforeVariant', None)
    source.write_text(json.dumps(template), encoding='utf-8')
    legacy = PresentationTemplateRenderer(renderer.template_root)
    with pytest.raises(TemplateRenderError):
        render(legacy, 'content', {'title': '原有规则', 'layoutKind': 'process', 'items': [{'title': '单项', 'text': '保留原先拒绝行为'}]})


def test_real_background_assets_and_template_resource_references():
    """正式成品必须可解码并达到尺寸要求，不能用渲染器测试空文件替代素材验收。"""
    from PIL import Image
    template_root = ROOT / 'backend/main_api/template'
    template = json.loads((template_root / 'template_25.json').read_text(encoding='utf-8'))
    expected = {f'template_25_asset_bg_{name}_v1.jpg' for name in ['city_cover', 'nebula_contents', 'building_section', 'meeting_section', 'city_end']}
    assert set(template['metadata']['assetFiles']) == expected
    references = {e['src'].rsplit('/', 1)[-1] for s in template['slides'] for e in s['elements'] if e.get('type') == 'image'}
    assert references == expected
    for name in expected:
        with Image.open(template_root / name) as image:
            image.load()
            assert image.size == (1920, 1080) and image.mode == 'RGB' and image.format == 'JPEG'


def test_fallback_does_not_mutate_callers_input_and_unknown_layout_still_errors(renderer):
    data = {'title': '数据保留', 'layoutKind': 'metrics', 'items': [{'title': f'指标{i}', 'value': f'{i}万元', 'text': '说明', 'kind': 'metric'} for i in range(3)]}
    before = json.dumps(data, ensure_ascii=False)
    render(renderer, 'content', data)
    assert json.dumps(data, ensure_ascii=False) == before
    with pytest.raises(TemplateRenderError):
        render(renderer, 'content', {'title': '未知布局', 'layoutKind': 'typo-layout', 'items': [{'title': '事项', 'text': '内容'}]})


@pytest.mark.parametrize('kind,count', [('process', 4), ('timeline', 3), ('metrics', 4), ('compare', 2)])
def test_special_layout_with_business_images_keeps_every_image(renderer, kind, count):
    """专项页没有图片槽时降级图文页，不能返回成功却丢掉合法图片。"""
    items = [{'title': f'主题{i}', 'text': f'说明{i}', **({'value': f'{i + 1}万元'} if kind == 'metrics' else {})} for i in range(count)]
    images = [{'src': f'https://example.invalid/asset-{i}.jpg', 'width': 1200, 'height': 800} for i in range(count)]
    pages = render(renderer, 'content', {'title': '图文不能丢失', 'layoutKind': kind, 'items': items}, images=images)
    assert [e['src'] for s in pages for e in s['elements'] if e.get('imageType') == 'content'] == [i['src'] for i in images]
    assert all(s['templateSlideId'].startswith('content-image-') for s in pages)
    text = ''.join(plain(e) for s in pages for e in s['elements'])
    assert all(i['title'] in text and i['text'] in text and (kind != 'metrics' or i['value'] in text) for i in items)


@pytest.mark.parametrize('kind,count,repeats', [('timeline', 3, 1), ('process', 4, 3), ('metrics', 4, 4), ('compare', 2, 10)])
def test_special_body_overflow_falls_back_losslessly(renderer, kind, count, repeats):
    """数量匹配也要按专项正文框容量判断；降级分页须逐字保留原文。"""
    body = '完成核心产品测试并启动重点客户试点，收集使用反馈后完善交付方案并形成规模化推广准备。' * repeats
    items = [{'title': f'节点{i}', 'text': body, **({'value': f'{i + 1}万元'} if kind == 'metrics' else {})} for i in range(count)]
    pages = render(renderer, 'content', {'title': '实际长度专项说明', 'layoutKind': kind, 'items': items})
    assert all(s['templateSlideId'].startswith('content-text-') for s in pages)
    actual = ''.join(plain(e) for s in pages for e in s['elements'] if e.get('textType') == 'item')
    expected = ''.join((i['value'] + '\n' if kind == 'metrics' else '') + body for i in items)
    assert actual == expected


def test_metrics_without_optional_description_keep_titles_and_values(renderer):
    """只给指标名称与数值是有效输入，空说明不能连带删除整个业务组。"""
    items = [{'title': f'指标{i}', 'value': f'{i + 1}万元'} for i in range(4)]
    pages = render(renderer, 'content', {'title': '指标概览', 'layoutKind': 'metrics', 'items': items})
    text = ''.join(plain(e) for s in pages for e in s['elements'])
    assert all(i['title'] in text and i['value'] in text for i in items)


def test_fitting_compare_page_is_not_split_by_ordinary_body_capacity(renderer):
    """专项页能装下的正文不应被普通两栏的更小估算拆成非法单项对比页。"""
    items = [{'title': 'item0', 'text': '文' * 178}, {'title': 'item1', 'text': '文' * 10}]
    pages = render(renderer, 'content', {'title': '对比容量边界', 'layoutKind': 'compare', 'items': items})
    assert len(pages) == 1 and pages[0]['templateSlideId'] == 'content-compare-2'
    assert [plain(e) for e in pages[0]['elements'] if e.get('textType') == 'item'] == [i['text'] for i in items]


@pytest.mark.parametrize('template_id', ['template_21', 'template_22', 'template_23', 'template_24'])
@pytest.mark.parametrize('mixed_description', [False, True])
def test_existing_metric_templates_preserve_empty_optional_descriptions(template_id, mixed_description):
    """公共指标说明清理的改动也要覆盖已有模板，防止修新模板时丢掉旧指标。"""
    renderer = PresentationTemplateRenderer(ROOT / 'backend/main_api/template')
    items = [{'title': f'指标{i}', 'value': f'{i + 1}%', 'text': '有效说明' if mixed_description and i % 2 else ''} for i in range(4)]
    pages = renderer.render(template_id=template_id, semantic_slides=[{'type': 'content', 'data': {'title': '已有指标模板', 'layoutKind': 'metrics', 'items': items}}],
                            task_id='legacy-metric-body-regression', fallback_title='指标')['slides']
    text = ''.join(plain(e) for s in pages for e in s['elements'])
    assert all(i['title'] in text and i['value'] in text for i in items)
    if mixed_description:
        assert text.count('有效说明') == 2

"""使用固定输入验证深蓝电路模板的公开构建与填充行为。"""
from __future__ import annotations

import json
import re
import subprocess
from html import unescape
from pathlib import Path

import pytest

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError

ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / 'utils/build_deepblue_circuit_security_template.mjs'


def build_at(output: Path, stage: str = 'production') -> dict:
    subprocess.run(['node', str(BUILDER), str(output), '--stage', stage], check=True, capture_output=True)
    return json.loads(output.read_text(encoding='utf-8'))


def plain(element: dict) -> str:
    return unescape(re.sub('<[^>]+>', '', str(element.get('content', '')).replace('<br>', '\n')))


@pytest.fixture
def renderer(tmp_path):
    template = build_at(tmp_path / 'template_26.json')
    # 此测试只验证填充协议，临时占位资源不充当真实图片验收证据。
    for filename in template['metadata']['assetFiles']:
        (tmp_path / filename).write_bytes(b'fixture-only')
    return PresentationTemplateRenderer(tmp_path)


def render(renderer, kind, data, **extra):
    return renderer.render(template_id='template_26', semantic_slides=[{'type': kind, 'data': data, **extra}],
                           task_id='security-fixed-data', fallback_title='网络安全')['slides']


def test_builder_matches_approved_inventory_and_mvp_subset(tmp_path):
    """从用户规划读取独立期望值，避免用构建器的自身元数据证明库存。"""
    spec = (ROOT / 'doc/深蓝电路网络安全PPT模板开发说明.md').read_text(encoding='utf-8-sig')
    rows = re.findall(r'^\| \d+ \| `([^`]+)` \|.*?\| (基础版|完整版新增) \|', spec, re.M)
    assert len(rows) == 22
    production = build_at(tmp_path / 'template_26.json')
    mvp = build_at(tmp_path / 'mvp.json', 'mvp')
    assert [s['id'] for s in production['slides']] == [r[0] for r in rows]
    assert [s['id'] for s in mvp['slides']] == [r[0] for r in rows if r[1] == '基础版']
    assert len(mvp['slides']) == 14
    assert (production['width'], production['height']) == (1000, 562.5)
    assert len(production['metadata']['assetFiles']) == 8


def test_four_long_titles_preserve_originals_on_one_four_item_page(renderer):
    """原题回填后的四条正文必须仍留在四项页，不能为过关改用其他库存。"""
    items = [{'title': f'第{i}项面向业务持续发展的网络安全风险治理与实施保障完整说明', 'text': f'行动内容{i}。'} for i in range(4)]
    slides = render(renderer, 'content', {'title': '安全方案', 'items': items})
    assert len(slides) == 1
    assert slides[0]['templateSlideId'] == 'content-text-4'
    body = ''.join(plain(e) for e in slides[0]['elements'] if e.get('textType') == 'item')
    assert all(x['title'] in body and x['text'] in body for x in items)
    assert [body.index(x['title']) for x in items] == sorted(body.index(x['title']) for x in items)


@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 6, 7, 13])
def test_directory_preserves_all_items_and_continuous_numbers(renderer, count):
    items = [f'目录主题{i:02d}' for i in range(1, count + 1)]
    slides = render(renderer, 'contents', {'items': items})
    assert [plain(e) for s in slides for e in s['elements'] if e.get('textType') == 'item'] == items
    assert [plain(e) for s in slides for e in s['elements'] if e.get('textType') == 'itemNumber'] == [f'{i:02d}' for i in range(1, count + 1)]


@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 9])
def test_ordinary_content_keeps_original_order(renderer, count):
    items = [{'title': f'要点{i}', 'text': f'完整正文编号{i}。'} for i in range(count)]
    slides = render(renderer, 'content', {'title': '安全建设', 'items': items})
    assert [plain(e) for s in slides for e in s['elements'] if e.get('textType') == 'item'] == [x['text'] for x in items]
    assert all(s['templateSlideId'].startswith('content-text-') for s in slides)


def test_long_body_paginates_without_losing_characters(renderer):
    body = '保留业务原文、风险描述和每一项整改行动。' * 100
    slides = render(renderer, 'content', {'title': '长正文测试', 'items': [{'title': '实施说明', 'text': body}]})
    assert len(slides) > 1
    assert ''.join(plain(e) for s in slides for e in s['elements'] if e.get('textType') == 'item') == body


def test_long_cover_uses_large_title_layout_without_truncation(renderer):
    title = '面向企业业务持续发展的网络安全风险治理体系建设与实施保障项目计划'
    slides = render(renderer, 'cover', {'title': title, 'text': '项目实施说明'})
    assert slides[0]['templateSlideId'] == 'cover-long-title'
    assert title in ''.join(plain(e) for e in slides[0]['elements']).replace('\n', '')


@pytest.mark.parametrize('count', [1, 2, 3, 4])
@pytest.mark.parametrize('dimensions', [(1200, 800), (800, 1200), (1000, 1000)])
def test_images_bind_to_items_and_crop_without_stretching(renderer, count, dimensions):
    items = [{'title': f'业务{i}', 'text': f'对应图片说明{i}。'} for i in range(count)]
    images = [{'src': f'https://example.invalid/security-{i}.jpg', 'width': dimensions[0], 'height': dimensions[1]} for i in range(count)]
    slides = render(renderer, 'content', {'title': '业务场景', 'items': items}, images=images)
    assert len(slides) == 1
    actual = [e for e in slides[0]['elements'] if e.get('imageType') == 'content']
    assert [e['src'] for e in actual] == [i['src'] for i in images]
    assert all(e['src'].startswith('/api/data/template_26_') for e in slides[0]['elements'] if e.get('imageType') == 'decoration')
    for e in actual:
        lo, hi = e['clip']['range']
        assert 0 <= lo[0] < hi[0] <= 100 and 0 <= lo[1] < hi[1] <= 100
        assert dimensions[0] * (hi[0] - lo[0]) / (dimensions[1] * (hi[1] - lo[1])) == pytest.approx(e['width'] / e['height'])


def test_mismatched_image_counts_raise_a_clear_error(renderer):
    with pytest.raises(TemplateRenderError):
        render(renderer, 'content', {'title': '图片数量不匹配', 'items': [{'title': '一', 'text': '说明一'}, {'title': '二', 'text': '说明二'}]},
               images=[{'src': 'https://example.invalid/one.jpg', 'width': 1200, 'height': 800}])


@pytest.mark.parametrize('kind,count,expected', [('process', 4, 'content-process-4'), ('metrics', 4, 'content-metrics-4'), ('hub-spoke', 6, 'content-hub-6')])
def test_special_layout_preserves_labels_values_and_central_subject(renderer, kind, count, expected):
    items = [{'title': f'能力{i}', 'text': f'能力说明{i}。', **({'value': f'{i + 1}万元'} if kind == 'metrics' else {})} for i in range(count)]
    slides = render(renderer, 'content', {'title': '安全治理体系', 'layoutKind': kind, 'items': items})
    assert len(slides) == 1
    assert slides[0]['templateSlideId'] == expected
    texts = ''.join(plain(e) for e in slides[0]['elements'])
    assert '安全治理体系' in texts
    assert all(x['title'] in texts and x['text'] in texts for x in items)
    if kind == 'metrics':
        assert all(x['value'] in texts for x in items)
    if kind == 'hub-spoke':
        assert sum(e['type'] == 'line' for e in slides[0]['elements']) >= 6


@pytest.mark.parametrize('kind,count', [('process', 3), ('metrics', 3), ('hub-spoke', 5)])
def test_special_count_mismatch_falls_back_preserving_information(renderer, kind, count):
    items = [{'title': f'主题{i}', 'text': f'完整说明{i}', **({'kind': 'metric', 'value': f'{i + 1}小时'} if kind == 'metrics' else {})} for i in range(count)]
    slides = render(renderer, 'content', {'title': '容量适配', 'layoutKind': kind, 'items': items})
    text = ''.join(plain(e) for s in slides for e in s['elements'])
    assert all(s['templateSlideId'].startswith('content-text-') for s in slides)
    assert all(x['title'] in text and x['text'] in text for x in items)
    if kind == 'metrics':
        assert all(x['value'] in text for x in items)


def test_end_action_keeps_action_body_and_empty_description_does_not_delete_metrics(renderer):
    slides = render(renderer, 'end', {'title': '交流与行动', 'text': '后续安排', 'items': [{'title': '负责人', 'text': '示例负责人'}, {'title': '行动', 'text': '制定整改计划'}]})
    assert slides[0]['templateSlideId'] == 'end-action'
    text = ''.join(plain(e) for e in slides[0]['elements'])
    assert '示例负责人' in text and '制定整改计划' in text
    metrics = render(renderer, 'content', {'title': '指标展示', 'layoutKind': 'metrics', 'items': [{'title': f'指标{i}', 'value': f'{i}%', 'text': ''} for i in range(4)]})
    text = ''.join(plain(e) for e in metrics[0]['elements'])
    assert all(f'指标{i}' in text and f'{i}%' in text for i in range(4))


@pytest.mark.parametrize('count', [3, 4])
def test_separate_metric_units_remain_editable_and_survive_fallback(renderer, count):
    """单位是独立业务字段，专项页与回退正文都不能静默丢弃。"""
    items = [{'title': f'指标{i}', 'value': i, 'unit': '万元', 'text': f'说明{i}'} for i in range(count)]
    slides = render(renderer, 'content', {'title': '独立单位验证', 'layoutKind': 'metrics', 'items': items})
    text = ''.join(plain(e) for s in slides for e in s['elements'])
    assert text.count('万元') == count
    if count == 4:
        values = [plain(e) for e in slides[0]['elements'] if e.get('textType') == 'itemNumber']
        units = [plain(e) for e in slides[0]['elements'] if e.get('textType') == 'itemUnit']
        assert values == [str(i) for i in range(4)]
        assert units == ['万元'] * 4
    else:
        assert all(s['templateSlideId'].startswith('content-text-') for s in slides)


def test_hub_keeps_semantic_item_order_in_editable_objects(renderer):
    """关系图的对象顺序与视觉行序都应对应原始条目顺序。"""
    items = [{'title': f'节点{i}', 'text': f'说明顺序{i}'} for i in range(6)]
    slides = render(renderer, 'content', {'title': '中心主题', 'layoutKind': 'hub-spoke', 'items': items})
    assert [plain(e) for e in slides[0]['elements'] if e.get('textType') == 'item'] == [x['text'] for x in items]

"""用固定数据检查乐章雅韵模板的实际选版、信息保留与图片协议。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

import pytest

from backend.main_api.workers.template_renderer import PresentationTemplateRenderer, TemplateRenderError

ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / 'utils/build_music_theme_template.mjs'


def build_at(output):
    subprocess.run(['node', str(BUILDER), str(output)], check=True, capture_output=True)
    return json.loads(output.read_text(encoding='utf-8'))


def plain(element):
    return unescape(re.sub('<[^>]+>', '', str(element.get('content', '')).replace('<br>', '\n')))


@pytest.fixture
def renderer(tmp_path):
    template = build_at(tmp_path / 'template_29.json')
    # 单测中的资源只满足加载检查，不能用作图片质量或浏览器验收证据。
    for filename in template['metadata']['assetFiles']:
        (tmp_path / filename).write_bytes(b'fixture-only')
    return PresentationTemplateRenderer(tmp_path)


def render(renderer, kind, data, **extra):
    return renderer.render(template_id='template_29', semantic_slides=[{'type': kind, 'data': data, **extra}],
                           task_id='music-fixed', fallback_title='乐章雅韵')['slides']


def test_builder_matches_user_inventory_and_is_deterministic(tmp_path):
    spec = (ROOT / 'doc/乐章雅韵音乐主题PPT模板开发说明.md').read_text(encoding='utf-8-sig')
    expected = re.findall(r'^\| \d+ \| `([^`]+)` \| `(cover|contents|transition|content|end)`', spec, re.M)
    assert len(expected) == 18
    one = build_at(tmp_path / 'one.json')
    two = build_at(tmp_path / 'two.json')
    assert one == two
    assert [(s['id'], s['type']) for s in one['slides']] == expected
    assert (one['width'], one['height']) == (1000, 562.5)
    assert len(set(one['metadata']['assetFiles'])) == 5
    assert len({e['id'] for s in one['slides'] for e in s['elements']}) == sum(len(s['elements']) for s in one['slides'])


def test_long_item_titles_stay_on_one_four_item_page(renderer):
    items = [{'title': f'第{i}项面向未来业务发展与项目协作的完整行动目标及实施路径说明', 'text': f'执行行动{i}。'} for i in range(4)]
    pages = render(renderer, 'content', {'title': '内容完整性', 'items': items})
    assert len(pages) == 1 and pages[0]['templateSlideId'] == 'content-text-4'
    bodies = [plain(e) for e in pages[0]['elements'] if e.get('textType') == 'item']
    assert all(item['title'] in body and item['text'] in body for item, body in zip(items, bodies, strict=True))


@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 6, 7, 13])
def test_contents_keep_names_order_and_continuous_numbers(renderer, count):
    names = [f'章节{i:02d}' for i in range(1, count + 1)]
    pages = render(renderer, 'contents', {'items': names})
    assert [plain(e) for s in pages for e in s['elements'] if e.get('textType') == 'item'] == names
    assert [plain(e) for s in pages for e in s['elements'] if e.get('textType') == 'itemNumber'] == [f'{i:02d}' for i in range(1, count + 1)]


@pytest.mark.parametrize('count', [1, 2, 3, 4, 5, 9])
def test_ordinary_items_keep_original_order(renderer, count):
    items = [{'title': f'要点{i}', 'text': f'原始正文{i}，保留每一条信息。'} for i in range(count)]
    pages = render(renderer, 'content', {'title': '工作说明', 'items': items})
    assert all(s['templateSlideId'].startswith('content-text-') for s in pages)
    assert [plain(e) for s in pages for e in s['elements'] if e.get('textType') == 'item'] == [x['text'] for x in items]


def test_long_body_and_cover_preserve_all_characters(renderer):
    body = '完整保留需求说明、实施计划和各项交付安排。' * 100
    pages = render(renderer, 'content', {'title': '长正文', 'items': [{'title': '计划', 'text': body}]})
    assert len(pages) > 1
    assert ''.join(plain(e) for s in pages for e in s['elements'] if e.get('textType') == 'item') == body
    title = '面向未来业务持续发展与团队协作的项目建设目标实施路径及阶段成果汇报'
    page = render(renderer, 'cover', {'title': title, 'text': '完整副标题'})[0]
    assert page['templateSlideId'] == 'cover-long-title'
    assert title in ''.join(plain(e) for e in page['elements']).replace('\n', '')


def test_cover_subtitle_and_supplementary_information_are_preserved(renderer):
    subtitle = '项目介绍与阶段成果汇报\n汇报人：示例团队\n日期：2026年9月'
    page = render(renderer, 'cover', {'title': '向光而行', 'text': subtitle})[0]
    contents = '\n'.join(plain(e) for e in page['elements'] if e.get('textType') == 'content')
    assert all(line in contents for line in subtitle.splitlines())


@pytest.mark.parametrize('count', [1, 2, 3, 4])
@pytest.mark.parametrize('dimensions', [(1200, 800), (800, 1200), (1000, 1000)])
def test_images_bind_crop_and_protect_decorations(renderer, count, dimensions):
    items = [{'title': f'案例{i}', 'text': f'图片对应说明{i}'} for i in range(count)]
    images = [{'src': f'https://example.invalid/image-{i}.jpg', 'width': dimensions[0], 'height': dimensions[1]} for i in range(count)]
    page = render(renderer, 'content', {'title': '图文展示', 'items': items}, images=images)[0]
    pictures = [e for e in page['elements'] if e.get('imageType') == 'content']
    assert [p['src'] for p in pictures] == [p['src'] for p in images]
    assert all(e['src'].startswith('/api/data/template_29_') for e in page['elements'] if e.get('imageType') == 'decoration')
    for picture in pictures:
        lo, hi = picture['clip']['range']
        assert 0 <= lo[0] < hi[0] <= 100 and 0 <= lo[1] < hi[1] <= 100
        assert dimensions[0] * (hi[0] - lo[0]) / (dimensions[1] * (hi[1] - lo[1])) == pytest.approx(picture['width'] / picture['height'])


def test_image_count_and_missing_dimensions_fail_clearly(renderer):
    data = {'title': '图片异常', 'items': [{'title': '一', 'text': '内容一'}, {'title': '二', 'text': '内容二'}]}
    with pytest.raises(TemplateRenderError):
        render(renderer, 'content', data, images=[{'src': 'https://example.invalid/one.jpg', 'width': 1200, 'height': 800}])
    with pytest.raises(TemplateRenderError):
        render(renderer, 'content', {'title': '图片尺寸缺失', 'items': data['items'][:1]}, images=[{'src': 'https://example.invalid/one.jpg'}])


def test_missing_resource_is_not_silently_accepted(tmp_path):
    build_at(tmp_path / 'template_29.json')
    with pytest.raises(TemplateRenderError) as error:
        render(PresentationTemplateRenderer(tmp_path), 'cover', {'title': '缺失素材'})
    assert error.value.code == 'TEMPLATE_RESOURCE_MISSING'


def test_production_assets_match_declared_dimensions_and_alpha():
    """读取正式图片本身检查格式与透明中心，不依赖处理脚本自己的成功标记。"""
    from PIL import Image
    template = json.loads((ROOT / 'backend/main_api/template/template_29.json').read_text(encoding='utf-8'))
    for filename in template['metadata']['assetFiles']:
        with Image.open(ROOT / 'backend/main_api/template' / filename) as image:
            if filename.endswith('.jpg'):
                assert image.mode == 'RGB' and image.size == (1920, 1080)
            else:
                assert image.mode == 'RGBA' and image.getchannel('A').getextrema()[0] == 0
                assert image.size == (1200, 1600) and image.getchannel('A').getextrema()[1] == 255



def test_real_api_registration_and_asset_reading_without_production_dependencies():
    """隔离环境导入真实主 API，验证注册与正式资源读取，不连接生产依赖。"""
    environment = {key: os.environ[key] for key in ('PATH', 'PATHEXT', 'SYSTEMROOT', 'TEMP', 'TMP', 'WINDIR') if key in os.environ}
    environment.update(APP_ENV='test', PERSISTENCE_ENABLED='false', SSO_ENABLED='false', BILLING_ENABLED='false',
                       STORAGE_ENABLED='false', TASK_WORKER_ENABLED='false', RELEASE_CHANNEL='test', RELEASE_COMMIT='template-29-test')
    code = (
        "import json,dotenv;dotenv.load_dotenv=lambda *a,**k:False;import main;"
        "from fastapi.testclient import TestClient;client=TestClient(main.app);"
        "response=client.get('/templates');items=response.json()['data'];"
        "cover=client.get('/data/template_29.jpg');data=client.get('/data/template_29.json');"
        "print(json.dumps({'status':response.status_code,'target':[x for x in items if x['id']=='template_29'],"
        "'cover':cover.status_code,'data':data.status_code,'slides':len(data.json()['slides'])}))"
    )
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT / 'backend/main_api', env=environment,
                            capture_output=True, text=True, check=True, timeout=25)
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {
        'status': 200, 'target': [{'name': '乐章雅韵·音乐主题', 'id': 'template_29', 'cover': '/api/data/template_29.jpg'}],
        'cover': 200, 'data': 200, 'slides': 18,
    }


@pytest.mark.parametrize('variant,layout', [('music','cover-music'),('long-title','cover-long-title')])
def test_explicit_cover_variants_are_reachable(renderer, variant, layout):
    assert render(renderer, 'cover', {'title':'协作共进','text':'完整补充信息','variant':variant})[0]['templateSlideId'] == layout


@pytest.mark.parametrize('variant', ['left','right'])
def test_single_image_variants_are_reachable(renderer, variant):
    data={'title':'单图对应','variant':variant,'items':[{'title':'自然采光','text':'保留图文关联'}]}
    page=render(renderer,'content',data,images=[{'src':'https://example.invalid/example.jpg','width':800,'height':1200}])[0]
    assert page['templateSlideId'] == f'content-image-{variant}-1'


def test_end_title_and_supplementary_info_are_filled(renderer):
    page=render(renderer,'end',{'title':'期待再次合作','text':'项目组\n下一步：整理建议'})[0]
    assert [plain(e) for e in page['elements'] if e.get('textType')=='title'] == ['期待再次合作']
    body=''.join(plain(e) for e in page['elements'] if e.get('textType')=='content')
    assert '项目组' in body and '下一步：整理建议' in body

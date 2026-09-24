"""核对音乐模板实际交付与证据，仅生成待人工确认记录，不闭合总 Goal。"""
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_29_qa'
TEMPLATES = ROOT / 'backend/main_api/template'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((QA / name).read_text(encoding='utf-8-sig'))


def persist_manifest(path, manifest):
    """同一交付版本已经人工确认时保留确认；变更版本不得继承旧结论。"""
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8-sig'))
        unchanged = all(previous.get(key) == manifest.get(key) for key in ('candidate', 'productionFiles', 'evidence'))
        if unchanged and previous.get('status') == 'COMPLETED' and previous.get('humanConfirmation'):
            return previous
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main():
    template_path = TEMPLATES / 'template_29.json'
    template = json.loads(template_path.read_text(encoding='utf-8'))
    spec = (ROOT / 'doc/乐章雅韵音乐主题PPT模板开发说明.md').read_text(encoding='utf-8')
    expected = re.findall(r'^\| \d+ \| `([^`]+)` \| `(cover|contents|transition|content|end)`', spec, re.M)
    assert len(expected) == 18 and [(s['id'], s['type']) for s in template['slides']] == expected
    assets = read('asset-inspection.json')['assets']
    assert len(assets) == 5 and {a['file'] for a in assets} == set(template['metadata']['assetFiles'])
    for asset in assets:
        path = TEMPLATES / asset['file']
        assert digest(path) == asset['sha256']
        with Image.open(path) as image:
            if path.suffix == '.png':
                assert image.size == (1200, 1600) and image.mode == 'RGBA'
                assert image.getchannel('A').getextrema() == (0, 255)
            else:
                assert image.size == (1920, 1080) and image.mode == 'RGB'

    names = ['editor-verified/summary.json', 'fit-summary.json', 'online-save-summary.json',
             'persistence-summary.json', 'image-failure-summary.json', 'real-handler-summary.json',
             'native-render-summary.json', 'runtime/runtime-summary.json', 'development-checks.json']
    evidence = {name: read(name) for name in names}
    assert all(item['status'] == 'PASS' for item in evidence.values())
    editor = evidence['editor-verified/summary.json']
    assert editor['sourceSha256'] == digest(QA / 'production-document.json')
    assert editor['pptxSha256'] == digest(QA / 'editor-verified/roundtrip.pptx')
    assert editor['slideCount'] == 18 and editor['missingTexts'] == [] and editor['jsonFullStateEqual']
    assert editor['pptxEditorReimport'] and editor['exportRetrySucceeded'] and all(editor['uiEdits'].values())
    assert len(editor['replacementResults']) == 33 and all(x['decorationProtected'] for x in editor['replacementResults'])
    assert len(editor['viewports']) == 4 and all(x['withinViewport'] for x in editor['viewports'])
    fit = evidence['fit-summary.json']
    assert len(fit['selectors']) == 4 and all(not x['problems'] for x in fit['stressPages'])
    assert fit['previewWriteBlocked']
    saved = evidence['online-save-summary.json']
    assert saved['newBrowserContextReloadEqual'] and saved['saveFailureVisible'] and saved['saveRetrySucceeded']
    assert evidence['persistence-summary.json']['sourceSha256'] == digest(QA / 'editor-verified/edited.json')
    assert evidence['image-failure-summary.json']['retrySucceeded']
    handler = evidence['real-handler-summary.json']
    assert handler['workerStatus'] == 'succeeded' and handler['slideCount'] == 18
    assert set(handler['reachedStableLayoutIds']) == {p['id'] for p in template['slides']}
    assert not handler['realTextModelCalls'] and not handler['productionQueueWrites']

    # 比对演示软件实际读取的原生文字，不以 ZIP 可解压或截图成功代替可编辑性验证。
    pptx = QA / '乐章雅韵音乐主题-18版式样例.pptx'
    native = evidence['native-render-summary.json']
    assert digest(pptx) == digest(QA / 'editor-verified/music-18-layouts.pptx') == native['sourceSha256']
    document = read('production-document.json')
    normal = lambda value: re.sub(r'\s+', '', unescape(re.sub('<[^>]+>', '', value)))
    comparisons = []
    for index, (expected_slide, actual_slide) in enumerate(zip(document['slides'], native['pages'], strict=True), 1):
        text = '|'.join(normal(value) for value in actual_slide['editableTexts'])
        missing = [normal(e['content']) for e in expected_slide['elements'] if e.get('content') and normal(e['content']) not in text]
        assert not missing, f'第 {index} 页原生文字缺失：{missing}'
        comparisons.append({'page': index, 'nativeEditableTexts': len(actual_slide['editableTexts']), 'missing': missing})
    (QA / 'native-text-comparison.json').write_text(json.dumps({'status':'PASS', 'sourceSha256':digest(pptx), 'slides':comparisons}, ensure_ascii=False, indent=2), encoding='utf-8')
    names.append('native-text-comparison.json')
    suites = ET.parse(QA / 'unit-tests.xml').getroot().findall('testsuite')
    tests = sum(int(s.get('tests', 0)) for s in suites)
    assert tests >= 39 and all(int(s.get('failures', 0)) + int(s.get('errors', 0)) == 0 for s in suites)
    names.append('unit-tests.xml')
    paths = [ROOT / 'backend/main_api/main.py', ROOT / 'backend/main_api/workers/template_renderer.py',
             template_path, TEMPLATES / 'template_29.jpg', QA / 'production-document.json', pptx]
    paths += [ROOT / name for name in ('frontend/src/hooks/useExport.ts', 'frontend/src/hooks/useImport.ts',
                                     'frontend/src/hooks/templateImageProtocol.ts', 'utils/build_music_theme_template.mjs',
                                     'utils/prepare_music_source_assets.py', 'utils/render_music_source_assets.ps1')]
    paths += sorted((ROOT / 'utils').glob('*template_29*'))
    paths += sorted((ROOT / 'backend/main_api/tests').glob('test_template_29*.py'))
    paths += [TEMPLATES / a['file'] for a in assets]
    fingerprints = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}
    candidate = 'template_29-' + hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()[:12]
    manifest = {'status':'AWAITING_HUMAN_CONFIRMATION', 'statusText':'自动检查通过，待人工确认',
        'candidate':candidate, 'templateId':'template_29', 'humanConfirmation':None,
        'createdAt':datetime.now(timezone.utc).isoformat(),
        'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        'baseCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'layoutCount':18, 'assetCount':5, 'backendTests':tests, 'stressPages':len(fit['stressPages']),
        'imageReplacementChecks':33, 'productionFiles':fingerprints,
        'evidence':{name:digest(QA / name) for name in names},
        'previewUrl':'http://127.0.0.1:5781/__template29', 'selectorUrl':'http://127.0.0.1:5781/app',
        'onlineSavedExampleUrl':saved['url'], 'productionWrites':False, 'gitDeliveryPerformed':False}
    manifest = persist_manifest(QA / 'candidate-manifest.json', manifest)
    print(json.dumps({key:manifest[key] for key in ('status','candidate','layoutCount','assetCount','backendTests','stressPages')}))


if __name__ == '__main__':
    main()

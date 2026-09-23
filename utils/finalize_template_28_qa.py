"""核对本次交付文件与证据，准备待人工确认记录，不完成实际 Goal。"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_28_qa'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((QA / name).read_text(encoding='utf-8-sig'))


def persist_manifest(path, manifest):
    """集中保存交付记录，便于验证复核与人工确认之间的状态约定。"""
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8-sig'))
        # 同一候选的实现和证据都未变化时，复核只读取既有确认，不撤销用户结论。
        unchanged = all(previous.get(key) == manifest.get(key)
                        for key in ('candidate', 'productionFiles', 'evidence'))
        if unchanged and previous.get('status') == 'COMPLETED' and previous.get('humanConfirmation'):
            return previous
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main():
    spec = (ROOT / 'doc/青绿几何清新商务PPT模板开发说明.md').read_text(encoding='utf-8')
    template_path = ROOT / 'backend/main_api/template/template_28.json'
    template = json.loads(template_path.read_text(encoding='utf-8'))
    expected = re.findall(r'^\| \d+ \| `([^`]+)` \| `(cover|contents|transition|content|end)`', spec, re.M)
    assert len(expected) == 18 and [(s['id'], s['type']) for s in template['slides']] == expected
    assets = template['metadata']['assetFiles']
    assert len(assets) == len(set(assets)) == 5
    for filename in assets:
        with Image.open(template_path.parent / filename) as im:
            assert im.size == (1920, 1080)
            if filename.endswith('.png'):
                assert im.mode == 'RGBA' and im.getpixel((960, 540))[3] == 0
            else:
                assert im.mode == 'RGB'
    names = ['editor-verified/summary.json', 'fit-summary.json', 'online-save-summary.json',
             'persistence-summary.json', 'image-failure-summary.json', 'real-handler-summary.json',
             'native-render-summary.json', 'native-text-comparison.json', 'runtime/runtime-summary.json']
    evidence = {name: read(name) for name in names}
    assert all(v['status'] == 'PASS' for v in evidence.values())
    editor = evidence['editor-verified/summary.json']
    assert editor['sourceSha256'] == digest(QA / 'production-document.json')
    assert editor['pptxSha256'] == digest(QA / 'editor-verified/roundtrip.pptx')
    assert editor['slideCount'] == 18 and editor['missingTexts'] == [] and editor['jsonFullStateEqual']
    assert editor['pptxEditorReimport'] and editor['exportRetrySucceeded']
    assert len(editor['replacementResults']) == 33 and all(r['decorationProtected'] for r in editor['replacementResults'])
    assert len(editor['viewports']) == 4 and all(v['withinViewport'] for v in editor['viewports'])
    fit = evidence['fit-summary.json']
    assert len(fit['selectors']) == 4 and all(not p['problems'] for p in fit['stressPages'])
    assert evidence['persistence-summary.json']['sourceSha256'] == digest(QA / 'editor-verified/edited.json')
    assert evidence['online-save-summary.json']['newBrowserContextReloadEqual']
    assert evidence['image-failure-summary.json']['retrySucceeded']
    assert evidence['real-handler-summary.json']['slideCount'] == 18
    assert evidence['real-handler-summary.json']['realTextModelCalls'] is False
    pptx = QA / '青绿几何清新商务-18版式样例.pptx'
    assert digest(pptx) == digest(QA / 'editor-verified/teal-18-layouts.pptx')
    for name in ('native-render-summary.json', 'native-text-comparison.json'):
        assert evidence[name]['sourceSha256'] == digest(pptx)
    assert all(not p['missing'] for p in evidence['native-text-comparison.json']['slides'])
    suites = ET.parse(QA / 'unit-tests.xml').getroot().findall('testsuite')
    tests = sum(int(s.get('tests', 0)) for s in suites)
    assert tests == 39 and all(int(s.get('failures', 0)) + int(s.get('errors', 0)) == 0 for s in suites)
    # 记录核心实现及输入的文件摘要，后续人工确认可直接核对同一交付版本。
    paths = ['backend/main_api/main.py', 'backend/main_api/workers/template_renderer.py',
             'frontend/src/hooks/useExport.ts', 'frontend/src/hooks/useImport.ts',
             'frontend/src/hooks/templateImageProtocol.ts', 'utils/build_teal_geometric_business_template.mjs',
             'backend/main_api/tests/test_template_28.py', 'backend/main_api/template/template_28.json',
             'backend/main_api/template/template_28.jpg',
             'doc/assets/template_28_qa/production-document.json',
             'doc/assets/template_28_qa/青绿几何清新商务-18版式样例.pptx']
    paths += ['backend/main_api/template/' + filename for filename in assets]
    fingerprints = {name: digest(ROOT / name) for name in paths}
    candidate = 'template_28-' + hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()[:12]
    manifest = {
        'status': 'AWAITING_HUMAN_CONFIRMATION', 'statusText': '自动检查通过，待人工确认',
        'candidate': candidate, 'templateId': 'template_28', 'humanConfirmation': None,
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
        'baseCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'layoutCount': 18, 'assetCount': 5, 'backendTests': tests,
        'editorSlides': 18, 'imageReplacementChecks': 33, 'stressPages': len(fit['stressPages']),
        'responsiveViewports': [[v['width'], v['height']] for v in editor['viewports']],
        'productionFiles': fingerprints, 'evidence': {name: digest(QA / name) for name in names},
        'previewUrl': 'http://127.0.0.1:5780/__template28', 'selectorUrl': 'http://127.0.0.1:5780/app',
        'onlineSavedExampleUrl': evidence['online-save-summary.json']['url'],
        'productionWrites': False, 'gitDeliveryPerformed': False,
    }
    manifest = persist_manifest(QA / 'candidate-manifest.json', manifest)
    print(json.dumps({k: manifest[k] for k in ('status', 'candidate', 'layoutCount', 'assetCount', 'backendTests', 'stressPages')}))


if __name__ == '__main__':
    main()

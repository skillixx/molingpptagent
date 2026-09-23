"""核对当前候选与证据的文件指纹，生成供 P6 人工确认的交付清单。"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_27_qa'
TEMPLATES = ROOT / 'backend/main_api/template'


def read(name):
    return json.loads((QA / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result(name):
    root = ElementTree.parse(QA / name).getroot()
    suites = [root] if root.tag == 'testsuite' else list(root.findall('testsuite'))
    result = {key: sum(int(s.get(key, '0')) for s in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
    if result['tests'] == 0 or result['failures'] or result['errors']:
        raise RuntimeError(f'测试证据未通过：{name}')
    return result


def main():
    template = json.loads((TEMPLATES / 'template_27.json').read_text(encoding='utf-8'))
    spec = (ROOT / 'doc/唯美清新PPT模板开发说明.md').read_text(encoding='utf-8-sig')
    expected_ids = [m[0] for m in re.findall(r'^\| \d+ \| `([^`]+)` \| `(cover|contents|transition|content|end)`', spec, re.M)]
    if len(expected_ids) != 21 or [s['id'] for s in template['slides']] != expected_ids:
        raise RuntimeError('正式模板库存与当前规格不一致')
    assets = read('asset-inspection.json')['assets']
    if len(assets) != 6 or {x['file'] for x in assets} != set(template['metadata']['assetFiles']):
        raise RuntimeError('正式素材库存不一致')
    for asset in assets:
        if digest(TEMPLATES / asset['file']) != asset['sha256']:
            raise RuntimeError('正式素材在检查后发生变化')
    names = ['real-handler-summary.json', 'persistence-summary.json', 'editor-verified/summary.json',
             'runtime/runtime-summary.json', 'fit-summary.json', 'connector-summary.json', 'image-failure-summary.json', 'type-check-summary.json']
    summaries = {name: read(name) for name in names}
    if any(item.get('status') != 'PASS' for item in summaries.values()):
        raise RuntimeError('仍有未通过的功能验证')
    browser = summaries['editor-verified/summary.json']
    persistence = summaries['persistence-summary.json']
    if browser['sourceSha256'] != digest(QA / 'production-document.json'):
        raise RuntimeError('浏览器验证不属于当前样例')
    if persistence['sourceSha256'] != digest(QA / 'editor-verified/edited.json'):
        raise RuntimeError('持久化验证不属于当前编辑稿')
    if not all(browser['uiEdits'].values()) or len(browser['nativeGeometry']) != 82:
        raise RuntimeError('编辑或原生结构验证不完整')
    if summaries['type-check-summary.json']['sourceSha256'] != digest(ROOT / 'frontend/src/hooks/useExport.ts'):
        raise RuntimeError('类型检查不属于当前导出器候选')
    pptx = QA / '唯美清新-21版式样例.pptx'
    native = read('native-render-summary.json')
    if native['sourceSha256'] != digest(pptx) or digest(pptx) != digest(QA / 'editor-verified/weimei-21-layouts.pptx'):
        raise RuntimeError('原生演示软件渲染不属于当前交付稿')
    expected = read('production-document.json')['slides']
    normal = lambda text: re.sub(r'\s+', '', unescape(re.sub('<[^>]*>', '', text)))
    missing = []
    for i, (slide, actual) in enumerate(zip(expected, native['pages'], strict=True), 1):
        texts = '|'.join(normal(t) for t in actual['editableTexts'])
        for element in slide['elements']:
            text = normal(element.get('content', ''))
            if text and text not in texts:
                missing.append({'page': i, 'text': text})
    if missing:
        raise RuntimeError(f'原生演示软件内容比对失败：{missing}')
    text_comparison = {'status': 'PASS', 'renderer': native['renderer'], 'slides': len(expected), 'nativeEditableTextCount': sum(len(x['editableTexts']) for x in native['pages']), 'missingTexts': [], 'sourceSha256': digest(pptx)}
    (QA / 'native-text-comparison.json').write_text(json.dumps(text_comparison, ensure_ascii=False, indent=2), encoding='utf-8')

    # 缩略图只拼接真实渲染结果，便于用户一次查看完整库存。
    for part in range(2):
        sheet = Image.new('RGB', (1500, 1200), '#dfe4ef')
        draw = ImageDraw.Draw(sheet)
        for j, number in enumerate(range(part * 12 + 1, min((part + 1) * 12, 21) + 1)):
            image = Image.open(QA / 'native-renders' / f'slide-{number:02d}.png')
            image.thumbnail((488, 275))
            x, y = j % 3 * 500 + 6, j // 3 * 300 + 24
            sheet.paste(image, (x, y))
            draw.text((x, y - 18), f'Slide {number:02d}', fill='black')
        sheet.save(QA / f'native-contact-{part + 1}.jpg', quality=92)

    source_paths = ['backend/main_api/main.py', 'frontend/src/hooks/useExport.ts', 'utils/build_weimei_fresh_template.mjs',
                    'backend/main_api/template/template_27.json', 'backend/main_api/template/template_27.jpg']
    source_paths += [f'backend/main_api/template/{x["file"]}' for x in assets]
    source_paths += ['doc/assets/template_27_qa/production-document.json', 'doc/assets/template_27_qa/唯美清新-21版式样例.pptx']
    source_paths += ['backend/main_api/tests/test_template_27.py', 'frontend/src/hooks/__tests__/useExportLines.spec.ts',
                     'frontend/src/hooks/__tests__/useExportFailure.spec.ts']
    source_paths += [f'utils/{name}' for name in ['process_weimei_template_assets.py', 'build_template_27_qa_document.py',
        'run_template_27_handler_qa.py', 'verify_template_27_browser.cjs', 'verify_template_27_runtime.cjs',
        'verify_template_27_fit.cjs', 'verify_template_27_persistence.py', 'verify_template_27_connectors.cjs',
        'verify_template_27_image_failure.cjs', 'serve_template_27_preview.py', 'serve_template_27_frontend.mjs', 'finalize_template_27_qa.py']]
    hashes = {name: digest(ROOT / name) for name in source_paths}
    candidate = 'template_27-' + hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]
    result = {'status': 'AUTOMATED_CHECKS_PASSED_AWAITING_USER', 'candidate': candidate, 'humanConfirmation': None,
              'createdAt': datetime.now(timezone.utc).isoformat(), 'templateId': 'template_27', 'layoutCount': 21, 'assetCount': 6,
              'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
              'baseCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'productionFiles': hashes, 'backendTests': test_result('unit-tests.xml'), 'frontendTests': test_result('frontend-export-tests.xml'),
              'evidence': {name: {'status': item['status'], 'sha256': digest(QA / name)} for name, item in summaries.items()},
              'nativePresentationRender': text_comparison, 'preview': 'http://127.0.0.1:5779/__template27',
              'selector': 'http://127.0.0.1:5779/app', 'runtimeMode': 'isolated-read-only-api-fixed-data-preview',
              'gitDelivery': False, 'productionDeployment': False}
    (QA / 'candidate-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'candidate': candidate, 'backendTests': result['backendTests'], 'frontendTests': result['frontendTests']}, ensure_ascii=False))


if __name__ == '__main__':
    main()

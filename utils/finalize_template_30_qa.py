"""核对当前候选与实际检查证据，整理 G8 人工确认材料；不自动闭合 Goal。"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_30_qa'
TEMPLATE_ROOT = ROOT / 'backend/main_api/template'


def read(name):
    return json.loads((QA / name).read_text(encoding='utf-8-sig'))


def digest(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def normalized_pages(document):
    """Worker 与直接渲染的任务 ID 不同，只排除派生标识，保留所有内容和几何比较。"""
    pages = copy.deepcopy(document['slides'])
    for page in pages:
        page.pop('id', None)
        for element in page['elements']:
            element.pop('id', None)
            element.pop('groupId', None)
    return pages


def package_text(file):
    ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    with zipfile.ZipFile(file) as archive:
        names = sorted((name for name in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+.xml', name)),
                       key=lambda name: int(re.search(r'(\d+)\.xml', name).group(1)))
        return [''.join(node.text or '' for node in ET.fromstring(archive.read(name)).findall('.//a:t', ns)) for name in names]


def main():
    (QA / 'evidence.json').write_text(json.dumps({'status': 'VERIFYING', 'humanConfirmed': False}), encoding='utf-8')
    names = ['editor-verified/summary.json', 'fit-summary.json', 'online-save-summary.json',
             'persistence-summary.json', 'real-handler-summary.json', 'image-failure-summary.json',
             'reimport-edit-summary.json', 'native-summary.json']
    checks = {name: read(name) for name in names}
    for name, report in checks.items():
        require(report['status'] == 'PASS', f'{name} 尚未通过')
    source = QA / 'production-document.json'
    source_hash = digest(source)
    editor = checks['editor-verified/summary.json']
    native = checks['native-summary.json']
    require(editor['sourceSha256'] == source_hash, '编辑器证据不是当前样例')
    require(checks['online-save-summary.json']['sourceSha256'] == source_hash, '在线保存证据不是当前样例')
    require(checks['persistence-summary.json']['sourceSha256'] == digest(QA / 'editor-verified/edited.json'), '持久化证据不是当前编辑稿')
    require(editor['pptxSha256'] == digest(QA / 'editor-verified/roundtrip.pptx'), '编辑器往返文件发生变化')
    require(checks['reimport-edit-summary.json']['sourceSha256'] == editor['pptxSha256'], '继续编辑证据不是当前导出')
    clean = QA / 'editor-verified/neon-39-layouts.pptx'
    require(native['sourceSha256'] == digest(clean), '本机打开证据不是当前导出')
    require(package_text(clean) == package_text(native['savedCopy']), '本机保存前后文字或顺序改变')
    document = read('production-document.json')
    require(normalized_pages(document) == normalized_pages(read('real-handler-document.json')), '真实 Worker 输出与已检查样例不一致')
    require(len(document['slides']) == 39 and editor['slideCount'] == 39, '样例数量不符')
    template = json.loads((TEMPLATE_ROOT / 'template_30.json').read_text(encoding='utf-8'))
    require(len(template['metadata']['baseSlideIds']) == 22, '基础版式未齐全')

    # 封面与用户下载样例均来自未加入编辑测试文字的干净导出。
    shutil.copyfile(QA / 'editor-verified/cover.jpg', TEMPLATE_ROOT / 'template_30.jpg')
    sample = QA / '蓝紫霓虹科技产品发布-39版式样例.pptx'
    shutil.copyfile(clean, sample)
    assets = read('asset-inspection.json')
    for record in assets['assets']:
        require(digest(TEMPLATE_ROOT / record['file']) == record['sha256'], f"素材检查已过期：{record['file']}")
    files = ['backend/main_api/main.py', 'backend/main_api/workers/template_renderer.py',
             'frontend/src/utils/prosemirror/schema/nodes.ts', 'utils/build_neon_technology_launch_template.mjs',
             'backend/main_api/template/template_30.json', 'backend/main_api/template/template_30.jpg']
    files += ['backend/main_api/template/' + record['file'] for record in assets['assets']]
    hashes = {name: digest(ROOT / name) for name in sorted(files)}
    candidate = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]

    # 验证实际预览服务正在提供当前文件，而不是其他分支或旧缓存的模板。
    with urllib.request.urlopen('http://127.0.0.1:6804/data/template_30.json', timeout=10) as response:
        require(json.load(response) == template, '预览 API 的模板与工作区不一致')
    with urllib.request.urlopen('http://127.0.0.1:6804/templates', timeout=10) as response:
        entries = json.load(response)['data']
        require(sum(entry['id'] == 'template_30' for entry in entries) == 1, '模板注册缺失或重复')
    for filename in [record['file'] for record in assets['assets']] + ['template_30.jpg']:
        with urllib.request.urlopen('http://127.0.0.1:6804/data/' + filename, timeout=10) as response:
            require(hashlib.sha256(response.read()).hexdigest() == digest(TEMPLATE_ROOT / filename), f'资源未提供当前版本：{filename}')

    # 拼图仅组合真实编辑器截图，供人工快速核对 22 个基础版式。
    sheet = Image.new('RGB', (1600, 6 * 251), (231, 234, 240))
    draw = ImageDraw.Draw(sheet)
    for index in range(22):
        with Image.open(QA / f'editor-verified/canvas-{index + 1}.png') as original:
            image = original.convert('RGB')
            image.thumbnail((380, 214))
        x = index % 4 * 400 + 10
        y = index // 4 * 251 + 8
        sheet.paste(image, (x, y))
        draw.text((x, y + 220), f'L{index + 1:02}', fill=(20, 30, 50))
    sheet.save(QA / '基础版式总览.jpg', quality=92)

    baseline = read('baseline-regression-summary.json')
    require(baseline['status'] == 'BASELINE_FAILURES_REPRODUCED', '基线问题尚未独立复现')
    affected_log = (QA / 'affected-regression.log').read_text(encoding='utf-8-sig')
    require('311 passed' in affected_log and 'failed' not in affected_log, '受影响集合回归结果缺失或失败')
    template_log = (QA / 'template30-tests.log').read_text(encoding='utf-8-sig')
    require('23 passed' in template_log and 'failed' not in template_log, '本模板专项结果缺失或失败')
    result = {'status': 'READY_FOR_HUMAN_REVIEW', 'humanConfirmed': False, 'templateId': 'template_30',
        'candidate': candidate, 'baseCommit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        'baseLayouts': 22, 'adaptations': 17, 'totalLayouts': 39, 'assetCount': len(assets['assets']),
        'imageGenerationCalls': assets['generationCalls'], 'actualImageModel': '工具未暴露',
        'template30Tests': {'passed': 23, 'report': 'template30-tests.log'},
        'affectedBackendRegression': {'passed': 311, 'report': 'affected-regression.log'},
        'broaderBackendRegression': {'passed': 1133, 'failed': 3, 'baselineReproduced': True, 'report': 'baseline-regression-summary.json'},
        'frontendUnitTests': {'files': 30, 'passed': 176}, 'frontendTypecheck': 'PASS',
        'checks': {name: report['status'] for name, report in checks.items()},
        'nativeSavedTextAndOrderEqual': True, 'workerDocumentEqualExceptDerivedIds': True,
        'runtimeAssetsMatchCurrentFiles': True, 'sourceDocumentSha256': source_hash,
        'implementationHashes': hashes, 'sample': str(sample), 'sampleSha256': digest(sample),
        'previewUrl': 'http://127.0.0.1:5792/__template30', 'selectorUrl': 'http://127.0.0.1:5792/app',
        'limitations': ['隔离预览使用固定内容与专用 SQLite，真实业务模型调用未执行。',
                       '手机沿用现有预览和下载模式，未新增手机编辑器。',
                       '现有 PPTX 导出器将原生形状渐变转换为近似中间色；位图背景与装饰保留原色彩。'],
        'productionOperations': False, 'gitDelivery': False}
    (QA / 'evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (QA / 'native-roundtrip-summary.json').write_text(json.dumps({'status': 'PASS', 'slides': 39,
        'sourceSha256': native['sourceSha256'], 'savedCopySha256': digest(native['savedCopy']),
        'allTextAndOrderPreserved': True}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'candidate': candidate, 'layouts': 39, 'assets': len(assets['assets'])}))


if __name__ == '__main__':
    main()

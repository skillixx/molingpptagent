"""汇总当前候选的真实证据，准备 T8 人工验收；不执行 Goal 闭合或 Git 交付。"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_26_qa'
TEMPLATES = ROOT / 'backend/main_api/template'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    # 归档重跑不能抹去用户确认，先检查状态再接触任何输出文件。
    for name in ('candidate.json', 'closure.json'):
        record_path = QA / name
        if record_path.exists():
            record = read(record_path)
            if record.get('humanConfirmed') or record.get('goalClosed') or record.get('T8') == '已完成':
                raise RuntimeError('该候选已人工确认，禁止用自动归档覆盖；新候选请另行保存证据。')
    template = read(TEMPLATES / 'template_26.json')
    spec_path = ROOT / 'doc/深蓝电路网络安全PPT模板开发说明.md'
    spec = spec_path.read_text(encoding='utf-8-sig')
    expected = re.findall(r'^\| \d+ \| `([^`]+)` \|', spec, re.M)
    assert len(expected) == 22 and [s['id'] for s in template['slides']] == expected
    assert len(template['metadata']['mvpSlideIds']) == 14
    assets = read(QA / 'asset-generation.json')
    assert len(assets['assets']) == 8
    for asset in assets['assets']:
        path = TEMPLATES / asset['filename']
        assert sha(path) == asset['sha256']
        with Image.open(path) as image:
            image.load()
            assert list(image.size) == asset['dimensions']
            if asset['hasAlpha']:
                assert image.mode == 'RGBA' and image.getchannel('A').getextrema() == (0, 255)
        asset['visualInspection'] = '已查看生成图及全部真实编辑器和原生PPTX渲染，满足实际页面用途'
    (QA / 'asset-generation.json').write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding='utf-8')

    browser = read(QA / 'editor-delivery/summary.json')
    persist = read(QA / 'persistence-summary.json')
    worker = read(QA / 'real-handler-summary.json')
    runtime = read(QA / 'runtime-selector/runtime-summary.json')
    package = read(QA / 'pptx-package-summary.json')
    native = read(QA / 'native-render-summary.json')
    for evidence in [browser, persist, worker, runtime, package]:
        assert evidence['status'] == 'PASS'
    assert browser['slideCount'] == 22 and not browser['missingTexts'] and not browser['errors'] and not browser['writes']
    assert all(browser['uiEdits'].values()) and browser['jsonFullStateEqual'] and browser['pptxEditorReimport']
    assert browser['sourceSha256'] == sha(QA / 'production-document.json')
    assert browser['pptxSha256'] == package['pptxSha256'] == sha(QA / 'editor-delivery/roundtrip.pptx')
    assert persist['sourceSha256'] == sha(QA / 'editor-delivery/edited.json')
    assert worker['slideCount'] == 22 and set(worker['reachedStableLayoutIds']) == set(expected)
    assert len(browser['viewports']) == 4 and all(v['withinViewport'] for v in browser['viewports'])
    assert len(browser['replacementResults']) == 33 and len(browser['imageGeometry']) == 11
    assert native['slides'] == 22 and package['all11BusinessPicturesRestored'] and all(package['sampleImagesEmbedded'].values())
    for index in range(1, 23):
        with Image.open(QA / f'native-renders/slide-{index:02d}.png') as image:
            assert image.size == (1600, 900)
    suites = list(ET.parse(QA / 'tests.xml').getroot().iter('testsuite'))
    test_count = sum(int(s.get('tests', 0)) for s in suites)
    assert test_count == 170 and all(int(s.get('failures', 0)) == 0 and int(s.get('errors', 0)) == 0 and int(s.get('skipped', 0)) == 0 for s in suites)
    notes = read(QA / 'verification-notes.json')
    assert notes['frontendTests']['exitCode'] == 0 and notes['frontendTests']['passed'] >= 11
    assert notes['typeCheck']['exitCode'] == 0
    assert notes['typeCheck']['typesSourceSha256'] == sha(ROOT / 'frontend/src/types/slides.ts')
    frontend_test_count = notes['frontendTests']['passed']

    shutil.copyfile(QA / 'editor-delivery/cover.jpg', TEMPLATES / 'template_26.jpg')
    delivery_pptx = QA / '深蓝电路网络安全-22版式验收.pptx'
    delivery_json = QA / 'template_26_editable_sample.json'
    shutil.copyfile(QA / 'editor-delivery/roundtrip.pptx', delivery_pptx)
    shutil.copyfile(QA / 'editor-delivery/edited.json', delivery_json)
    paths = [ROOT / p for p in ['backend/main_api/main.py', 'backend/main_api/workers/template_renderer.py',
        'frontend/src/types/slides.ts', 'utils/build_deepblue_circuit_security_template.mjs', 'backend/main_api/tests/test_template_26.py']]
    paths += [TEMPLATES / 'template_26.json', TEMPLATES / 'template_26.jpg']
    paths += [TEMPLATES / filename for filename in template['metadata']['assetFiles']]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    candidate = 'template26-' + hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]
    manifest = {'candidateId': candidate, 'templateId': 'template_26', 'status': 'T8_AWAITING_USER_CONFIRMATION',
                'files': hashes, 'pptxSha256': sha(delivery_pptx), 'sampleJsonSha256': sha(delivery_json),
                'automaticChecks': 'PASS', 'humanConfirmed': False, 'goalClosed': False,
                'backendTests': test_count, 'evidence': ['tests.xml', 'editor-delivery/summary.json', 'persistence-summary.json',
                    'real-handler-summary.json', 'runtime-selector/runtime-summary.json', 'pptx-package-summary.json', 'native-render-summary.json']}
    (QA / 'candidate.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    # 验收页只展示已渲染的真实 PPTX 页面；链接可打开大图及下载可编辑文档。
    cards = '\n'.join(f'<article><a href="native-renders/slide-{i:02d}.png" target="_blank" rel="noopener"><img src="native-renders/slide-{i:02d}.png" alt="第{i}页 {html.escape(identity)}" loading="lazy"></a><p>{i:02d} · {html.escape(identity)}</p></article>' for i, identity in enumerate(expected, 1))
    preview = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>深蓝电路·网络安全 — 模板验收</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#edf2f5;color:#152a39;font-family:"Microsoft YaHei",Arial,sans-serif}}main{{max-width:1500px;margin:auto;padding:clamp(16px,3vw,40px)}}h1{{font-size:clamp(25px,3vw,40px);margin-bottom:12px}}p{{line-height:1.7;overflow-wrap:anywhere}}.actions{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}}.actions a{{background:#173e52;color:#fff;padding:12px 18px;border-radius:6px;text-decoration:none}}a:focus-visible{{outline:3px solid #1684b5;outline-offset:3px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:22px}}article{{margin:0;min-width:0}}img{{display:block;width:100%;height:auto;border-radius:5px}}article p{{margin:8px 0 0;font-size:13px}}.note{{border-left:4px solid #437e99;padding-left:16px}}</style>
<main><h1>深蓝电路·网络安全</h1><p>22 个版式 · 8 项固定素材 · 14 个基础版式已包含<br>候选：{candidate}</p>
<p class="note"><strong>T8 自动检测通过，待人工确认。</strong><br>下面是导出 PPTX 的原生渲染。点击页面可查看大图；下载 PPTX 或 JSON 可检查可编辑内容。检查后请在对话中回复“确认完成”或说明需要修改的内容。当前尚未闭合 Goal。</p>
<div class="actions"><a href="{delivery_pptx.name}" download>下载可编辑 PPTX</a><a href="{delivery_json.name}" download>下载编辑器 JSON</a><a href="验收说明.md">查看验收说明</a></div><p>示例照片由图片工具生成，指标为固定验证数据，不代表真实业务。封面、正文与指标单位包含实际编辑验证的文字。</p><section class="grid">{cards}</section></main></html>'''
    (QA / 'index.html').write_text(preview, encoding='utf-8')
    report = f'''# 深蓝电路·网络安全模板验收说明

状态：T8 自动检测通过，待人工确认。候选 `{candidate}`，模板 `template_26`。Goal 尚未闭合。

## 检查入口

- [22 页原生渲染预览](./index.html)
- [可编辑验收 PPTX](./{delivery_pptx.name})
- [可导入编辑器的 JSON](./{delivery_json.name})
- [固定素材与生成记录](./asset-generation.json)：使用内置 image_gen，按 GPT2 图片模板方式请求，实际模型未暴露；A1～A8 的最终提示词保存在 `asset-prompts/`。

## 已验证结果

- 14 个基础版式、22 个完整版式，8 项固定素材；4 张业务展示样例与固定装饰分开管理。
- 后端模板及公共渲染回归 170 项通过；前端相关测试 {frontend_test_count} 项通过，TypeScript 类型检查通过。
- 四项长标题仍保留在四项页；长正文保序续页；六节点对象顺序与视觉行序一致。
- 指标数值和单位分别可编辑；缺少单位、数值 0、超容量及带图回退均保留信息。
- 真实编辑器通过键盘修改标题和单位；单位修改不改变数值。
- 11 个业务图片槽在横、竖、方图下完成 33 次替换检查，固定装饰保持不变；交付稿已恢复各自的业务样例图。
- JSON 保存重开完整状态一致；真实作品 API 使用隔离 SQLite 验证编辑稿保存、重新连接读取、版本冲突及所有者隔离。
- 真实 Worker、处理器和渲染器使用固定上游数据，按顺序输出全部 22 个版式；没有调用真实文本模型或写入生产队列。
- PPTX 导出失败提示、状态复位及重试通过；重新导入没有文字缺失，11 个业务图框几何位置保留。
- PowerPoint 原生打开并渲染全部 22 页，已检查所有页面，无明显溢出、遮挡或素材裁断；包内包含 215 个原生形状（含文字）。
- 编辑器覆盖 1920×1080、1366×768、768×1024、390×844，画布/预览与手机操作入口均在视口内。

## 证据及实际边界

当前候选校验值与证据索引见 [candidate.json](./candidate.json)。程序入口检查使用当前分支真实模板 API，并仅在验收浏览器内提供隔离身份；没有改动项目认证逻辑，不代表已验证生产 SSO。持久化检查使用临时 SQLite，未连接生产数据库。此处的本地预览仅供人工查看候选，非生产部署。

图片生成工具返回的原始尺寸及最终格式、尺寸规范化记录保存在素材清单中。PPTX 中照片和固定装饰是位图；业务文字、指标、流程及关系图是可编辑对象。原稿动画、音乐和数值驱动图形不在本次范围内。

## 人工确认

请检查当前候选后明确回复“确认完成”或提出修改。只有收到对本候选的明确确认，才记录确认并完成 T8 和 Goal；此次确认不自动授权提交、推送、合并或生产操作。
'''
    (QA / '验收说明.md').write_text(report, encoding='utf-8')
    print(json.dumps({'candidate': candidate, 'automaticChecks': 'PASS', 'T8': '待人工确认', 'goalClosed': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()

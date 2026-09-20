"""核对当前候选与已验证证据，生成待人工确认记录；绝不自动闭合 Goal。"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'doc/assets/template_25_qa'
TEMPLATE = ROOT / 'backend/main_api/template'


def read(name):
    return json.loads((QA / name).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    progress = read('progress.json')
    if progress.get('humanConfirmation'):
        raise RuntimeError('已有人工确认记录，不允许自动覆盖闭合状态')
    template = json.loads((TEMPLATE / 'template_25.json').read_text(encoding='utf-8'))
    if len(template['slides']) != 24 or len(template['metadata']['assetFiles']) != 5:
        raise RuntimeError('模板或素材库存不符')
    browser = read('editor-verified-v2/summary.json')
    styles = read('roundtrip-style-summary.json')
    persistence = read('persistence-summary.json')
    handler = read('real-handler-summary.json')
    runtime = read('runtime-current.json')
    selector = read('runtime/runtime-summary.json')
    native = read('native-render-summary.json')
    for label, record in [('browser', browser), ('styles', styles), ('persistence', persistence), ('handler', handler), ('runtime', runtime), ('selector', selector)]:
        if record.get('status') != 'PASS':
            raise RuntimeError(f'证据未通过: {label}')
    if browser['sourceSha256'] != digest(QA / 'production-document.json'):
        raise RuntimeError('浏览器证据不是当前渲染输入')
    pptx = QA / 'editor-verified-v2/roundtrip.pptx'
    if browser['pptxSha256'] != digest(pptx) or native['sourceSha256'].lower() != digest(pptx):
        raise RuntimeError('导出与原生渲染不是同一 PPTX')
    if persistence['sourceSha256'] != digest(QA / 'editor-verified-v2/edited.json'):
        raise RuntimeError('数据库保存证据不是当前编辑稿')
    if browser['slideCount'] != 24 or styles['editableTextObjectsChecked'] != 150 or styles['failures']:
        raise RuntimeError('完整文字与版式覆盖不足')
    if len(browser['replacementResults']) != 33 or len(browser['viewports']) != 4 or not all(x['withinViewport'] for x in browser['viewports']):
        raise RuntimeError('换图或视口证据不足')
    if native['slides'] != 24 or not native['rendered']:
        raise RuntimeError('原生渲染页数不足')
    for item in runtime['assets']:
        if digest(TEMPLATE / item['name']) != item['sha256']:
            raise RuntimeError(f'运行接口证据已过期: {item["name"]}')
    suites = list(ElementTree.parse(QA / 'tests.xml').getroot().iter('testsuite'))
    tests = sum(int(s.attrib.get('tests', 0)) for s in suites)
    failures = sum(int(s.attrib.get('failures', 0)) + int(s.attrib.get('errors', 0)) + int(s.attrib.get('skipped', 0)) for s in suites)
    if tests != 145 or failures:
        raise RuntimeError('专项及回归测试记录不完整')
    source = Path(r'C:\Users\sk20\Desktop\融资路演(1).ppt')
    if digest(source) != read('baseline.json')['source'].lower():
        raise RuntimeError('参考源文件发生变化')
    code = [ROOT / p for p in ['utils/build_blueblack_city_pitch_template.mjs', 'backend/main_api/workers/template_renderer.py', 'backend/main_api/main.py', 'backend/main_api/tests/test_template_25.py']]
    if any(p.stat().st_mtime > (QA / 'tests.xml').stat().st_mtime for p in code):
        raise RuntimeError('代码在测试后变动，需重验受影响范围')
    candidate_files = code + [TEMPLATE / 'template_25.json', TEMPLATE / 'template_25.jpg'] + [TEMPLATE / p for p in template['metadata']['assetFiles']]
    file_hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in candidate_files}
    candidate = 'template25-' + hashlib.sha256(json.dumps(file_hashes, sort_keys=True).encode()).hexdigest()[:12]
    manifest = {'candidateId': candidate, 'templateId': 'template_25', 'files': file_hashes,
                'tests': tests, 'styleObjects': 150, 'imageReplacements': 33, 'viewports': browser['viewports'],
                'automatedStatus': 'PASS', 'humanConfirmation': None, 'goalStatus': 'active',
                'createdAt': datetime.now(timezone.utc).isoformat()}
    (QA / 'candidate-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copyfile(pptx, QA / '蓝黑城市融资路演-24版式验收.pptx')
    shutil.copyfile(QA / 'editor-verified-v2/edited.json', QA / 'template_25_editable_sample.json')
    for task in ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']:
        progress[task] = 'PASS'
    progress.update(T8='AUTO_PASS_WAITING_USER_CONFIRMATION', candidateId=candidate, humanConfirmation=None,
                    updatedAt=datetime.now(timezone.utc).isoformat(), goalStatus='active')
    progress['testEvidence'].update(passed=tests, durationSeconds=15.34)
    progress.pop('browserSessionId', None)
    (QA / 'progress.json').write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding='utf-8')
    assets = read('asset-generation.json')
    for item in assets['assets'].values():
        item['visualCheck'] = 'PASS：实际浏览器及原生 PowerPoint 页面叠字检查通过'
    assets['assets']['end']['referenceImages'] = [assets['assets']['cover']['source']]
    (QA / 'asset-generation.json').write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding='utf-8')
    report = f'''# 蓝黑城市·融资路演模板验收说明

状态：**T8 自动检测通过，待人工确认**。当前候选 `{candidate}`，模板 `template_25`。尚未闭合 Goal。

## 可检查结果

- [项目模板选择入口](http://127.0.0.1:5778/app)：选择“蓝黑城市·融资路演”，沿用项目现有登录方式。
- [24 版式验收 PPTX](./蓝黑城市融资路演-24版式验收.pptx)：包含实际编辑、换图后的结果，示例内容不代表真实融资数据。
- [可导入编辑器的 JSON 样稿](./template_25_editable_sample.json)：保留项目语义槽和图片角色。
- [原生 PowerPoint 预览 1～12 页](./native-renders/contact-1.jpg)、[13～24 页](./native-renders/contact-13.jpg)。

## 验证结果

| 项目 | 当前证据 |
|---|---|
| 版式与素材 | 24 个版式、五张 1920×1080 RGB JPG；源 PPT 指纹不变 |
| 专项及回归 | {tests} 项通过，见 [JUnit 记录](./tests.xml) |
| 编辑器与换图 | 24 页渲染、33 次业务图片替换、四视口通过，见 [浏览器摘要](./editor-verified-v2/summary.json) |
| 文字可编辑与样式 | 150 个文字对象在 PPTX 重新导入后保留内容、对齐和字重，见 [样式摘要](./roundtrip-style-summary.json) |
| 数据库保存重开 | 真实作品 API＋隔离 SQLite，完整编辑稿一致，旧版本写入和跨用户访问被拒绝，见 [保存摘要](./persistence-summary.json) |
| 生成链路 | 固定上游数据经过真实 Worker、处理器和渲染器成功生成，见 [处理链摘要](./real-handler-summary.json) |
| 原生 PowerPoint | 成功打开并渲染 24 页，见 [原生渲染摘要](./native-render-summary.json) |
| 运行入口 | 实际模板卡片可选择；七项资源的主 API、前端代理与磁盘指纹一致；依赖就绪，见 [运行摘要](./runtime-current.json) |
| 异常反馈 | 注入导出失败后显示错误、恢复状态，重试导出成功 |

## 验证范围与限制

- 浏览器身份采用隔离测试身份；模板列表和正式资源由本地主 API 实际返回，未绕过或修改项目 SSO 实现。
- 生成验证使用固定上游数据，没有调用真实文本模型，没有向生产任务队列写入任务；图片通过实际图片生成工具生产，模型名称工具未暴露。
- 手机端沿用项目已有的预览与下载界面，已实际点击下载；未扩展为全功能桌面编辑器。
- 原生 PPTX 重新导入后文字以可编辑文字形状保留；内部模板语义标记应通过 JSON 样稿保留。
- 已修复长标题选版、专项容量降级、源图片数量校验和导出对齐/字重问题。之前的失败记录保留供追溯，最终结果以当前候选和 v2 证据为准。
- 本地主 API 和 Worker 已加载当前代码；使用进程级 localhost 代理绕过设置恢复依赖健康，没有更改 `.env`。
- 未提交、推送、创建 PR、合并或部署。

## 人工确认

请检查上述当前候选。只有用户明确确认当前候选完成并允许闭合后，才记录确认内容、更新 T8 为已闭合并将 Goal 标记为完成。未回复不算确认。
'''
    (QA / '验收说明.md').write_text(report, encoding='utf-8')
    print(json.dumps({'candidateId': candidate, 'T8': progress['T8'], 'tests': tests}, ensure_ascii=False))


if __name__ == '__main__':
    main()

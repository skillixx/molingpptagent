# template_26 验收与交付证据

正式模板包含 22 个版式（含 14 个基础版式）、封面和 8 项固定素材，位于 `backend/main_api/template/`。用户已确认候选 `template26-5db890c046cf`，原确认记录保存在 `candidate.json`、`closure.json` 和 `progress.json`，不因后续提交审查而改写。

## 仓库包含的证据

本目录提交检查摘要、固定输入、4 张业务展示样例、素材提示词、原生渲染总览及必要设备截图。`native-renders/contact-1.jpg`～`contact-3.jpg` 展示全部 22 页。原始生成文件路径仅用于追溯，正式模板直接使用仓库内成品，不依赖这些路径。

当前合并评估以 [交付检查](./ship-verification.json) 和 [合并评估](../../template_26_merge_readiness.md) 为准。合并前修正了旧本地生成入口的独立指标数值/单位处理、标注选项和验收脚本状态保护；已确认的模板 JSON、封面与 8 项固定素材保持不变。

## 复现

从项目根目录运行，需安装项目 Python 依赖、Node.js 和前端依赖：

```text
python -m pytest backend/main_api/tests/test_template_26.py backend/main_api/tests/test_template_26_qa_archive.py backend/main_api/tests/test_template_25.py backend/main_api/tests/test_template_renderer.py -q
node utils/build_deepblue_circuit_security_template.mjs output/template26-rebuilt.json
python utils/build_template_26_qa_document.py
python utils/run_template_26_handler_qa.py
```

前端检查在 `frontend/` 中运行：

```text
npm run type-check
npm run test:unit -- --run src/hooks/__tests__/useAIPPTMetrics.spec.ts src/hooks/__tests__/templateImageProtocol.spec.ts src/hooks/__tests__/useExportArchiveState.spec.ts
```

浏览器验证使用当前源码的 Vite、Chrome、Playwright 和 sharp，可通过 `PLAYWRIGHT_PACKAGE_PATH`、`SHARP_PACKAGE_PATH` 指定已安装依赖。验证器仅在浏览器中隔离身份并拦截写请求，不应为了验证而在对外 6800/5778 端口启动关闭 SSO 的测试服务。正常运行服务沿用项目配置。

```text
node utils/verify_template_26_browser.cjs doc/assets/template_26_qa/production-document.json output/template26-browser
python utils/verify_template_26_persistence.py output/template26-browser/edited.json
```

固定输入 Worker 和作品保存验证使用隔离临时 SQLite，不写入生产数据库，不调用真实文本模型。`sample-images/S1.jpg`～`S4.jpg` 是 AI 生成的虚构展示图，不代表真实业务事实。

`finalize_template_26_qa.py` 是原验收机的归档工具，依赖完整本地证据；人工确认后拒绝覆盖状态，不是新克隆或 CI 的检查入口。`process_deepblue_circuit_security_assets.mjs` 只用于原始生成文件的机械格式规范化，新克隆直接使用已提交成品。

## 本地保留的产物

源 PPT、原始生成文件、PPTX 导出、逐页截图、巨型往返 JSON、早期失败记录、运行进程和日志保留在原验收机，不随本次 Git 提交上传，也不删除。开发说明和原验收说明中的这些本地文件链接属于验收入口，不表示远程仓库包含相应大文件；需要时可使用上述脚本重建。

代码变更、素材变更或验收环境变化时，应重验实际影响。原有证据不能单凭旧候选哈希代替新路径验证；特别是公共导入、导出、图片裁切逻辑发生变化时，应重新检查往返。

# template_25 验收与交付证据

本目录提交可审查的文本摘要、固定输入、两张原生渲染总览和必要设备截图。正式的 24 版式模板、封面及五张背景位于 `backend/main_api/template/`。

## 复现检查

从仓库根目录运行，环境需要项目 Python 依赖和 Node.js：

```text
python -m pytest backend/main_api/tests/test_template_25.py backend/main_api/tests/test_template_renderer.py backend/main_api/tests/test_template_assets.py backend/main_api/tests/test_template_21.py backend/main_api/tests/test_template_22.py backend/main_api/tests/test_template_23.py backend/main_api/tests/test_template_24.py -q -k "not test_template_23_reference_registration_and_cover_are_available"
node utils/build_blueblack_city_pitch_template.mjs output/template25-rebuilt.json
python utils/build_template_25_qa_document.py
```

被排除的单项是远程 main 已有的旧模板测试，依赖开发者桌面的“星空风格(1).pptx”；当前机器缺少该文件。该测试未被修改，排除不代表其已通过。有对应真实附件时可取消排除运行。

浏览器检查使用 `utils/verify_template_25_browser.cjs`，需要当前源码的 Vite、Chrome、Playwright 和 sharp，可通过 `PLAYWRIGHT_PACKAGE_PATH`、`SHARP_PACKAGE_PATH` 指定已安装包路径。它使用隔离身份与真实编辑器函数，验证换图、JSON 保存重开、PPTX 导出导入、手机下载及导出失败重试。

```text
node utils/verify_template_25_browser.cjs doc/assets/template_25_qa/production-document.json output/template25-browser
python utils/verify_template_25_roundtrip.py output/template25-browser/roundtrip-state.json output/template25-style.json
python utils/verify_template_25_persistence.py output/template25-browser/edited.json
```

持久化验证走真实作品路由与隔离 SQLite，不写入生产数据库。`run_template_25_handler_qa.py` 使用固定上游数据验证真实 Worker/Handler/Renderer，不调用文本模型或执行计费。

## 历史确认与合并审查

`candidate-manifest.json`、`closure.json` 和 `progress.json` 保留用户确认候选 `template25-da624b852daa` 时的记录。Git 交付是之后单独授权的操作；历史确认快照不改写为新代码哈希。

合并前审查补充修复了专项布局图片丢失、专项正文容量不一致和空指标说明导致整组被删除的问题，并补充回归测试。已确认的正式模板 JSON、封面、五张图片以及原 24 页样稿渲染结果没有变化。新的代码检查以 [ship-verification.json](./ship-verification.json)、[ship-tests.xml](./ship-tests.xml) 和[合并评估](../../template_25_merge_readiness.md)为准。

`finalize_template_25_qa.py` 是原验收机的归档工具，依赖原稿与完整本地证据。它在人工确认后拒绝覆盖状态，不是 CI 或新 checkout 的检查入口。

## 本地保留、不随代码提交的产物

原始生成图片、源 PPT、逐页截图、早期失败过程、大体积编辑 JSON、往返状态、导出的 PPTX、运行进程盘点和日志保留在原验收机。摘要中的这些路径是历史证据定位，不代表远程仓库包含对应文件。

`验收说明.md` 用于原 T8 人工检查；其中本地 PPTX/JSON 产物可用以上脚本重建。不会提交其他模板的 QA 产物或 `.codex_tmp/` 临时依赖。

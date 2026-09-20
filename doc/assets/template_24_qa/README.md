# template_24 验收记录

本目录提交可供审查的文本摘要、三页探针、十二页 MVP、固定数据 Worker 输出和生产版总览。正式模板及九项图片位于 `backend/main_api/template/`。

## 可以在新 checkout 中运行的检查

在项目 Python 虚拟环境安装依赖且 Node.js 可用时，从仓库根目录执行：

```text
python -m pytest -q backend/main_api/tests/test_template_24.py backend/main_api/tests/test_template_renderer.py backend/main_api/tests/test_template_assets.py
node utils/build_neon_city_project_template.mjs --stage production output/template24-rebuilt.json
```

浏览器验收使用 `utils/verify_template_24_browser.cjs`。需要当前源码的 Vite 服务、Chrome、Playwright 和 sharp；可通过 `PLAYWRIGHT_PACKAGE_PATH` 与 `SHARP_PACKAGE_PATH` 指定现有包路径。脚本会模拟登录身份并阻止外部 API 写请求，使用真实编辑器换图函数及 JSON/PPTX 导入导出函数。

## 本地保留的产物

生成工具原始图片、逐页截图、编辑后的大体积 JSON、PPTX 导出物和早期失败过程记录只在原验收机保留，不随本次提交发布。摘要中的这些文件路径用于定位原始证据，不代表远程仓库包含对应文件。素材记录中的原始路径是历史来源记录。

`utils/finalize_template_24_qa.py` 是原验收环境的 G8 归档工具，要求桌面参考 PPT、原图、完整本地 QA 文件和本地接口全部可用。它不是 CI 检查入口；G9 闭合后会拒绝再次运行，防止覆盖人工确认记录。

`frozen-candidate-manifest.json` 和 `g8-summary.json` 保留原 G8 验收快照，`g9-closure.json` 记录人工确认。交付审查对构建器参数解析、换图验收调用和闭合记录保护所作的修正及新测试结果，以 [ship-verification.json](./ship-verification.json) 和 [合并评估](../../template_24_merge_readiness.md) 为准。页面、正式模板 JSON 和九项素材未因这些工具修正改变。

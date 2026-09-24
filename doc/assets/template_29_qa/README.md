# 乐章雅韵·音乐主题：交付与复现说明

模板编号为 `template_29`，包含 18 个可复用版式和 5 张正式装饰图。用户已于 2026-09-24 回复“确认完成”，T1～T6 已闭合；原验收版本为 `template_29-aa7f0cfaeed2`，见 [人工确认及候选记录](candidate-manifest.json)。

## 查看与使用

- [18 版式可编辑 PPTX 样例](乐章雅韵音乐主题-18版式样例.pptx)。
- [原生渲染页面总览](music-contact-sheet.png)。
- 本机预览：<http://127.0.0.1:5781/__template29>；模板选择：<http://127.0.0.1:5781/app>。这些地址只在对应本地服务运行时有效。
- 正式站点模板列表已在用户授权重启主 API 后加载 `template_29`，见 [正式入口验证](runtime/public-final-verification.json)。

默认按标题容量选择普通或长标题封面；可用 `data.variant: music / long-title` 显式选择。单图默认左图，可用 `data.variant: left / right` 指定；多图按每项一图关联，须提供原图尺寸。目录超过六项、正文超过页面容量时有序分页，完整保留标题、正文及项目顺序。

桌面及平板支持项目已有的完整编辑流程，手机沿用预览与下载模式。标题、正文、编号、简单形状和线条保持原生可编辑；装饰与业务图片分别标记，换图不会替换固定装饰。结束页支持标题与补充文字自动填充。

本地验收服务使用专用 SQLite 和固定语义数据，允许保存草稿与编辑，不执行真实模型生成、计费或生产写入。完整生成处理链使用固定上游响应验证真实 Worker、处理器和渲染器，不能把该检查描述为真实模型端到端生成。

## 素材来源与文件范围

正式资源位于 `backend/main_api/template/`：四张 1920×1080 RGB JPEG 背景、一张 1200×1600 RGBA 透明小提琴；来源与摘要见 [asset-inspection.json](asset-inspection.json)。本次复用用户原稿装饰，未调用图片生成。原稿文件未修改。

构建入口为 `utils/build_music_theme_template.mjs`。原稿重提取使用 `utils/prepare_music_source_assets.py` 和 `utils/render_music_source_assets.ps1`；这一步需要 Windows、PowerPoint COM 及用户原稿，默认原稿路径写在准备脚本的 `SOURCE` 中。正常构建 JSON、生成固定样例及使用已提交的正式素材不需要原稿或图片生成工具。

`fixtures/business-1.jpg` 至 `business-4.jpg` 是原稿中的音乐照片，仅供固定样例和测试，不属于五张装饰库存。远程提交保留代码、正式资源、必要样例与检查摘要；本地 SQLite、日志、去字原稿副本和重复截图保留在本机，不混入提交。

## 已有验证

| 范围 | 结果与证据 |
| --- | --- |
| 模板行为 | 39 项通过，见 [unit-tests.xml](unit-tests.xml) |
| 交付确认状态 | 4 项通过，同一候选复核保留人工确认，变更候选不继承旧确认 |
| 前端与类型检查 | 27 项相关测试通过，`npm run type-check` 通过；见 [development-checks.json](development-checks.json) |
| 生成处理链 | 真实 Worker 与渲染器覆盖全部 18 个版式，见 [real-handler-summary.json](real-handler-summary.json) |
| 编辑、换图及往返 | 标题和正文键盘编辑、33 次换图、装饰保护、JSON 完整重载和 PPTX 往返通过，见 [编辑器结果](editor-verified/summary.json) |
| 保存及重试 | 实际保存按钮、自动保存、失败反馈与重试、新浏览器重开通过，见 [在线保存结果](online-save-summary.json) |
| 持久化 | 隔离 SQLite 保存重开、版本冲突和所有者隔离通过，见 [persistence-summary.json](persistence-summary.json) |
| 布局与设备 | 26 页压力样例及四类屏幕通过，见 [fit-summary.json](fit-summary.json) |
| 图片读取异常 | 失败反馈及恢复后重试通过，见 [image-failure-summary.json](image-failure-summary.json) |
| 原生演示软件 | 18 页打开、渲染及原生文本完整性通过，见 [渲染记录](native-render-summary.json)与[文字核对](native-text-comparison.json) |

原候选记录保留人工验收时的文件摘要。Git 行尾规范化、文档补充及远程交付记录不改写历史确认；提交树的独立验证另行记录，不把本地未跟踪文件作为提交可用性的依据。

功能分支已提交并推送，当前 main 可快进合并；独立检出后端 43 项、前端 27 项及类型检查通过。详见 [远程交付评估](../../乐章雅韵音乐主题PPT模板远程交付评估.md)及 [提交验证记录](ship-verification.json)。本次未创建 PR、未实际合并 main。

## 开发者复现

模板构建只依赖 Node.js 内置模块。后端测试使用项目 Python 环境；图片检查需要 Pillow，重新提取原稿还需要 lxml。浏览器脚本需要 Playwright、Sharp 和 Chrome，可通过 `PLAYWRIGHT_PACKAGE_PATH`、`SHARP_PACKAGE_PATH` 指向已有依赖，或使用独立 QA 依赖目录，不要求修改产品依赖。

```powershell
node utils/build_music_theme_template.mjs
.\.venv\Scripts\python.exe utils/build_template_29_qa_document.py
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_29.py backend/main_api/tests/test_template_29_delivery.py -q
```

浏览器复现前按项目规则确认端口 5781 和 6803 可用，再分别启动 `utils/serve_template_29_frontend.mjs` 与 `utils/serve_template_29_preview.py`。验证脚本为 `verify_template_29_browser.cjs`、`verify_template_29_fit.cjs`、`verify_template_29_online_save.cjs`、`verify_template_29_image_failure.cjs`；入口验证命令为：

```powershell
node utils/verify_template_29_runtime.cjs doc/assets/template_29_qa/runtime
.\.venv\Scripts\python.exe utils/verify_template_29_persistence.py doc/assets/template_29_qa/editor-verified/edited.json
```

固定语义稿经过真实 Worker 的检查使用 `utils/run_template_29_handler_qa.py`。原生渲染使用 `utils/render_template_29_native.ps1`，复核交付记录使用 `utils/finalize_template_29_qa.py`。重新生成证据后，复核器会依据实际文件摘要判断是否仍为原人工确认候选；不会把发生变化的候选自动标成人工已确认。

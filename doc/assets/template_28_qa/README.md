# 青绿几何·清新商务：使用说明与验证结果

**状态：用户已确认，T1～T6 已完成并闭合。** 用户明确答复为“确认完成”，详见[闭合记录](closure-report.md)。

| 项目 | 当前交付 |
| --- | --- |
| 模板编号 | `template_28` |
| 交付版本 | `template_28-b89a16a70e65` |
| 工作分支 | `codex/teal-geometric-template` |
| 开发范围 | 18 个可复用版式、五张正式装饰 |
| Git 与生产 | 未提交、未推送、未创建 PR、未合并、未部署 |

## 如何检查

- [打开完整十八版式样例](http://127.0.0.1:5780/__template28)：载入真实编辑器，可编辑并保存到本地验收作品库。
- [打开正常模板选择入口](http://127.0.0.1:5780/app)：选择“青绿几何·清新商务”，查看封面与选择反馈。
- [查看已验证的在线保存示例](http://127.0.0.1:5780/editor/0be5bc01-0224-59ee-9f58-62ef09059e15)：标题与图片已实际修改并保存，可在全新浏览器页面重载。
- [下载可编辑 PPTX 样例](青绿几何清新商务-18版式样例.pptx)：包含全部 18 个版式，使用普通示例内容；编辑破坏性测试使用独立文件。
- [浏览前九页](native-contact-1.jpg)与[浏览后九页](native-contact-2.jpg)：来自 Microsoft PowerPoint 原生渲染。

以上地址运行于当前工作区 `D:/moling/TrainPPTAgent`。前端端口 5780、验收 API 端口 6802。专用 API 复用当前主 API 的模板和资源读取，作品保存使用 `runtime-preview.sqlite` 隔离数据库；仅允许本地草稿及编辑保存，不启动真实生成任务、不连接生产数据。

## 使用方式

- 默认按输入内容选择普通正文和对应容量；目录超过六项时有序分页，正文按一至四项及实际容量组织。
- 封面通过 `data.variant: geometric / long-title` 显式选择；未指定时按现有标题容量和候选机制选版。
- 单图通过 `data.variant: left / right` 指定左右布局，未指定时采用左图默认。多图按每项一图关联，提供原始图片宽高。
- 长项目标题通过已有适配机制保留完整原文，不因为标题较长把四项页强行拆成四个单项页。
- 结束页已支持 `data.title` 和 `data.text` 自动填充，仍可在线编辑和导出编辑；本次没有需要强制手动补充的结束页字段。
- 在桌面或平板编辑文字、替换业务图片；点击“保存到我的作品”后进入持久化编辑，后续修改自动保存。手机沿用项目已有的预览和下载模式。
- 正式 PPTX 可通过编辑器导出，也可直接使用上面的样例文件。验收环境不提供生产生成与云端导出归档服务，本地 PPTX 下载已经验证。

## 素材与文件

四张背景和一张透明花纹位于 `backend/main_api/template/`：

| 编号 | 正式文件 | 规格 |
| --- | --- | --- |
| A1 | `template_28_asset_bg_cover_v1.jpg` | 1920×1080 RGB |
| A2 | `template_28_asset_bg_content_v1.jpg` | 1920×1080 RGB |
| A3 | `template_28_asset_bg_section_v1.jpg` | 1920×1080 RGB |
| A4 | `template_28_asset_bg_end_v1.jpg` | 1920×1080 RGB |
| A5 | `template_28_asset_corner_ornament_v1.png` | 1920×1080 RGBA，中心透明 |

制作按用户约定的“GPT2 图片模板”方式，实际调用内置 imagegen，底层模型名称工具未暴露。五张原始输出保存在本目录 `source-images/`，正式资源仅作尺寸和格式处理。[生成提示词与来源](asset-generation.json)、[图片格式与透明检查](asset-inspection.json)可核对。业务测试照片复用已有本地验收素材，未生成额外业务图片，不属于正式装饰。

构建入口：`utils/build_teal_geometric_business_template.mjs`；正式数据：`backend/main_api/template/template_28.json`；封面：`backend/main_api/template/template_28.jpg`。正式页面使用原生文字、形状和线条，没有把整页烘焙成图片。

## 当前验证结果

| 范围 | 结果与证据 |
| --- | --- |
| 后端固定数据专项 | 39 项通过，覆盖版式清单、内容保留、分页、选版、裁切、异常、正式素材和真实模板 API；[测试输出](unit-tests.xml) |
| 真实生成处理链 | 固定上游数据经过真实处理器、渲染器与隔离任务执行器，18 个版式按序产生，无真实文本模型调用；[结果](real-handler-summary.json) |
| 实际编辑与导出 | 18 页渲染，标题与正文键盘编辑、33 次横竖方图替换、装饰保护、JSON 保存重载、PPTX 重新导入通过；[结果](editor-verified/summary.json) |
| 在线保存 | 实际保存按钮、真实自动保存接口、文字与图片变更、独立浏览器上下文服务端重载一致；[结果](online-save-summary.json) |
| 数据持久化 | 隔离 SQLite 完整保存并重载编辑稿，版本冲突及所有者隔离检查通过；[结果](persistence-summary.json) |
| 内容显示与入口适配 | 26 页固定压力样例无文字重叠或越界；模板入口与编辑／预览在1920×1080、1366×768、768×1024、390×844检查通过；[结果](fit-summary.json) |
| 异常与重试 | 图片读取失败和导出写出失败均给出反馈、恢复状态并能重试成功；[图片失败结果](image-failure-summary.json)、[导出结果](editor-verified/summary.json) |
| PowerPoint | 原生打开并渲染18页，110个原生文字对象与导出前内容核对无丢失；[渲染记录](native-render-summary.json)、[文本核对](native-text-comparison.json) |
| 正常模板入口 | 真实模板注册、封面读取、选择反馈和编辑入口通过；[结果](runtime/runtime-summary.json) |

已查看浏览器与 PowerPoint 的全部页面缩略图，以及长标题、手机、平板和重新导入图文页。白字可读、花纹透明且未遮挡正文，图片比例正常。两种渲染环境存在少量字体换行与细线透明度差异，没有发现影响阅读的内容丢失或遮挡；本项目不要求逐像素一致。

## 开发者复现检查

生产模板构建只依赖 Node.js 内置模块。后端检查使用项目 Python 环境；浏览器检查另需 Playwright、Sharp 和 Google Chrome。本次使用的包版本为 Playwright 1.62.1、Sharp 0.35.4。PowerPoint 原生渲染脚本需要 Windows 和已安装的 Microsoft PowerPoint。

可在独立 QA 依赖目录安装浏览器检查依赖，不修改前端产品依赖：

```powershell
npm install --prefix .codex-tmp/template28-qa-deps --no-save playwright@1.62.1 sharp@0.35.4
$env:NODE_PATH = (Resolve-Path .codex-tmp/template28-qa-deps/node_modules).Path
```

也可以通过 `PLAYWRIGHT_PACKAGE_PATH` 和 `SHARP_PACKAGE_PATH` 指向已有包目录。正式资源已包含在仓库中，重建 JSON 和固定样例无需再次调用图片生成：

```powershell
node utils/build_teal_geometric_business_template.mjs
.\.venv\Scripts\python.exe utils/build_template_28_qa_document.py
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_28.py backend/main_api/tests/test_template_28_delivery.py -q
```

浏览器复现时先按项目规则核对端口6802和5780：分别在独立终端运行 `utils/serve_template_28_preview.py`（项目Python）与 `utils/serve_template_28_frontend.mjs`（Node），再运行 `verify_template_28_browser.cjs`、`verify_template_28_fit.cjs`、`verify_template_28_image_failure.cjs` 和 `verify_template_28_online_save.cjs`。入口检查使用 `node utils/verify_template_28_runtime.cjs doc/assets/template_28_qa/runtime`。

持久化检查使用 `utils/verify_template_28_persistence.py doc/assets/template_28_qa/editor-verified/edited.json`；原生渲染使用 `utils/render_template_28_native.ps1`。复核脚本 `utils/finalize_template_28_qa.py` 在候选实现与证据均未变化时保留已有人工确认，变化后的候选才重新进入待确认状态。本地SQLite、日志和可重建截图不作为生产资源提交。

## 人工确认与闭合记录

[交付版本清单](candidate-manifest.json)已记录用户对当前版本的明确确认。闭合前核对核心文件、样例和验证证据未变化，已完成 T6 与总 Goal 闭合。

如果提出范围内修改，将修复并仅重验受影响部分，再提交确认。地图、数据图表、关系图与动画等首版外能力不包含在本次交付中。

运行入口更新（2026-09-23 15:52）：用户明确要求“修复并重启”后，域名实际连接的主 API 6800 已重载，当前 PID 为44312。已为该进程设置本机地址直连，保留外部代理；`https://ppt.axicomin.cn/api/templates` 已返回包含 template_28 的27个模板条目，封面读取200，模板数据18页，`/readyz` 为200且五项依赖均为up。旧预览5779和验收入口5780也包含新模板。数据库、Worker、前端和 `.env` 均未改变；见[实际域名最终验证](runtime/public-final-verification.json)。已打开的页面刷新后加载新列表。

# 唯美清新模板交付与人工确认

当前状态：**用户已确认，P0–P6 已闭合**。模板编号为 `template_27`，名称为“蓝紫光斑·唯美清新”。用户于 2026-09-23 明确回复“确认完成”；当前候选及验证证据未发生变化。

候选标识：`template_27-590cf3bd956a`。代码位于 `codex/weimei-fresh-template`，基线为 `180d26961e05cf6a5d855c37d96653b4ab0963a6`，本次改动尚未提交。确切文件指纹见 [候选清单](candidate-manifest.json)。

## 查看与使用

- 日常入口已于 2026-09-23 重新加载主 API，现在可在 [日常模板选择页](http://127.0.0.1:5778/app) 找到本模板；原页面请刷新。修复记录见 [日常入口验证](live-entry-fix-20260923/README.md)。
- [直接打开 21 页样例编辑器](http://127.0.0.1:5779/__template27)：自动将固定语义样例载入项目真实编辑器，可查看、修改并导出到本地。
- [打开模板选择页](http://127.0.0.1:5779/app)：可找到并选中“蓝紫光斑·唯美清新”。
- [下载可编辑的 21 版式 PPTX 样例](唯美清新-21版式样例.pptx)。该文件在破坏性编辑测试之前独立导出，不含测试替换文字。
- [固定语义生成稿 JSON](production-document.json)：可通过编辑器的 JSON 导入入口打开。
- [第 1–12 页原生渲染缩略图](native-contact-1.jpg)、[第 13–21 页原生渲染缩略图](native-contact-2.jpg)。

本地预览使用隔离身份和只读 API，模板列表、JSON、图片读取复用当前分支的真实接口。预览不连接生产数据库、不执行真实文本生成，也不提供云端保存或归档；这些写操作会收到明确的验收模式提示。编辑器本地编辑和下载可用，完整作品保存与重载已另用真实 API 和隔离 SQLite 验证。

示例业务照片是本次生成的一张协作空间图片及其横、竖、方形裁切，用于演示可替换槽位，不属于 6 张固定装饰。封面补充信息可与副标题一起写入多行 `data.text`，不会自动补造日期或汇报人。

## 实际交付

| 内容 | 位置 |
| --- | --- |
| 21 个正式版式 | `backend/main_api/template/template_27.json` |
| 6 张正式装饰 | `backend/main_api/template/template_27_asset_*` |
| 模板选择封面 | `backend/main_api/template/template_27.jpg` |
| 确定性构建脚本 | `utils/build_weimei_fresh_template.mjs` |
| 图片处理脚本 | `utils/process_weimei_template_assets.py` |
| 模板注册 | `backend/main_api/main.py` |
| 专项固定数据测试 | `backend/main_api/tests/test_template_27.py` |
| 导出器相关修复 | `frontend/src/hooks/useExport.ts` |
| 本地预览启动脚本 | `utils/serve_template_27_preview.py`、`utils/serve_template_27_frontend.mjs` |

所有路径相对于项目根目录。图片通过内置 imagegen 生成，实际模型名称工具未暴露。六张装饰的完整提示词与来源见 [生成记录](asset-generation.json)，实际尺寸、透明通道和文件指纹见 [素材检查](asset-inspection.json)，原图保存在 `source-images/`。

## 验证结果

| 验证内容 | 当前结果与证据 |
| --- | --- |
| 后端模板专项测试 | 40 项通过，0 失败；[JUnit](unit-tests.xml) |
| 受影响前端导出测试 | 27 项通过，0 失败；[JUnit](frontend-export-tests.xml) |
| 前端类型检查 | `npm run type-check` 通过；[结果](type-check-summary.json) |
| 真实处理链与 Worker | 固定上游数据、隔离 SQLite，实际生成全部 21 个版式；[结果](real-handler-summary.json) |
| 浏览器编辑与保存 | 保留标题、正文、图片替换、流程和时间轴标题、指标数值与单位修改，JSON 保存重载全量一致；[结果](editor-verified/summary.json) |
| 作品 API 持久化 | 完整编辑稿数据库重载一致，拒绝过期写入，用户隔离有效；[结果](persistence-summary.json) |
| 图片与异常 | 11 个业务槽位各覆盖横、竖、方形替换；读取失败有可见提示，同一实例可恢复重试；[错误验证](image-failure-summary.json) |
| 设备与长文本 | 四类代表视口、9 页压力样例，未发现文字越界或重叠；[结果](fit-summary.json) |
| PPTX 往返 | 全部文字保留、11 个图片位置保留、82 个原生图形和线条类型及几何匹配；[结果](editor-verified/summary.json) |
| 连接线可编辑性 | 流程、时间轴分别保留 4、5 条原生线，重新导入后实际键盘移动成功；[结果](connector-summary.json) |
| 原生演示软件渲染 | 本机 WPS Office 通过 PowerPoint 兼容 COM 接口打开并渲染全部 21 页，156 个原生文字对象内容比对无缺失；[结果](native-text-comparison.json) |
| 当前分支模板注册与选择 | 真实列表、封面资源、卡片选择与编辑器入口通过；[结果](runtime/runtime-summary.json) |
| 双轴代码审查 | 发现的两项覆盖缺口已补齐，并经独立只读复核；[修复记录](review-resolution.md) |

原生渲染环境已经核实为 WPS Office，不能将其表述为微软 PowerPoint 桌面版验证。PPTX 在项目中的实际导出、重新导入和编辑另有独立浏览器证据。手机和平板检查使用真实浏览器的代表视口，不宣称完成所有实体设备或所有 Office 版本验证。

## 本次修复

1. 调整目录编号框容量，避免两位数字因内边距被误判为溢出。
2. 调整封面圆环位置，改善标题与装饰的分离。
3. 普通直线改为原生 PPTX 线条，修复流程和时间轴重新导入后变成零高度形状、连接线不可见的问题；折线和曲线路径保持原有逻辑。
4. 图片读取与 PPTX 写出统一进行异常处理，读取失败后也能恢复导出状态并重试。

所有功能缺陷均先通过相应失败用例复现，再修复、重验。没有调用真实文本模型、生产任务或生产数据来验证模板。

## 复现入口

在项目根目录执行已交付脚本，可重建模板、验证固定样例。已有有效证据无需为人工确认重复运行。

```powershell
node utils/build_weimei_fresh_template.mjs
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_27.py -q
.\.venv\Scripts\python.exe utils/build_template_27_qa_document.py
.\.venv\Scripts\python.exe utils/run_template_27_handler_qa.py
```

如本地预览进程已退出，先确认 5779 和 6801 未被其他进程占用，再按项目规则以隐藏窗口启动两个预览脚本。API 脚本使用项目 `.venv`，前端脚本使用 Node；实际运行进程记录见 [预览信息](preview-processes.json)。不要停止归属不明的进程。浏览器验收脚本需要可用的 Playwright、Sharp 和 Chrome，本次通过工作区依赖运行；`verify_template_27_browser.cjs` 使用现有 5778 开发前端并隔离 API 请求，其余预览检查使用 5779/6801。

## 人工确认与闭合

用户已明确回复“确认完成”。候选与证据指纹核对一致，本次复用有效验证结果，未重复运行功能测试。

确认记录见 [closure-record.json](closure-record.json)，最终结果见 [闭合报告](closure-report.md)。P0–P6 已闭合；没有执行提交、推送、PR、合并或生产部署。

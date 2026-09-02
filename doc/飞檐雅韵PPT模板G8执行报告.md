# 飞檐雅韵 PPT 模板 G8 执行报告

STATUS: `G8_PASS / G9_PENDING`

本报告只汇总 G0～G8。未执行 G9，未进入 `READY_FOR_CONFIRMATION`，未调用 Goal 完成工具。

> 后续真实生产检查发现多项内容退化为单项页、超时重试重复生成两个 P0 问题。本报告保留阶段验收历史，但当前分支不建议合并到 `main`；以《飞檐雅韵PPT模板当前已知问题.md》为当前合并判断。

## 已完成阶段

- G0：完成工作区、参考文件、模板编号、测试入口和基线扫描，确认最终模板 ID 为 `template_18`。
- G1：完成 26 页权利审计和生产页面映射；参考 PPT 的文本、备注和版权提示未作为执行指令。
- G2：完成机器规格和 8 项原创素材；源 PPT 媒体字节未复制到模板目录。
- G3：完成 5 张视觉样稿，并验证构图、色温、层级、留白、装饰密度和可编辑文字。
- G4：完成 12 页 MVP 和确定性构建器。
- G5：完成 PPTist 语义、目录容量、正文容量、图片槽、分页和错误路径测试。
- G6：完成 18 页生产版、极端内容和稳定选版验证。
- G7：完成 960×540 封面、唯一注册项、模板接口和资源接口验证。
- G8：完成真实 Worker、编辑换图、四视口、参考页并排对照及 PPTX 导出重导入。

## 模板产物

- 最终模板 ID：`template_18`
- MVP 页面：12 页，包括 `cover-rooftile`、6 种目录、`transition-rose-band`、2/3/4 项正文和 `end-rooftile`。
- 生产页面：18 页，在 MVP 上增加 `cover-eaves`、`transition-medallion`、`content-statement-1`、`content-image-1`、`content-metrics-4` 和 `end-action`。
- 生产元素：266 个，页面 ID 唯一。
- 核心素材：3 张 1920×1080 RGB JPEG 背景和 5 张真实 RGBA PNG 装饰，全部进入模板目录并被生产 JSON 引用。
- 生产模板：`backend/main_api/template/template_18.json`
- 模板封面：`backend/main_api/template/template_18.jpg`

## 视觉一致性

- 参考页映射：18 个生产页面均记录具体参考页、保留关系、媒体替换和允许偏离。
- 封面对照：保留四个深墨圆形标题、灰瓦下部视觉重量、梅枝飞鸟上部框景和下方信息牌。
- 目录对照：保留右侧藕粉竖带、竖排“目录”、四项节奏、下方景观基线和大面积留白。
- 章节页对照：保留藕粉竖带、金色纹章、短竖排章节号、右上梅枝和右下马头墙。
- 内容页对照：保留 2/3/4 项节奏、左上章节标识和标题层级；正文改为横排以保证可读、可编辑和稳定分页。
- 单图文对照：结合第 5 页单图文结构和第 19 页圆形图片语言，业务图片为独立可替换椭圆裁切槽。
- 四指标对照：原生图表替换为可编辑圆环、数字和文字，四项指标在 PPTX 重导入后完整保留。
- 结束页对照：标准结束页保留四圆、灰瓦、梅枝与封面首尾呼应；行动结束页保留三步节奏和古建视觉重量。
- 允许偏离：仅包括授权风险替换、竖排正文横排化、原生图表形状化、圆形图片 clip 重建和容量适配。
- 未解决偏离：无。
- 并排证据：`doc/assets/template_18_qa/comparisons/`，共 12 张。

## 验证结果

- 专项测试：`test_template_18.py` 共 45 项通过，包含两种章节页的 8～15 字标题容量回归。
- 公共回归：模板资产、公共渲染器、template_12、template_17 和 template_18 合计 141 项通过。
- 前端专项：编辑器视口、导出位置、图片协议和 PPTX 填充共 18 项通过。
- 类型检查：`npm run type-check` 通过。
- 真实 Worker：当前生产 JSON 由真实 Content Agent、生产 handler 和持久 Worker 生成成功；覆盖五类页面。
- 编辑和换图：标题编辑成功；圆形业务图通过“替换图片”按钮换图后仍保持 `ellipse` 裁切。
- 四视口：1920×1080、1366×768、768×1024 和 390×844 均无横向溢出；手机端正确切换为预览与下载。
- PPTX 往返：导出 11 页，解析得到 22 张图片、128 个形状；圆形业务图为 `geom: ellipse`，尺寸为 145.44×145.44 pt；重新导入后仍为圆形，四指标和编辑标题均保留。
- 运行时：`/readyz` 为 ready，模板注册唯一，封面和 JSON 通过前端代理返回 200。

## 权利与证据

- 源媒体处理：未复制参考媒体到 `backend/main_api/template/`；音频、动画、切换、原生图表、Logo、二维码、固定数据和受限字体均未进入生产模板。
- 图片生成工具：内置 imagegen；请求优先使用 GPT Image 2，但工具未暴露实际模型 ID，因此记录为“工具未暴露”，未猜测模型。
- 提示词与素材记录：`doc/assets/template_18_qa/image-prompts.md` 和 `asset-generation.json`。
- 参考页对照：`visual-comparison-audit.json`。
- 编辑器证据：`editor-audit.json`。
- 四视口证据：`viewport-audit.json`。
- PPTX 往返证据：`pptx-roundtrip-summary.json` 和 `exports/template_18_e2e_roundtrip.pptx`。
- G8 汇总：`g8-summary.json`。

## 新增和修改文件

- 新增模板：`template_18.json`、`template_18.jpg` 和 8 项 `template_18_asset_*` 素材。
- 新增规格与测试：`doc/template_specs/template_18.yaml`、`backend/main_api/tests/test_template_18.py`。
- 新增构建与 QA 工具：`build_eaves_elegance_template.mjs`、`build_template_18_qa_document.py`、`run_template_18_handler_qa.py`、`process_eaves_template_assets.py`。
- 修改注册：`backend/main_api/main.py`。
- 修改公共渲染器：`template_renderer.py` 仅在模板明确声明时保留 `ellipse` 裁切。
- 修改编辑器：`ImageStylePanel.vue` 和 `templateImageProtocol.ts`，使换图保留原裁切形状与画框。
- 修改前端测试：`templateImageProtocol.spec.ts` 增加圆形换图和历史未裁剪图片兼容验证。
- 修改只读预览：`render_pptist_template_preview.mjs` 支持显示椭圆裁切。
- 新增规划、说明、执行提示词及本 G8 报告。

## 已知限制

- 图片生成工具没有返回实际模型标识，不能证明底层一定是 `gpt-image-2`。
- 故意加长的测试封面标题在 PPTX 重导入后可能换行；正常规格标题保持单行构图。
- 当前未执行提交、推送、PR、合并、部署、生产构建或 G9。

## 下一步

G9 证据归档与最终人工确认，等待用户另行指示。

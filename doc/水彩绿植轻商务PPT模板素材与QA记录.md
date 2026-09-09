# 水彩绿植轻商务 PPT 模板素材与 QA 记录

## 1. 当前结论

`template_19` 已完成 G0～G8 开发与自动验收，G9 自动复核通过，并于 2026-09-09 获得用户明确确认，最终状态为 `DONE`。

生产模板必须保持与原图或原 PPT 的视觉风格、构图逻辑、色彩气质、留白节奏和装饰语言一致。当前候选版本已经按这一肯定要求完成封面、目录、章节、正文、图文、指标和结束页核对，同时没有复制参考 PPT 的媒体字节。

用户人工确认门禁已经满足。本次闭合只更新 Goal 状态；提交、推送、PR、合并和部署仍未授权且未执行。

## 2. 候选版本

| 项目 | 结果 |
|---|---|
| 模板 ID | `template_19` |
| 模板名称 | 水彩绿植轻商务 |
| 生产页数 | 18 |
| MVP 页数 | 12 |
| 核心素材 | 9 项 |
| 模板 JSON SHA-256 | `C1D18473F6EB47D9EEECC4D02C29D5B4D53D3E511DC4F57E225A23FB9B485A0E` |
| 选择器封面 SHA-256 | `5779DBC005E3CC48CA639DE23BE2D24AD07AFD35AE369D60A6846A1C01497E0D` |
| 参考 PPT SHA-256 | `E80BFD5543B8C18F79181463E54D8FF6843C8DA13E6BD4D84141BA4E26A0211D` |

## 3. 素材生成与权利

- 背景和透明装饰使用内置图片生成工具制作；工具未暴露实际模型名称，记录为“工具未暴露”。
- 参考 PPT 只用于视觉风格、构图、配色、空间和视觉重量判断，不复制参考媒体字节。
- 4 张背景均为 RGB JPEG；5 张装饰均为具有真实 Alpha 的 RGBA PNG；9 项均被生产模板引用并满足体积上限。
- 植物完整框景连续 3 轮生成均返回 RGB 棋盘格，已停止继续重试，并使用通过透明度验收的桉叶角景镜像变体替代。
- 所有生成轮次、源文件、发布路径和哈希记录在 [`asset-generation.json`](./assets/template_19_qa/asset-generation.json) 与 [`image-prompts.md`](./assets/template_19_qa/image-prompts.md)。

## 4. G0～G8 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| 参考稿审计与页面映射 | PASS | [`reference-rights-audit.json`](./assets/template_19_qa/reference-rights-audit.json)、[`reference-page-map.json`](./assets/template_19_qa/reference-page-map.json) |
| 三页技术探针 | PASS | [`probe-summary.json`](./assets/template_19_qa/probe-summary.json)、`probe-roundtrip-*.json` |
| 12 页 MVP / 18 页生产版 | PASS | `samples/`、[`template_19.json`](../backend/main_api/template/template_19.json) |
| 后端完整测试 | 1007 passed | [`g8-summary.json`](./assets/template_19_qa/g8-summary.json) |
| 前端完整单测 | 26 files / 136 tests passed | [`g8-summary.json`](./assets/template_19_qa/g8-summary.json) |
| TypeScript 类型检查 | PASS | [`g8-summary.json`](./assets/template_19_qa/g8-summary.json) |
| 真实 Worker | PASS，12 页，五种页面类型齐全 | [`real-handler-summary.json`](./assets/template_19_qa/real-handler-summary.json) |
| 四视口 | PASS | [`viewport-audit.json`](./assets/template_19_qa/viewport-audit.json) |
| 编辑、换图、装饰保护 | PASS | [`editor-audit.json`](./assets/template_19_qa/editor-audit.json) |
| PPTX 导出和项目重导入 | PASS，18 页 | [`pptx-roundtrip-summary.json`](./assets/template_19_qa/pptx-roundtrip-summary.json) |
| 18 页逐页全尺寸检查 | PASS | [`editor-audit.json`](./assets/template_19_qa/editor-audit.json) |
| 样式一致性 | PASS | [`visual-comparison-audit.json`](./assets/template_19_qa/visual-comparison-audit.json) |
| 本地运行环境 | PASS | [`runtime-audit.json`](./assets/template_19_qa/runtime-audit.json) |

## 5. 编辑器与 PPTX 回环

- 生产 JSON 已在真实前端导入，共 18 页。
- 封面标题修改为“水彩绿植生产编辑验收”，导出后解析和重新导入均保留。
- 第 12 页业务图片已替换；固定水彩植物装饰未被覆盖；图片裁切在重新导入后仍存在。
- 导出的本地 QA 文件 `doc/assets/template_19_qa/exports/template_19_production_editor_roundtrip.pptx` 已通过项目同款解析和真实编辑器重新导入；该大体积导出不入库，长期证据以 [`pptx-roundtrip-summary.json`](./assets/template_19_qa/pptx-roundtrip-summary.json) 为准。
- 重新导入后的 18 页均在 960 × 540 编辑画布中逐页检查，未发现文字溢出、元素丢失、明显裁切错误或明显样式漂移。

## 6. 已知限制

- 参考 PPT 中的音频、转场、特殊字体、原生图表和嵌入对象按 V1 计划排除。
- 参考 PPT 通用导入兼容、历史模板迁移、全量字体兼容、动画和原生图表支持属于独立任务，不阻塞本模板。
- 图片生成工具未暴露实际底层模型名称，因此不猜测具体模型。
- 植物完整框景素材未达到真实 Alpha 标准，已使用规划允许且通过验收的透明角景变体替代。

## 7. G9 最终状态

G9 自动复核已通过，详见 [`g9-final-audit.json`](./assets/template_19_qa/g9-final-audit.json)。用户已明确回复“确认完成”，当前状态为 `DONE`。

2026-09-04 根据真实失败任务补充修复：无图封面副标题槽高度由 76 调整为 88，带图封面副标题行高固定为 1.3，两种封面均可完整容纳 50 字真实 Agent 摘要；前端首次路由跳转异常会自动使用 `replace` 重试，连续两次失败才显示手动入口。固定 80 项真实长短正文夹具生成 30 页，单项内容页占比为 0。修改后专项与完整回归均通过，Worker 已重启加载新模板。

用户人工确认已于 2026-09-09 收到，最终闭合已经完成。

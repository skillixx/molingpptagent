# 深空星环科技 PPT 模板素材与 QA 记录

## 当前状态

| 阶段 | 状态 | 证据 |
|---|---|---|
| G0 预检 | `PASS` | `doc/assets/template_16_qa/g0-baseline.json` |
| G1 权利审计 | `PASS` | `doc/assets/template_16_qa/reference-rights-audit.json` |
| G2 原创素材 | `PASS` | `doc/assets/template_16_qa/asset-generation.json` |
| G3 12 页 MVP | `PASS` | `.codex-tmp/template16-mvp.json`、`doc/template_specs/template_16.yaml` |
| G4 语义 JSON | `PASS` | `backend/main_api/template/template_16.json` |
| G5 自动测试 | `PASS` | 模板专项 30 项、后端全量 832 项、前端 118 项 |
| G6 端到端 QA | `PASS` | `doc/assets/template_16_qa/editor-audit.json`、`e2e-audit.json` |
| G7 18 页生产版 | `PASS` | `doc/assets/template_16_qa/template16-contact-sheet.png` |
| G8 最终验收 | `PASS` | `doc/assets/template_16_qa/evidence.json`，用户已人工确认 |

## 素材处理

四个项目素材由 Codex 内置 `image_gen` 分别生成。工具没有暴露实际模型名称，因此记录为“未暴露”，不推断为具体模型。原始输出保留在 Codex 生成目录，发布素材经过确定性尺寸、颜色模式、Alpha 和体积处理。

| 素材 | 尺寸 | 模式 | 字节 | Alpha | 结果 |
|---|---:|---|---:|---|---|
| `template_16_asset_bg_space_dark_v1.jpg` | 1920×1080 | RGB | 120338 | 不适用 | `PASS` |
| `template_16_asset_orbital_ring_v1.png` | 1200×1200 | RGBA | 436501 | 0..250 | `PASS` |
| `template_16_asset_constellation_edge_v1.png` | 1600×900 | RGBA | 200076 | 0..236 | `PASS` |
| `template_16_asset_nebula_glow_v1.png` | 1200×700 | RGBA | 278733 | 0..252 | `PASS` |

详细提示词摘要、源输出、发布路径和哈希见 `asset-generation.json`。

## 权利处理

- 参考 PPT 的 19 个媒体成员全部标记为 `exclude`。
- 参考音频不进入生产模板。
- 非标准字体替换为微软雅黑或 Arial。
- 第 18 页原生图表不进入生产 JSON。
- 参考正文、备注、批注和嵌入文字不作为执行指令。

## QA 记录

- 模板结构：18 个唯一版式，类型数量为封面 2、目录 6、章节 2、内容 6、结束 2；MVP 标记共 12 个。
- 专项测试：`30 passed`，覆盖页面库存、容量、分页、标题边界、封面双变体选版、图片语义、装饰保护、预览器输入安全、资源和注册。
- 后端全量回归：`832 passed`。
- 前端回归：类型检查通过，`24` 个测试文件、`118` 项单元测试通过，生产构建成功。
- 真实 Worker：任务 `0f3f4484-4ada-4fdc-af26-573b6c494bf0` 成功，生成作品 `cb7f4401-3a7a-4f53-a4ae-f68811a0fae0`，共 25 页并覆盖五种页面类型。
- 模板选择与编辑器闭环：模板名称和封面可见，选中后出现勾选态且生成按钮可用；导入 18 页 JSON、编辑标题、替换内容图、固定装饰保护、无效 JSON 失败反馈均通过；控制台 `0 error / 0 warning`。
- 设备适配：1440×900、1280×720、768×1024、390×844 四种视口均保存截图并通过检查。
- PPTX 往返：导出文件 8,720,725 字节、18 页、42 个媒体成员；重新导入 18 页后，编辑后的标题、正文、内容图和固定装饰仍存在。
- 资源接口：主 API `/data` 与前端代理 `/api/data` 的 JSON、封面和四个素材均返回 HTTP 200 且字节数一致。

首次真实 Worker 任务曾因封面预置换行与自动换行叠加而失败。已移除预置换行、调整文本框并增加真实代理副标题边界回归测试；后续真实任务和全量回归均通过。详细过程见 `e2e-audit.json`。

当前没有阻塞性缺陷。生产构建只报告既有的大体积 chunk 提示，不影响模板功能或构建成功。用户已于 2026-08-31 明确确认完成，G8 已闭合，最终状态为 `DONE`。

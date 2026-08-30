# 星脉科技产品发布 PPT 模板素材与 QA 计划

## 1. 规划状态

| 项目 | 内容 |
|---|---|
| 模板 ID | `template_15`，候选 |
| 规格路径 | `doc/template_specs/template_15.yaml` |
| 规格状态 | `READY_FOR_BUILD` |
| QA 状态 | `NOT_RUN` |
| 文档性质 | 规划阶段待执行清单，不包含图片生成、测试或运行结果 |

## 2. 素材 manifest

| ID | 角色 | 发布文件名 | 格式/尺寸/模式 | Alpha | 最大字节 | 安全区 | 权利动作 | 最大尝试 |
|---|---|---|---|---|---:|---|---|---:|
| `bg-cover` | 背景 | `template_15_asset_bg_cover_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 380000 | 左侧标题低细节，右侧产品舞台 | `regenerate` | 3 |
| `bg-section` | 背景 | `template_15_asset_bg_section_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 340000 | 中央章节标题低细节 | `regenerate` | 3 |
| `bg-end` | 背景 | `template_15_asset_bg_end_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 340000 | 中央行动收束低细节 | `regenerate` | 3 |
| `spectrum-footer` | 装饰 | `template_15_asset_spectrum_footer_v1.png` | PNG / 1600×520 / RGBA | 是 | 950000 | 上方透明，粒子只从底缘生长 | `regenerate` | 3 |
| `horizon-glow` | 装饰 | `template_15_asset_horizon_glow_v1.png` | PNG / 1600×700 / RGBA | 是 | 850000 | 光弧位于下三分之一 | `regenerate` | 3 |
| `particle-field` | 装饰 | `template_15_asset_particle_field_v1.png` | PNG / 1600×900 / RGBA | 是 | 900000 | 正文安全区至少 85% 透明 | `regenerate` | 3 |
| `product-stage` | 装饰 | `template_15_asset_product_stage_v1.png` | PNG / 1200×700 / RGBA | 是 | 800000 | 中央上方透明供用户产品图叠放 | `regenerate` | 3 |

提示词共同约束：

- 无文字、无 Logo、无水印、无伪代码、无假截图。
- 不出现手机、手表、芯片或其他可识别产品外形。
- 不出现真实人物、可识别企业、学校或机构。
- 只生成原创的蓝紫光谱、粒子、地平线和舞台光效。
- 所有 PNG 必须保留真实透明通道，不得用棋盘格伪装透明。

规划阶段不填写生成工具结果、文件哈希或“已通过”。后续实施应记录工具实际暴露的模型信息；工具未暴露时写“未暴露”，不得猜测。

## 3. 参考权利 QA

| 案例 ID | 检查对象 | 通过标准 | 计划证据 | 状态 |
|---|---|---|---|---|
| `case-reference-rights-audit` | 42 图片、17 WDP、1 WAV、字体、品牌与示例文案 | 未知权利内容没有原样进入模板或发布集合 | `doc/assets/template_15_qa/reference-rights-audit.json` | `NOT_RUN` |

禁止带入：Electronic、Note x、具体型号、产品渲染、城市照片、商务人物、APP/UI 图、参考音频、参考字体文件、包图网相关标识或水印。

机器检查还必须验证规格列出的 60 个 `ppt/media/*` 成员与参考审计的媒体并集完全相等，且统一动作均为 `exclude`；任何新增、遗漏或被标记为 `reuse` 的成员都应失败。

## 4. 自动化测试矩阵

| 案例 ID | 检查对象 | 输入边界 | 预期结果 | 证据类型 | 状态 |
|---|---|---|---|---|---|
| `case-page-inventory` | ID、画布、页面库存、MVP 标记、唯一 ID | 20 个 MVP / 39 个生产版式 | 与 `pages.layout_catalog` 一致、每个 ID 数量为 1、无重复或未声明变体 | pytest 摘要 | `NOT_RUN` |
| `case-template-protocol` | 页面、文字、图片语义槽 | 全部页面类型 | 内容图与固定装饰角色严格分离 | pytest 摘要 | `NOT_RUN` |
| `case-selection-partition` | 选版唯一性与失败契约 | 普通、全 metric、8 类显式专项、有效/无效图片组合 | 每个合法输入恰好命中一个 ID；非法输入返回 `TemplateRenderError`；普通正文与 metrics 不重叠 | pytest 参数化摘要 | `NOT_RUN` |
| `case-contents-capacity` | 目录选版与分页 | 3、4、5、6、7、11 项 | 3–6 精确选版；超量无损分页 | pytest 摘要 | `NOT_RUN` |
| `case-text-capacity` | 普通无图正文 | 1–7 项 | 1–6 精确容量；7 固定 6+1；不误入显式专项版式 | pytest 摘要 | `NOT_RUN` |
| `case-specialty-layouts` | 8 类专项版式 | 规则允许的全部项目数 | 每类可到达且越界输入明确失败 | pytest 参数化摘要 | `NOT_RUN` |
| `case-overflow-pagination` | 目录、普通正文、长正文、带图长正文 | 目录 7/11、正文 7/8/11 与超长文本 | 目录平衡分页；正文 7=6+1；字符和顺序无损；单张关联图只在首段保留 | pytest 摘要 | `NOT_RUN` |
| `case-title-fit-boundaries` | 封面与内容标题 | 封面中文 24/25/36/37、拉丁 48/49/72/73；内容中文 20/21/36/37、拉丁 44/45/80/81；混排等式内/等式上/超限 | NFC 后按 `wide×latin_limit + ascii×cjk_limit` 计量；单行、两行、改选或明确报错；标题与产品图零重叠 | pytest 摘要与代表性渲染 | `NOT_RUN` |
| `case-image-counts` | 内容图选版 | 0–7 张 | 0–6 精确选版；7 张按规则分页或明确报错 | pytest 参数化摘要 | `NOT_RUN` |
| `case-image-item-matrix` | 图片数 × item 数 | 0 图；1 图×1–7 项；2 图×1–7 项；3–6 图等量/不等量；7+ 图等量/不等量 | 每个组合唯一进入 text/hero/dense/dual/gallery/分页或明确错误 | pytest 矩阵摘要 | `NOT_RUN` |
| `case-image-crop-and-errors` | 横图、竖图、方图、缺失尺寸、图片数越界 | 1920×1080、1080×1920、1000×1000、缺失尺寸 | 比例裁切正确；非法输入明确报错 | pytest 摘要和渲染截图 | `NOT_RUN` |
| `case-asset-manifest` | 封面与 7 个外置素材 | 实际发布文件集合 | 名称唯一，格式、尺寸、模式、Alpha、体积均符合规格 | 文件属性 JSON | `NOT_RUN` |
| `case-registration-routes` | 模板列表、JSON、封面、资源路由 | API 读取 | `template_15` 唯一显示且全部资源可读 | API 响应摘要 | `NOT_RUN` |

计划测试命令（本规划阶段不执行）：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_15.py
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_assets.py backend/main_api/tests/test_template_renderer.py
```

## 5. 真实任务与交互 QA

| 案例 ID | 场景 | 操作 | 通过标准 | 计划证据 | 状态 |
|---|---|---|---|---|---|
| `case-worker-generation` | 持久 Worker 真实生成 | 用发布主题输入覆盖 5 类页面与 8 类专项版式 | 任务成功，声明版式均实际出现，无仅靠单元测试到达的死版式 | `doc/assets/template_15_qa/real-generation-summary.json` | `NOT_RUN` |
| `case-edit-persistence` | 文字编辑 | 修改标题、指标和正文，保存后重新加载 | 内容、层级和布局保持正确 | `doc/assets/template_15_qa/edit-persistence.png` | `NOT_RUN` |
| `case-image-replacement` | 内容图替换 | 替换横图、竖图和方图 | 新图裁切正确；光谱、舞台、粒子装饰不变 | `doc/assets/template_15_qa/image-replacement.png` | `NOT_RUN` |
| `case-button-feedback` | 模板选择、生成、保存、换图、导出、失败重试 | 触发正常与失败分支 | 按钮有加载、成功、失败或明确假性交互，失败后恢复且可重试 | `doc/assets/template_15_qa/button-feedback/` | `NOT_RUN` |

## 6. 视口矩阵

| 案例 ID | 设备类别 | 宽 × 高 | 检查点 | 计划截图 | 状态 |
|---|---|---:|---|---|---|
| `viewport-desktop` | 桌面 | 1440 × 900 | 无横向溢出；模板选择、编辑、换图、生成、导出按钮可见并有反馈 | `doc/assets/template_15_qa/viewports/desktop.png` | `NOT_RUN` |
| `viewport-laptop` | 笔记本 | 1280 × 720 | 主画布与侧栏不互相遮挡；关键按钮可触达 | `doc/assets/template_15_qa/viewports/laptop.png` | `NOT_RUN` |
| `viewport-tablet` | 平板 | 768 × 1024 | 侧栏折叠合理；无横向滚动；触控目标清晰 | `doc/assets/template_15_qa/viewports/tablet.png` | `NOT_RUN` |
| `viewport-mobile` | 手机 | 390 × 844 | 单列或明确折叠；核心操作可完成；反馈不被遮挡 | `doc/assets/template_15_qa/viewports/mobile.png` | `NOT_RUN` |

## 7. PPTX 往返

| 案例 ID | 检查 | 通过标准 | 计划证据 | 状态 |
|---|---|---|---|---|
| `export-roundtrip` | 导出、解析、重导入与继续编辑 | 页数与核心结构合理；字体、内容图、装饰分组未异常；重导入后可编辑 | `doc/assets/template_15_qa/export-roundtrip-summary.json` | `NOT_RUN` |

## 8. 完成条件覆盖

| 完成条件 ID | 案例 ID | 预期证据 |
|---|---|---|
| `criterion-reference-rights` | `case-reference-rights-audit` | 权利审计 JSON |
| `criterion-page-inventory` | `case-page-inventory` | pytest 摘要 |
| `criterion-template-protocol` | `case-template-protocol` | pytest 摘要 |
| `criterion-selection-determinism` | `case-selection-partition`、`case-image-item-matrix` | 输入分区唯一性与错误断言 |
| `criterion-capacity-selection` | `case-contents-capacity`、`case-text-capacity` | 参数化测试摘要 |
| `criterion-specialty-layouts` | `case-specialty-layouts` | 可到达性摘要 |
| `criterion-overflow` | `case-overflow-pagination` | 无损分页断言 |
| `criterion-title-fit` | `case-title-fit-boundaries` | 字数边界、版式改选、错误与零重叠断言 |
| `criterion-image-semantics` | `case-image-counts`、`case-image-item-matrix`、`case-image-crop-and-errors`、`case-image-replacement` | 测试摘要与换图截图 |
| `criterion-assets` | `case-asset-manifest` | 文件属性 JSON |
| `criterion-registration` | `case-registration-routes` | API 响应摘要 |
| `criterion-real-generation` | `case-worker-generation` | 真实生成摘要和蒙太奇 |
| `criterion-editing` | `case-edit-persistence`、`case-image-replacement` | 编辑与换图截图 |
| `criterion-responsive` | 4 个视口案例 | 四视口截图 |
| `criterion-button-feedback` | `case-button-feedback`、4 个视口案例 | 正常/失败反馈截图 |
| `criterion-export-roundtrip` | `export-roundtrip` | 往返摘要 |

## 9. 证据目录策略

标准入口：`doc/assets/template_15_qa/evidence.json`

默认计划提交：

- `evidence.json`；
- 生产模板和真实任务蒙太奇；
- 四视口关键截图；
- 编辑、换图、失败重试和重导入关键截图；
- 提示词、来源、授权动作和精简摘要。

默认不提交：

- 图片生成原图；
- 全部逐页原始截图；
- 大型 QA PPTX、临时导出和本次 `.codex-tmp/` 分析中间件；
- 进程日志或包含用户数据的调试文件。

## 10. 待确认与已知限制

开放决策：无。独立规划审计为 `PASS`，规格达到 `READY_FOR_BUILD`；所有 QA 案例仍保持 `NOT_RUN`。

已知限制：

- `template_15` 是候选 ID，实施前必须重新扫描。
- 参考稿权利状态未知，不允许从中复制媒体、字体、品牌或音频。
- 当前运行时无法完整渲染参考 PPTX；后续真实构建必须补齐逐页渲染与视觉复核证据。
- 参考稿动画、音频和 3:1 超宽画布不在生产模板范围内。

该文档在规划阶段不得把任何案例状态改为 `PASS`。实际结果由后续模板开发与 QA 流程及证据文件记录，自动状态最多到 `READY_FOR_CONFIRMATION`。

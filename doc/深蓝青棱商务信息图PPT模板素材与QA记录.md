# 深蓝青棱商务信息图 PPT 模板素材与 QA 计划

## 1. 规划状态

| 项目 | 内容 |
|---|---|
| 模板 ID | `template_14`，候选，不代表已占用 |
| 规格路径 | `doc/template_specs/template_14.yaml` |
| QA 状态 | `NOT_RUN` |
| 文档性质 | 规划阶段待执行清单，不包含测试、生成、运行或通过结果 |

本文所有案例均为未来工作。规划阶段不得把任何状态改为 `PASS`，也不得填写图片生成结果、真实模型标识、任务 ID 或测试通过数。

## 2. 素材 manifest

| ID | 角色 | 发布文件名 | 格式/尺寸/模式 | Alpha | 最大字节 | 安全区 | 权利动作 | 最大尝试 |
|---|---|---|---|---|---:|---|---|---:|
| `cover-background` | 背景 | `template_14_asset_bg_cover_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 350000 | 中左标题区低细节，切面限右上与左下 | `regenerate` | 3 |
| `section-background` | 背景 | `template_14_asset_bg_section_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 320000 | 中央和左中部保留章节号与标题 | `regenerate` | 3 |
| `end-background` | 背景 | `template_14_asset_bg_end_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 320000 | 中央结束语区低细节，装饰集中四角 | `regenerate` | 3 |
| `facet-corner` | 固定装饰 | `template_14_asset_facet_corner_v1.png` | PNG / 1400×900 / RGBA | 是 | 1000000 | 主体只在右上和左下，中央透明 | `regenerate` | 3 |
| `line-particle-overlay` | 固定装饰 | `template_14_asset_line_particle_v1.png` | PNG / 1400×900 / RGBA | 是 | 800000 | 稀疏线点只在边缘，文字区透明 | `regenerate` | 3 |

全局最大生成尝试：15。

提示词共同约束：

- 深蓝、青蓝、平面几何、理性商务、原创构图。
- 无文字、无数字、无 Logo、无水印、无真实人物、无第三方 UI、无假图表、无假二维码。
- 不复刻参考照片、广告牌、城市地标、品牌配色或受保护角色。
- 背景必须为 RGB；透明装饰必须为 RGBA 且具真实 Alpha 通道。
- 工具暴露真实模型信息时原样记录；未暴露时写“未暴露”，不得猜测。

素材权利复核：参考稿 6 张 JPEG 均不规划原样复用；`image3.jpg` 因水印排除，`image4.jpg` 因广告、商标和人物排除，其余照片只抽象为可替换内容图需求。

## 3. 自动化测试矩阵

| 案例 ID | 检查对象 | 输入边界 | 预期结果 | 证据类型 | 状态 |
|---|---|---|---|---|---|
| `case-spec-inventory` | ID、画布、页面库存、MVP、元素 ID | 36 个生产页面 | ID 全局唯一，库存与规格一致 | pytest + 页面清单 | `NOT_RUN` |
| `case-registration-and-resources` | 注册、JSON、封面、外置素材 | `/templates` 与 `/data/*` | 仅注册一次，全部资源 200，缺失资源安全 404 | pytest + API 摘要 | `NOT_RUN` |
| `case-contents-capacity` | 目录精确选版 | 2、3、4、5、6、10、11 项 | 支持容量精确匹配，11 项无损分页 | pytest | `NOT_RUN` |
| `case-text-capacity` | 纯文字正文选版 | 1 至 6 项 | 选择对应 item 槽位且无空内容图框 | pytest | `NOT_RUN` |
| `case-specialty-layout-kind` | 专项版式可达性 | 7 种 `layoutKind` | 每种版式可由确定输入选中，普通内容不误入专项页 | pytest | `NOT_RUN` |
| `case-overflow-eight-items` | 多项分页 | 8 项正文 | 两页、原顺序、字符不丢失 | pytest | `NOT_RUN` |
| `case-long-body-split` | 长正文分页 | 中英文混合长文本 | 不低于最小字号，片段拼接等于原文 | pytest | `NOT_RUN` |
| `case-long-body-with-images` | 带图长正文 | 2 项、2 图、首项超长 | 图片只在对应首段，续段进入纯文字页 | pytest + 渲染图 | `NOT_RUN` |
| `case-image-crop-ratios` | 内容图裁切 | 1600×900、900×1600、1000×1000 | 保持比例并中心裁切到目标框 | pytest + 渲染图 | `NOT_RUN` |
| `case-missing-image-dimensions` | 缺失尺寸边界 | 仅 `src` | 返回 `TEMPLATE_DATA_INVALID`，不拉伸 | pytest | `NOT_RUN` |
| `case-image-count-mismatch` | 图片/正文数量边界 | 图片多于正文项、封面 2 图 | 返回安全错误和最小上下文 | pytest | `NOT_RUN` |
| `case-decoration-isolation` | 图片角色与分组 | 内容图 + 五项固定装饰 | content 可换，decoration 锁定且引用本模板资源 | pytest + JSON 摘要 | `NOT_RUN` |
| `case-assets-contract` | 素材文件 | 五项发布素材 | 格式、尺寸、模式、Alpha、体积、文件名和引用均正确 | pytest + 文件摘要 | `NOT_RUN` |
| `case-rights-review` | 来源和授权 | 五项素材与参考媒体 | 来源、提示词和替代动作完整，无未知素材复用 | 人工审计记录 | `NOT_RUN` |
| `case-visual-review` | 所有页面视觉 | 36 页生产模板及真实作品 | 无遮挡、溢出、模糊、低对比和异常换行 | 全页蒙太奇 + 逐页记录 | `NOT_RUN` |
| `case-font-fallback` | 字体与字号 | 缺少参考字体环境 | 使用微软雅黑/Arial，最小字号和排版稳定 | pytest + 渲染图 | `NOT_RUN` |

规划测试命令，不在本次执行：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_14.py
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_renderer.py backend/main_api/tests/test_template_assets.py
```

## 4. 图片数量与语义边界

| 案例 ID | 输入 | 通过标准 | 状态 |
|---|---|---|---|
| `case-image-counts` | 0、1、2、3、4、5、6、7 张内容图 | 0 图选纯文字；1 至 6 图按精确槽位；7 图无损拆为 6+1；图片与内容项一一对应 | `NOT_RUN` |

补充边界：

- 封面仅允许 0 或 1 张内容图；2 张必须明确失败。
- 图片缺失宽高必须失败，不能猜测比例。
- 图片多于内容项必须失败，错误上下文只含数量，不泄露完整用户正文。
- 内容图 `imageType=content`；固定视觉 `imageType=decoration`，两者不得成组。
- 横图、竖图、方图都要验证裁切；主体不得被裁出安全区。

## 5. 真实任务与交互 QA

| 案例 ID | 场景 | 操作 | 通过标准 | 计划证据 | 状态 |
|---|---|---|---|---|---|
| `case-real-worker-generation` | 真实商务主题生成 | 使用持久 Worker 和 `template_14` 生成覆盖 5 类页面与专项版式的作品 | 任务成功，声明页面类型出现，内容顺序和语义正确 | `doc/assets/template_14_qa/evidence.json` + 真实作品蒙太奇 | `NOT_RUN` |
| `case-picker-unique` | 模板选择列表 | 在桌面、笔记本、平板、手机打开选择器并选择模板 | 只显示一个 `template_14`，名称、封面正确，选择反馈清晰 | `devices/template-picker-*.png` | `NOT_RUN` |
| `case-edit-save-reload` | 文字可编辑 | 修改标题和正文、保存、刷新或重进 | 文本持久化，布局不溢出，保存按钮有加载与成功反馈 | `devices/editor-text-edited-1366x768.png` | `NOT_RUN` |
| `case-content-image-replace` | 内容图替换 | 替换横图、竖图和方图 | 裁切正确；背景、装饰和其他内容图不变；换图按钮有反馈 | `devices/editor-image-replaced-1366x768.png` | `NOT_RUN` |
| `case-async-error-feedback` | 异步失败和重试 | 模拟生成、保存、导出失败后重试 | 失败原因可见，按钮恢复可点，不重复提交，重试可成功或给出明确结果 | `devices/async-failure-retry.png` | `NOT_RUN` |

关键按钮检查范围：模板选择、生成、保存、替换图片、导出、失败重试。每个按钮必须出现加载、成功、失败或明确的假性交互反馈；不能点击后没有反应。

## 6. 视口矩阵

| 案例 ID | 设备类别 | 宽 × 高 | 检查点 | 计划截图 | 状态 |
|---|---|---:|---|---|---|
| `viewport-desktop` | 桌面 | 1920 × 1080 | 无横向溢出；模板卡、画布、工具栏和关键按钮可见可触达 | `devices/editor-1920x1080.png` | `NOT_RUN` |
| `viewport-laptop` | 笔记本 | 1366 × 768 | 主编辑区不被侧栏挤压；浮层不遮挡保存、换图和导出 | `devices/editor-1366x768.png` | `NOT_RUN` |
| `viewport-tablet` | 平板 | 768 × 1024 | 工具区可折叠；触控目标足够；模板选择与反馈不越界 | `devices/editor-768x1024.png` | `NOT_RUN` |
| `viewport-mobile` | 手机 | 390 × 844 | 单列布局；无横向滚动；关键按钮可触达且反馈可见 | `devices/editor-390x844.png` | `NOT_RUN` |

四种视口都要覆盖模板选择器与编辑器关键操作，不只检查静态模板渲染图。

## 7. PPTX 往返

| 案例 ID | 检查 | 通过标准 | 计划证据 | 状态 |
|---|---|---|---|---|
| `export-roundtrip` | 导出、解析、重导入与继续编辑 | 页数与核心结构合理，重导入后标题和内容图仍可编辑，装饰角色不漂移 | `exports/template_14_roundtrip_summary.json` + 重导入截图 | `NOT_RUN` |

## 8. 完成条件覆盖

| 完成条件 ID | 案例 ID | 预期证据 |
|---|---|---|
| `criterion-reference-rights` | `case-rights-review`、`case-assets-contract` | 来源、提示词、权利动作和文件摘要 |
| `criterion-visual-system` | `case-visual-review` + 四视口 | 全页蒙太奇与设备截图 |
| `criterion-page-inventory` | `case-spec-inventory` | pytest 与页面清单 |
| `criterion-deterministic-selection` | 目录、正文容量与专项版式案例 | 选版断言 |
| `criterion-typography` | `case-font-fallback`、长正文、视觉检查 | 字号断言与渲染图 |
| `criterion-overflow` | 8 项、长正文、带图长正文 | 字符守恒与真实渲染 |
| `criterion-image-protocol` | `case-image-counts`、裁切、错误边界 | pytest 与换图截图 |
| `criterion-decoration-isolation` | 角色隔离与换图 | JSON 摘要与编辑器截图 |
| `criterion-assets` | 素材契约和权利复核 | 文件摘要与来源记录 |
| `criterion-registration` | 注册资源与选择器唯一性 | API 摘要与截图 |
| `criterion-real-generation` | 真实 Worker 与专项版式 | 真实任务蒙太奇与 evidence.json |
| `criterion-responsive` | 四视口 | 设备截图 |
| `criterion-interactions` | 异步失败与四视口 | 加载/成功/失败/重试截图 |
| `criterion-editable` | 文字保存重载与换图 | 编辑器截图与重载记录 |
| `criterion-export-roundtrip` | `export-roundtrip` | 往返摘要、重导入截图和可编辑文件 |

所有完成条件均已映射至少一个真实案例；规划规格中的 `qa.coverage_map` 是机器校验的权威映射。

## 9. 证据目录策略

标准入口：`doc/assets/template_14_qa/evidence.json`。

后续默认计划提交：

- `evidence.json`。
- 生产模板和真实任务蒙太奇。
- 桌面、笔记本、平板和手机关键截图。
- 编辑、换图、失败重试和 PPTX 重导入关键截图。
- 提示词、来源、授权动作和素材摘要。

后续默认不提交：

- 图片生成原图和全部失败尝试。
- 全部逐页原始截图。
- 大型 QA PPTX、临时导出和中间缓存。
- 进程日志、访问令牌或包含用户数据的调试文件。

## 10. 待确认与已知限制

开放决策：无阻断性开放决策。规格已经达到 `READY_FOR_BUILD`，但开发、图片生成、真实 QA 和最终人工闭合仍需新的明确授权。

已知限制：

- 当前环境不能把参考 PPTX 渲染为逐页 PNG，因而不把逐像素复刻作为验收目标。
- 参考照片和字体权利未知，固定视觉必须原创重绘，照片必须由用户内容图或许可清楚素材替换。
- `process / compare / hub-spoke / timeline / gallery / focus` 需要内容 Agent 显式提供 `data.layoutKind`；后续测试必须证明这些入口真实可达。

本文件目前的所有状态均为 `NOT_RUN`，没有任何模板开发、图片生成、测试通过或上线结论。

# 深蓝青棱商务信息图 PPT 模板开发说明

## 1. 文档状态

| 项目 | 内容 |
|---|---|
| 模板名称 | `深蓝青棱商务信息图` |
| 候选模板 ID | `template_14`，仅为候选，不代表已占用或已注册 |
| 机器规格 | `doc/template_specs/template_14.yaml` |
| 规格状态 | `READY_FOR_BUILD`，只表示规划闭环，不表示已获开发授权 |
| 规划日期 | `2026-08-29` |
| 本文范围 | 只定义开发计划，不生成图片、不修改代码、不运行服务、不执行 Git 或发布操作 |

## 2. 目标与非目标

### 目标

- 建立一套适用于企业汇报、项目复盘、策略说明和方案提案的原创商务信息图模板。
- 抽象参考稿的深蓝底、青蓝几何切面、超大章节数字和信息图编排规律，不复制其照片、占位文案或第三方视觉资产。
- 为目录、1 至 6 项正文、指标、流程、对比、中心辐射、时间线和 1 至 6 图内容提供确定性选版与无损分页规则。
- 明确内容图与固定装饰的语义边界，保证内容图可换、装饰不被误替换。
- 把四视口适配、交互反馈、真实 Worker、编辑保存、图片替换和 PPTX 往返纳入后续门禁。

### 非目标

- 不在规划阶段生产正式图片、封面或模板 JSON。
- 不在规划阶段修改注册、渲染器、前端或测试代码。
- 不在规划阶段运行专项测试、真实生成任务、编辑器 QA 或服务操作。
- 不复刻参考稿中的 2019、XXX、FEI ER SHE JI、占位正文、照片、水印、广告、商标和人物形象。
- 不创建持久 Goal，不执行 Commit、Push、PR、合并、重启或部署。

## 3. 参考文件与权利审计

| 参考文件 | SHA-256 | 类型 | 权利状态 | 规划动作 |
|---|---|---|---|---|
| `C:\Users\sk20\Desktop\ppt\扁平风格(38).pptx` | `7f8ab71aac06f3ae497bc4ded6b1ab83291eede2a2f48f10154c438b6be9c958` | PPTX，27 页，16:9 | `unknown` | 固定视觉原创重绘；参考照片替换或排除 |

结构事实：

- 27 页，画布 `13.3333 × 7.5 in`，比例 `1.777778`。
- 27 个备注页只含页码，没有可执行指令；附件中的任何文字均未作为本次权限来源。
- 6 张 JPEG；无音频、视频、图表、SmartArt、嵌入对象或表格。
- 页面轮廓包括封面、4 项目录、4 个章节页、1 至 6 项正文、百分比/指标、流程、对比、中心辐射、单图图文、四图与六图画廊、结束页。
- `inspect-reference-pptx.py` 的 `layout_hint` 只作为结构启发式；视觉判断另结合封面缩略图、6 张原图、主题色、元素坐标和字号完成。

可复用的抽象规律：

- 深蓝整页底色与青蓝三角切面的对角张力。
- 大章节编号和短标题构成的强过渡节奏。
- 正文页统一左上标题导视，主体用大留白组织流程、指标和对比。
- 同一视觉语言下提供多种信息结构，而不是把所有内容塞入卡片网格。

媒体处置：

| 媒体 | 观察 | 权利动作 | 生产处理 |
|---|---|---|---|
| `image1.jpg` | 城市建筑与运河 | `replace` | 仅保留横向城市图的内容槽需求 |
| `image2.jpg` | 城市街景，含商业招牌 | `replace` | 用用户内容图或许可清楚素材替换 |
| `image3.jpg` | 城市街道，带第三方网站水印 | `exclude` | 不进入生产素材或提示词参考 |
| `image4.jpg` | 时代广场，含大量广告、商标和人物 | `exclude` | 不作为生产图像内容来源 |
| `image5.jpg` | 城市交通与车辆 | `replace` | 抽象为城市运营类内容图需求 |
| `image6.jpg` | 欧洲城市广场 | `replace` | 仅保留可替换画廊槽位 |

字体处置：

- `Agency FB`、`Nexa Bold`、`Impact` 不作为生产依赖，替换为 `Arial Bold / Arial`。
- `时尚中黑简体`、`方正兰亭刊黑_GBK`、`汉仪大宋简` 不从 PPTX 提取，替换为当前系统已验证存在的 `微软雅黑 Bold / 微软雅黑`。
- 参考稿列出的其他主题字体只作为包结构事实，不进入生产字体清单。

视觉核验限制：artifact-tool 可导入全部 27 页，但在导出 PNG 时退出；本机没有 PowerPoint 或 LibreOffice。因此本计划不主张逐像素复刻，而是用结构、缩略图、媒体、主题色和元素几何形成原创生产方向。该限制不改变“未知素材不复用”的权利结论。

## 4. 当前项目发现

| 项目 | 当前发现 | 发现依据 |
|---|---|---|
| 模板目录 | `backend/main_api/template` | 当前仓库与候选 ID 脚本扫描 |
| 注册入口 | `backend/main_api/main.py` 的 `/templates` | 当前仓库扫描 |
| 渲染器 | `backend/main_api/workers/template_renderer.py` | 当前仓库扫描 |
| 专项测试入口 | `backend/main_api/tests/test_template_<N>.py` | 当前测试目录扫描 |
| 通用回归 | `test_template_renderer.py`、`test_template_assets.py` | 当前测试目录扫描 |
| 已占用编号 | `template_1` 至 `template_13`，其中 `template_6` 为注释保留 | 注册、JSON、封面、素材和专项测试联合扫描 |
| 候选 ID | `template_14` | `discover-template-id.py`，状态为 `available_at_scan_time` |

候选 ID 不会被规划文件占用。开发开始前必须重新运行扫描；若 `template_14` 已被任何注册、JSON、封面、素材或专项测试占用，先回到规划阶段更新 ID 和全部文件名。

当前分支已有未跟踪的 `.codex-tmp/`、`.codex_tmp/` 和 `doc/assets/template_10_qa/originals/`；本次未读取、改写或清理这些用户产物。

## 5. 视觉 Brief

- 沟通任务：让企业汇报受众在短时间内抓住结论、结构、关键数据和下一步行动，因为模板把复杂内容稳定映射为清晰的信息图层级。
- 主题与语气：理性、清晰、可信、现代，但不做霓虹科技感或重 UI 卡片感。
- 场景：企业内部汇报、项目复盘、策略说明、实施计划、方案提案和城市/运营类图文材料。
- 主色：深蓝 `#354A62`、深海军蓝 `#243447`、青蓝 `#45BEE3`、辅助蓝 `#28A7CF`。
- 辅色：暖白 `#F6F8FA`、灰蓝 `#6C7B8B`；警示红 `#FD5B5B` 只用于真实风险或负向变化。
- 中文字体：标题 `微软雅黑 Bold`，正文 `微软雅黑`；西文标题 `Arial Bold`，西文正文 `Arial`。
- 最小字号：封面 44、正文页标题 28、章节号 60、条目标题 18、指标 24、正文 16、图注和页脚 12。
- 构图：封面/章节/结束页为深色沉浸面；正文页用暖白底，青蓝导视线和少量几何切面提供节奏。
- 安全区：封面标题限制在 `x=88..760,y=184..398`；正文标题区 `x=44..956,y=28..104`；正文主体 `x=52..948,y=126..516`；页脚仅在 `y=528..552`。
- 禁止内容：未授权 Logo、商标、真实人物、第三方 UI、假截图、假数据、水印、参考占位文案和不可读小字号。

## 6. 页面系统

### MVP 页面矩阵

| 页面类型 | 数量 | 容量或变体 | 验证目的 |
|---|---:|---|---|
| 封面 | 1 | 无内容图 | 验证深色主视觉和两行标题安全区 |
| 目录 | 3 | 3 / 4 / 6 项 | 验证常用目录精确选版 |
| 章节 | 1 | 超大编号 + 标题 + 短说明 | 验证章节节奏与自动编号 |
| 纯文字正文 | 6 | 1 / 2 / 3 / 4 / 5 / 6 项 | 验证容量和无图选版 |
| 图文正文 | 4 | 1 / 2 / 4 / 6 图，图项一一对应 | 验证严格内容图协议 |
| 指标正文 | 1 | 4 项 `metrics` | 验证数字语义选版 |
| 流程正文 | 1 | 4 项 `process` | 验证显式 `layoutKind` |
| 结束页 | 1 | 行动收束 | 验证可读默认文案与安全区 |

MVP 共 18 个模板页面，只用于后续开发门禁；规划阶段没有构建或测试这些页面。

### 生产版页面矩阵

| 页面类型 | 数量 | 选择条件 | 说明 |
|---|---:|---|---|
| 封面 | 2 | 内容图数量 0 或 1 精确匹配 | 无图极简版、单图版 |
| 目录 | 6 | 2 / 3 / 4 / 5 / 6 / 10 项精确匹配 | 超量时无损分页 |
| 章节 | 2 | `variantMode=deterministic` | 深色大编号版、紧凑导语版 |
| 纯文字正文 | 9 | 1 至 6 项精确容量；2、3、4 项有稳定轮换变体 | 单结论、并列、四象限等 |
| 图文正文 | 6 | 1 至 6 图且图片数等于内容项数 | 单图分栏到六图画廊 |
| 指标正文 | 3 | `layoutKind=metrics`，3 / 4 / 5 项 | 环形、条形、中心指标 |
| 流程正文 | 2 | `layoutKind=process`，4 / 5 项 | 横向链路、折线推进 |
| 对比正文 | 2 | `layoutKind=compare`，2 / 4 项 | 双栏与四项同口径对比 |
| 中心辐射 | 1 | `layoutKind=hub-spoke`，5 项 | 中心主题 + 四分支 |
| 时间线 | 1 | `layoutKind=timeline`，4 项 | 里程碑或阶段结果 |
| 结束页 | 2 | `variantMode=deterministic` | 行动收束、联系信息 |

生产版共 36 个模板页面。数量来自本次需要覆盖的容量、严格图片协议和专项版式，不是复制参考稿的 27 页。

### 专项版式与确定性规则

| ID | 用途 | 确定性选版规则 |
|---|---|---|
| `metrics-radial` | 3 至 5 个指标或占比 | `layoutKind=metrics`，或 item.kind 为 `metric/number/stat`，再按项数精确选版 |
| `process-chain` | 4 或 5 个步骤 | `layoutKind=process`、无图、项数 4 或 5 |
| `compare-balanced` | 2 项或 4 项对比 | `layoutKind=compare`、无图、项数 2 或 4 |
| `hub-spoke` | 中心主题与四个分支 | `layoutKind=hub-spoke`、无图、恰好 5 项 |
| `timeline-zigzag` | 4 个日期或里程碑 | `layoutKind=timeline`、无图、恰好 4 项 |
| `image-gallery` | 3 至 6 张等权内容图 | `layoutKind=gallery`，图片数等于内容项数并精确匹配 3 / 4 / 5 / 6 图 |
| `headline-focus` | 单一结论或关键动作 | `layoutKind=focus`、无图、恰好 1 项 |

容量与溢出策略：

- 目录容量：2、3、4、5、6、10。
- 正文容量：1、2、3、4、5、6。
- 7 项及以上按每页最多 6 项无损分页，保留字符和顺序，续页标题追加“（续）”。
- 长正文按渲染器可读容量拆分；拼接所有片段后必须与原文逐字相同。
- 带图长正文只在第一段保留内容图，后续段落进入纯文字页。
- 不通过缩小到 16 pt 以下正文或 12 pt 以下图注来换取容量。

## 7. 素材清单

| ID | 角色 | 文件名 | 格式/尺寸/模式 | Alpha | 体积上限 | 安全区 | 权利动作 | 重试上限 |
|---|---|---|---|---|---:|---|---|---:|
| `cover-background` | 背景 | `template_14_asset_bg_cover_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 350000 | 中左标题区低细节，装饰限右上与左下 | `regenerate` | 3 |
| `section-background` | 背景 | `template_14_asset_bg_section_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 320000 | 中央和左中部保留章节号与标题 | `regenerate` | 3 |
| `end-background` | 背景 | `template_14_asset_bg_end_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 320000 | 中央结束语区低细节 | `regenerate` | 3 |
| `facet-corner` | 固定装饰 | `template_14_asset_facet_corner_v1.png` | PNG / 1400×900 / RGBA | 是 | 1000000 | 主体只在右上与左下，中央透明 | `regenerate` | 3 |
| `line-particle-overlay` | 固定装饰 | `template_14_asset_line_particle_v1.png` | PNG / 1400×900 / RGBA | 是 | 800000 | 稀疏线点只在边缘，文字区透明 | `regenerate` | 3 |

全局最多 15 次生成尝试。提示词必须禁止文字、Logo、水印、真实人物、第三方 UI、假图表和参考照片复刻。图像生成只在用户后续明确授权实施后进行。

## 8. 语义与渲染契约

- 页面类型：`cover / contents / transition / content / end`。
- 文字槽：`title / subtitle / section-number / item / itemNumber / metric / content / caption / footer`。
- 内容图片：`imageType: content`，必须独立可替换，不与标题或固定装饰成组。
- 固定装饰：`imageType: decoration`，锁定且只能引用 `template_14_asset_*` 发布资源。
- 图片分组：`content-images-independent`。
- 内容溢出：`paginate-without-loss`。
- 封面图片：按 0 图或 1 图精确选版；提供 2 图必须明确失败。
- 正文图片：图片数必须等于内容项数；缺少宽高、图片多于内容项或无匹配槽位时返回安全错误。
- 专项版式：普通内容不得误入 `metrics` 等专项布局；显式 `data.layoutKind` 优先。

## 9. 后续开发阶段与门禁

1. 重新核验规格哈希、参考哈希、候选 ID、仓库协议和用户当前授权。
2. 在获得图片生成授权后，按 manifest 生产五项原创素材并记录来源、提示词、真实模型暴露信息与重试。
3. 构建 18 页 MVP，完成容量、语义图片和真实生成门禁。
4. 扩展到 36 页生产版并注册 `template_14`。
5. 编写并运行 `test_template_14.py` 以及受影响通用回归。
6. 使用持久 Worker 完成真实任务、四视口、文字编辑、换图、失败重试和 PPTX 往返。
7. 汇总精简证据，自动状态最多到 `READY_FOR_CONFIRMATION`。
8. 只有用户明确确认后，后续执行流才能闭合为 `DONE` 或 `DONE_WITH_CONCERNS`。

## 10. 测试与 QA 覆盖摘要

| 完成条件 | 主要案例 | 预期证据 |
|---|---|---|
| 参考与权利 | `case-rights-review`、`case-assets-contract` | 来源、提示词与权利动作记录 |
| 页面库存与选版 | `case-spec-inventory`、`case-contents-capacity`、`case-specialty-layout-kind` | 专项测试输出与页面清单 |
| 无损分页 | `case-overflow-eight-items`、`case-long-body-split`、`case-long-body-with-images` | 字符守恒断言与真实渲染 |
| 图片协议 | `case-image-counts`、裁切、缺失尺寸、数量不匹配 | 测试输出与换图截图 |
| 注册与资源 | `case-registration-and-resources`、`case-picker-unique` | API 结果与模板列表截图 |
| 响应式与交互 | 四个 viewport、`case-async-error-feedback` | 关键截图和失败重试截图 |
| 编辑与导出 | `case-edit-save-reload`、`case-content-image-replace`、`export-roundtrip` | 重载截图、往返摘要和可编辑文件 |

目标视口：1920×1080 桌面、1366×768 笔记本、768×1024 平板、390×844 手机。

## 11. 预期交付物

- 已完成的规划规格：`doc/template_specs/template_14.yaml`。
- 后续模板 JSON：`backend/main_api/template/template_14.json`。
- 后续封面：`backend/main_api/template/template_14.jpg`。
- 后续五项素材：`backend/main_api/template/template_14_asset_*`。
- 后续专项测试：`backend/main_api/tests/test_template_14.py`。
- 后续 QA 证据入口：`doc/assets/template_14_qa/evidence.json`。

除规划规格和本文外，其余均是未来产物，不是本次已经开发或测试的文件。

## 12. 权限、开放决策与已知限制

后续实施必须重新取得图片生成、代码修改、真实任务执行和最终人工闭合的当前授权。Commit、Push、PR、合并、重启和生产部署必须分别获得明确授权，不能从模板开发授权中推导。

开放决策：无阻断性开放决策。模板名称、权利替代、视觉方向、页面矩阵、容量、素材和 QA 已形成可执行建议；`READY_FOR_BUILD` 不代表用户已授权开发。

已知限制：

- 当前环境无法生成参考 PPTX 的逐页 PNG，因此不承诺逐像素复刻；实施应坚持原创重绘，并在真实 QA 中以规格而不是参考截图作为主要门禁。
- 参考 PPTX 和 6 张照片的授权来源未知，任何原图与字体文件都不得直接进入生产模板。
- 当前渲染器只会从数字 item 自动推断 `metrics`；其他专项版式需要内容 Agent 显式提供 `data.layoutKind`。

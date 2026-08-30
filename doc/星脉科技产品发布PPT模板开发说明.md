# 星脉科技产品发布 PPT 模板开发说明

## 1. 文档状态

| 项目 | 内容 |
|---|---|
| 模板名称 | `星脉科技产品发布` |
| 候选模板 ID | `template_15`，仅为候选，不代表已占用 |
| 机器规格 | `doc/template_specs/template_15.yaml` |
| 规格状态 | `READY_FOR_BUILD` |
| 规划日期 | `2026-08-30` |
| 执行模式 | `plan-only` |
| 本文范围 | 只定义开发计划，不生成图片、不修改模板代码、不运行服务、不执行 Git 发布 |

## 2. 模板目标

### 沟通任务

一套成稿应让发布会观众、客户或内部决策者沿着“发布主张 → 核心性能 → 差异化证据 → 市场定位 → 行动收束”的顺序理解产品价值，并能据此形成下一步判断。

### 目标

- 把参考稿的深蓝舞台、蓝紫光谱地平线、超大结论文字和单一产品主角抽象为可复用的 16:9 科技发布模板。
- 支持从极简发布主张到性能指标、产品比较、场景定位、路线图和多图细节等真实内容密度。
- 保证内容图可独立替换、长内容无损分页、专项版式可确定性到达，并覆盖多设备交互与 PPTX 往返。

### 非目标

- 不复刻参考稿的 3:1 画布、具体手机/手表、城市照片、品牌文案、字体文件、动画或音频。
- 不在规划阶段生产正式图片、模板 JSON、封面或专项测试。
- 不在规划阶段修改注册、渲染器、前端或测试代码。
- 不在规划阶段运行真实任务、提交代码、合并、重启或部署。

## 3. 参考稿事实与结构分析

参考文件：`C:\Users\sk20\Desktop\ppt\产品发布 (2).pptx`

SHA-256：`390cfaaec81834b9fc96b72d647bc807ba45f271e3f15cd826655c9433f14944`

结构化盘点：

| 项目 | 结果 |
|---|---:|
| 幻灯片 | 25 页 |
| 原始画布 | 23.6215 × 7.8733 英寸，宽高比约 3.00022:1 |
| 备注页 | 25 |
| 图片资源 | 42 个（38 PNG、4 JPEG） |
| WDP 资源 | 17 个 |
| 音频 | 1 个 WAV，约 19 MB |
| 视频 / 图表 / SmartArt / 嵌入对象 | 0 |

页面叙事分组：

| 参考页 | 角色 | 抽象价值 |
|---|---|---|
| 1 | 封面 | 极简品牌栏、超大发布主张、底部光谱舞台 |
| 2 | 目录 | 4 个章节，建立发布叙事 |
| 3 / 9 / 15 / 20 | 章节过渡 | 大标题 + 单一抽象背景，节奏明确 |
| 4–8 | 性能表现 | 单特性、设备主图、体验结论 |
| 10–14 | 突出优势 | 大数字、功能特写、生态/配件说明 |
| 16–19 | 同级比较 | 产品线、价格、GPU、系统对比 |
| 21–24 | 市场定位 | 游戏、商务、安全、智慧生活场景 |
| 25 | 结束页 | 产品系列与发布会收束 |

人工视觉判断与脚本启发式已分开：结构来自 OOXML 确定性提取；视觉判断来自封面缩略图、全部嵌入媒体蒙太奇、图片关系和页面布局坐标。当前演示文稿运行时不能完整渲染这份文件，因此不声称已经逐页像素级复核；该限制不会转化为原样复刻授权。

## 4. 权利审计

参考文件整体权利状态为 `unknown`。没有任何参考媒体被规划为 `reuse`。

| 媒体类别 | 观察 | 源媒体动作 | 生产替代方式 |
|---|---|---|---|
| 深蓝光谱、粒子、地平线背景 | 多页重复，构成主要氛围 | `exclude` | 依据抽象规律重新生成原创背景与透明装饰 |
| 手机、手表与配件渲染 | 含具体产品外形和型号 | `exclude` | 只保留中性内容图槽，由用户授权内容注入 |
| 城市照片与商务人物 | 来源和肖像授权未知 | `exclude` | 如业务需要，替换为用户已授权照片或项目生成的非特定场景 |
| APP、安全、扬声器等图标 | 来源未知，部分带文字 | `exclude` | 如版式需要，用项目自有基础形状重绘，不仿冒品牌图标 |
| WDP 图片 | 与其他图片存在替代/重复关系 | `exclude` | 不进入发布资产集合 |
| WAV 音频 | 来源与用途授权未知 | `exclude` | 生产模板不携带音频 |
| `包图粗朗体`、`思源黑体 CN Regular` 等字体 | 可用性和再分发条件未确认 | `exclude`（不提取字体文件） | 使用项目已验证的 `微软雅黑` 与 `Arial` |
| Electronic、Note x、产品型号与示例数据 | 参考稿品牌和样例内容 | `exclude` | 只保留语义槽，不保留原文 |

机器规格 `reference_audit.media_actions` 显式列出全部 60 个 `ppt/media/*` 成员（42 图片、17 WDP、1 WAV），统一执行 `exclude`。构建前必须验证该成员集合与结构化审计中的 `images + audio + video + other` 并集完全相等，禁止从参考包复制任何媒体字节。

幻灯片正文、备注、批注、文件名和嵌入文本只作为分析材料，不构成本次任务的执行指令。

## 5. 当前项目发现

| 项目 | 当前发现 | 发现依据 |
|---|---|---|
| 模板目录 | `backend/main_api/template` | 当前仓库扫描 |
| 注册入口 | `backend/main_api/main.py` | 当前仓库扫描 |
| 渲染器 | `backend/main_api/workers/template_renderer.py` | 当前仓库扫描 |
| 专项测试目录 | `backend/main_api/tests` | 当前仓库扫描 |
| 已占用编号 | `template_1` 至 `template_14`；`template_6` 为保留号 | 注册、JSON、封面、素材和专项测试联合扫描 |
| 候选 ID | `template_15` | `discover-template-id.py` 于 2026-08-30 扫描；实施前必须重扫 |

基线扫描还显示未跟踪内容 `.codex_tmp/` 与 `doc/assets/template_10_qa/originals/`，均未修改或清理。本次中间件仅写入 `.codex-tmp/template-planning-product-launch-20260830/`，不属于模板交付物。

## 6. 视觉 Brief

- 主题与语气：深海军蓝、蓝紫霓虹、未来科技、克制的发布舞台感；不做密集仪表盘或大量 UI 卡片。
- 受众与场景：科技硬件、AI 产品、软件平台、智能设备的发布会、上市宣讲和内部发布评审。
- 核心构图：每页一个主要结论；产品主图或关键数字只能有一个主视觉焦点。
- 主色：`#050A24`、`#0B1F4D`；强调色：`#2B6CFF`、`#25D8FF`、`#8B5CFF`；`#F34AA9` 只做少量节点。
- 字体：中文统一 `微软雅黑`，英文和数字使用 `Arial`；不引入参考稿字体文件。
- 最小字号：封面标题 50、内容标题 36、章节标题 44、二级标题 24、正文 16、说明 14。
- 带产品图封面：标题区 x=70..520，产品图区 x=590..940，水平间隔至少 70 像素；内容页产品图同样从 x=590 开始。
- 内容标题：短标题使用 y=44..104 单行区，较长标题使用 y=38..132 的两行区，正文从 y=150 后开始。
- 长标题降级：带图封面超过 24 个中文字符或 48 个拉丁字符时改选无图封面；无图封面超过 36/72 时明确报错。内容标题在 20/44 以内单行，超过后进入两行区，超过 36/80 时明确报错；全程不截断、不遮图、不缩小到最小字号以下。
- 中英数字混排计量：文本先做 NFC 规范化并去除首尾空白；ASCII 字母、数字、半角标点和内部空格计入 `ascii_count`，CJK、全角及其他非 ASCII 码点计入 `wide_count`。使用 `wide_count×latin_limit + ascii_count×cjk_limit <= cjk_limit×latin_limit` 判定，不按字节数或总字符数猜测。
- 全局安全区：可编辑信息保持在 x=64..936、y=42..516；光谱装饰限制在底部，不压正文。
- 适配原则：参考稿的 3:1 横向张力改为 16:9 的“左文右图”或“上文下舞台”，不做横向拉伸。

## 7. 页面系统

### MVP 页面矩阵

| 页面类型 | 数量 | 容量或变体 | 验证目的 |
|---|---:|---|---|
| 封面 | 2 | 无图极简、1 图产品主角 | 验证标题安全区和产品图注入 |
| 目录 | 4 | 3 / 4 / 5 / 6 项 | 验证精确容量和章节编号 |
| 章节过渡 | 2 | 居中地平线、左题右光场 | 验证章节节奏和标题适配 |
| 正文 | 11 | 1–6 项普通内容、单图 hero、3/4 指标、双方案对比、3 图画廊 | 验证核心语义协议与选版 |
| 结束 | 1 | 中央行动收束 | 验证结束页安全区 |

MVP 共 20 个版式，只作为生产扩展前的门禁集合。

### 生产版页面矩阵

| 页面类型 | 数量 | 选择条件 | 说明 |
|---|---:|---|---|
| 封面 | 2 | 内容图 0 或 1 张 | 极简发布主张 / 产品主角 |
| 目录 | 4 | 章节数 3–6 | 精确容量，不留空占位 |
| 章节过渡 | 4 | 章节序号轮换或显式变体 | 地平线、光谱、粒子、舞台四种节奏 |
| 正文 | 27 | 普通容量、图片数量或显式 `layoutKind` | 覆盖主张、图文、指标、比较、画廊、路线图、流程、定位 |
| 结束 | 2 | 行动项有无 | 极简结束 / 行动收束 |

生产版共 39 个版式；数量来自本参考稿的发布叙事和本项目语义协议，不照搬历史模板。

### 稳定版式 ID 矩阵

| 页面类型 | 稳定 ID | 数量 | 选择规则摘要 | MVP |
|---|---|---:|---|---|
| 封面 | `cover-minimal`、`cover-hero` | 2 | 0 图用极简；1 图且标题满足带图上限用 hero，超限改选极简 | 全部 |
| 目录 | `contents-3`、`contents-4`、`contents-5`、`contents-6` | 4 | 目录项数量精确匹配；7 项以上按平衡规则分页 | 全部 |
| 章节 | `transition-horizon`、`transition-spectrum`、`transition-particle`、`transition-stage` | 4 | 显式 `variant` 优先，否则按从 1 开始的 `sectionIndex mod 4`；未知值报错 | 前 2 个 |
| 普通正文 | `content-text-1` 至 `content-text-6` | 6 | 无图、无显式专项版式、项目数精确匹配；3–5 项全为 metric 时排除普通正文；1 项兼容 `focus` | 全部 |
| 单图正文 | `content-hero-left`、`content-hero-right`、`content-image-1-dense` | 3 | 1 图 + 1–3 项按左右变体；1 图 + 4–6 项用窄图密集版 | `hero-left` |
| 双图正文 | `content-dual-image-2` | 1 | 2 图 + 2–6 项 | 否 |
| 指标 | `content-metrics-3`、`content-metrics-4`、`content-metrics-5` | 3 | 3–5 项全部为 `kind=metric` 或显式 `metrics` | 前 2 个 |
| 对比 | `content-compare-2`、`content-compare-4` | 2 | 显式 `compare` 且 2 / 4 项 | `compare-2` |
| 画廊 | `content-gallery-3`、`content-gallery-4`、`content-gallery-5`、`content-gallery-6` | 4 | 默认 3–6 图与项目等量；显式 gallery 另允许 2 图 + 2–6 项并用 dual-image | `gallery-3` |
| 时间线 | `content-timeline-3`、`content-timeline-4`、`content-timeline-5` | 3 | 显式 `timeline` 且 3–5 项 | 否 |
| 流程 | `content-process-3`、`content-process-4`、`content-process-5` | 3 | 显式 `process` 且 3–5 项 | 否 |
| 定位 | `content-positioning-3`、`content-positioning-4` | 2 | 显式 `positioning` 且 3 / 4 项 | 否 |
| 结束 | `end-minimal`、`end-action` | 2 | 0 项极简；1–3 项行动收束 | `end-minimal` |

上述 catalog 恰好包含 39 个生产版式；MVP 标记恰好覆盖 20 个版式。每个 ID 的完整选择条件保存在机器规格 `pages.layout_catalog`，构建者不得自行补发未声明变体。

选版优先级固定为：先验证显式 `layoutKind`，再验证图片矩阵，然后选择合法显式专项版式；无显式版式时先按图片数量选版，再让 3–5 个全 `metric` 项优先进入指标版，最后才进入普通正文。`content-text-3/4/5` 明确排除“全部为 metric”的输入，因此每个合法输入只能命中一个稳定 ID；显式专项版式缺图或项目数错误必须抛出 `TemplateRenderError`，不得静默回退。

### 专项版式

| ID | 用途 | 确定性选版规则 |
|---|---|---|
| `focus` | 单一发布主张 | 仅允许无图且 1 项；显式 focus 的其他组合报错 |
| `hero` | 产品主图 + 1–3 个卖点 | 仅允许 1 图且 1–3 项；显式 hero 的缺图、多图或 4 项以上报错 |
| `metrics` | 3–5 个指标 | 仅允许无图、3–5 项且全部 `kind=metric`；其他组合报错 |
| `compare` | 双产品/方案对比 | 仅允许显式 `compare`、无图、2 或 4 项；其他组合报错 |
| `gallery` | 2–6 张产品或场景图 | 2 图允许 2–6 项；3–6 图必须与 items 等量；其他组合报错 |
| `timeline` | 上市节奏或路线图 | 仅允许显式 `timeline`、无图、3–5 项；其他组合报错 |
| `process` | 技术链路或体验步骤 | 仅允许显式 `process`、无图、3–5 项；其他组合报错 |
| `positioning` | 目标人群和场景定位 | 仅允许显式 `positioning`、无图、3 或 4 项；其他组合报错 |

容量与溢出策略：

- 目录容量：3、4、5、6。
- 普通正文容量：1、2、3、4、5、6；7 项固定分页为 6+1，更多内容每页最多 6 项。
- 目录 7 项固定平衡为 4+3，11 项为 6+5；其他超量按每页 3–6 项、页间差不超过 1 的规则分页。
- 普通正文从 7 项起或长正文采用无损分页，保留字符、顺序和语义关联，不以不可读字号压缩。
- 1–6 张内容图精确选版；7 张固定 6+1，更多图片按对应 item 每页最多 6 张分页。
- 图片组合矩阵：0 图支持普通/指标/显式无图专项；1 图 + 1–3 项用 hero，1 图 + 4–6 项用 dense；2 图 + 2–6 项用 dual-image；3–6 图必须与 items 等量并用 gallery；7 图以上也必须与 items 等量后按每页最多 6 组分页。图片多于 items 或矩阵外组合明确报错。
- 带图长正文分页时，内容图只保留在首段；固定装饰在每页保持稳定。

## 8. 素材 manifest

| ID | 角色 | 文件名 | 格式/尺寸 | Alpha | 体积上限 | 安全区 | 权利动作 | 重试 |
|---|---|---|---|---|---:|---|---|---:|
| `bg-cover` | 背景 | `template_15_asset_bg_cover_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 380 KB | 左侧低细节，右侧产品舞台 | `regenerate` | 3 |
| `bg-section` | 背景 | `template_15_asset_bg_section_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 340 KB | 中央章节标题低细节区 | `regenerate` | 3 |
| `bg-end` | 背景 | `template_15_asset_bg_end_v1.jpg` | JPEG / 1920×1080 / RGB | 否 | 340 KB | 中央行动收束低细节区 | `regenerate` | 3 |
| `spectrum-footer` | 装饰 | `template_15_asset_spectrum_footer_v1.png` | PNG / 1600×520 / RGBA | 是 | 950 KB | 上方透明、底部粒子柱 | `regenerate` | 3 |
| `horizon-glow` | 装饰 | `template_15_asset_horizon_glow_v1.png` | PNG / 1600×700 / RGBA | 是 | 850 KB | 光弧位于下三分之一 | `regenerate` | 3 |
| `particle-field` | 装饰 | `template_15_asset_particle_field_v1.png` | PNG / 1600×900 / RGBA | 是 | 900 KB | 四角与底缘低密度粒子 | `regenerate` | 3 |
| `product-stage` | 装饰 | `template_15_asset_product_stage_v1.png` | PNG / 1200×700 / RGBA | 是 | 800 KB | 中央上方透明供产品图叠放 | `regenerate` | 3 |

全局素材生成重试上限为 21 次。正式提示词必须禁止文字、Logo、水印、伪代码、未授权肖像和具体产品外形。

## 9. 语义与渲染契约

- 页面类型：`cover`、`contents`、`transition`、`content`、`end`。
- 文字槽：`title`、`subtitle`、`item`、`itemNumber`、`metric`、`label`、`description`、`callout`。
- 用户内容图使用 `imageType: content`；固定背景与装饰使用 `imageType: decoration`。
- 内容图保持独立可替换，不与固定舞台、粒子或光谱装饰成组。
- 普通内容不能误入显式专项版式；`compare/gallery/timeline/process/positioning` 只按明确条件到达。
- 内容溢出统一使用 `paginate-without-loss`。

## 10. 开发阶段与门禁

1. 实施前重新核验参考哈希、规格哈希、候选 ID 和仓库结构。
2. 获得图片生成授权后按 manifest 生产并审计 7 项外置素材。
3. 构建 20 个 MVP 版式，先通过结构、容量、图片和错误边界测试。
4. 扩展为 39 个生产版式，并在模板列表唯一注册。
5. 运行 `test_template_15.py`、通用素材和渲染器受影响回归。
6. 使用持久 Worker 执行真实任务；完成文字编辑、内容图替换、失败重试和 PPTX 往返。
7. 验证桌面、笔记本、平板和手机视口，以及所有关键按钮反馈。
8. 汇总证据，自动状态最多进入 `READY_FOR_CONFIRMATION`；用户明确确认后才能闭合为 `DONE` 或 `DONE_WITH_CONCERNS`。

## 11. 测试与 QA 摘要

| 完成条件 | 主要案例 | 预期证据 |
|---|---|---|
| 参考权利隔离 | `case-reference-rights-audit` | 来源、动作和禁带清单 |
| 页面库存与协议 | `case-page-inventory`、`case-template-protocol` | 自动断言与 JSON 摘要 |
| 选版唯一性 | `case-selection-partition`、`case-image-item-matrix` | 每个合法输入恰好命中一个 ID，非法输入明确报错 |
| 容量与专项版式 | `case-contents-capacity`、`case-text-capacity`、`case-specialty-layouts` | 精确选版断言 |
| 标题与安全区 | `case-title-fit-boundaries` | 单行/两行/改选/报错边界与零重叠检查 |
| 分页与图片 | `case-overflow-pagination`、`case-image-counts`、`case-image-crop-and-errors` | 无损分页、裁切和错误边界 |
| 素材与注册 | `case-asset-manifest`、`case-registration-routes` | 文件属性与 API 响应 |
| 真实生成与编辑 | `case-worker-generation`、`case-edit-persistence`、`case-image-replacement` | 任务记录和关键截图 |
| 多设备与按钮 | 4 个视口、`case-button-feedback` | 截图和交互状态记录 |
| PPTX 往返 | `export-roundtrip` | 导出、解析、重导入摘要 |

目标视口：1440×900、1280×720、768×1024、390×844。

## 12. 规划交付物与未来产物

本次已写入：

- `doc/template_specs/template_15.yaml`
- `doc/星脉科技产品发布PPT模板开发说明.md`
- `doc/星脉科技产品发布PPT模板素材与QA计划.md`

后续开发预期产物：

- `backend/main_api/template/template_15.json`
- `backend/main_api/template/template_15.jpg`
- `backend/main_api/template/template_15_asset_*`
- `backend/main_api/tests/test_template_15.py`
- `doc/assets/template_15_qa/evidence.json`

这些生产文件尚未创建，不是本文已完成的产物。

## 13. 权限、开放决策与已知限制

后续实施必须重新取得图片生成、代码修改和真实 QA 授权。Commit、Push、PR、合并、重启和生产发布不包含在模板开发授权中。

开放决策：无。独立规划审计为 `PASS`，当前规格达到 `READY_FOR_BUILD`；该状态只表示规划输入完整，不表示已授权实施。

已知限制：

- `template_15` 只是本次扫描时可用的候选 ID，实施前必须重扫。
- 当前运行时不能完整渲染原稿；构建阶段必须对真实生成结果做逐页渲染复核。
- 参考稿的动画、音频和 3:1 超宽表现不进入生产模板。
- 参考权利证明未提供，因此只复用抽象规律，不复用原素材。

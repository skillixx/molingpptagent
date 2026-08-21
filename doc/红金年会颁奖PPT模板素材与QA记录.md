# 红金年会颁奖 PPT 模板素材与 QA 记录

## 1. 记录信息

| 项目 | 内容 |
|---|---|
| 模板 ID | `template_7` |
| 模板名称 | 红金年会颁奖 |
| 验收日期 | 2026-08-20 |
| 当前状态 | `DONE` |
| 页面比例 | 16:9 |
| 逻辑画布 | 1000 × 562.5 |
| 生产版页数 | 22 页 |
| MVP 标记页数 | 12 页 |
| 素材生成方式 | Codex 内置图片生成工具，GPT Image 2 路线 |
| 参考文件用途 | 仅参考红、黑、金配色、舞台氛围和页面类型，不复用原素材 |

本记录说明最终素材来源、提示词、模板结构、测试命令、浏览器截图和 PPTX 导出证据。开发者修改模板后，应重新执行第 5～7 章的检查。

## 2. 素材来源和版权结论

- 4 张背景和 8 张装饰图均为本项目独立生成的原创位图。
- 未从参考 PPT 中提取或复制帷幕、灯笼、奖杯、人物、证书、Logo、音频或水印。
- 素材中不包含公司 Logo、真实员工、真实证书、固定年份、生肖或可识别第三方标识。
- 背景使用 JPG；装饰使用带 Alpha 通道的 PNG。
- 项目最终素材全部位于 `backend/main_api/template/`，没有只保留在图片工具默认目录。
- 图片生成工具的默认源文件保留在 Codex 生成目录；项目只引用下表中的压缩版本。

## 3. 最终素材清单

| 文件 | 字节 | 尺寸 | 模式 | SHA-256 前 12 位 | 检查结果 |
|---|---:|---:|---|---|---|
| `template_7_asset_bg_cover_v1.jpg` | 244359 | 1920×1080 | RGB | `5768d48e0ba1` | 16:9；中央文字安全区；无文字和水印 |
| `template_7_asset_bg_content_v1.jpg` | 202092 | 1920×1080 | RGB | `a908f59738eb` | 低干扰内容背景；无文字和水印 |
| `template_7_asset_bg_section_v1.jpg` | 168705 | 1920×1080 | RGB | `019f77da430d` | 章节背景；左侧文字安全区 |
| `template_7_asset_bg_end_v1.jpg` | 166531 | 1920×1080 | RGB | `3dff421602a5` | 落幕背景；中央文字安全区 |
| `template_7_asset_stage_curtain_v1.png` | 726326 | 1200×675 | RGBA | `6afb98ad1432` | Alpha 有效；边缘完整 |
| `template_7_asset_stage_bottom_v1.png` | 351140 | 1200×675 | RGBA | `975383d0e013` | Alpha 有效；台阶完整 |
| `template_7_asset_festival_lantern_v1.png` | 735243 | 800×1200 | RGBA | `dec3b9049436` | Alpha 有效；流苏完整；无字符 |
| `template_7_asset_award_trophy_v1.png` | 688486 | 800×1200 | RGBA | `637debf3430c` | Alpha 有效；无文字和 Logo |
| `template_7_asset_award_laurel_v1.png` | 878910 | 900×823 | RGBA | `d1886c024ce2` | Alpha 有效；中心镂空 |
| `template_7_asset_award_title_frame_v1.png` | 435643 | 1200×800 | RGBA | `b3352a90b5e1` | Alpha 有效；中心无文字 |
| `template_7_asset_effect_spotlight_v1.png` | 894433 | 800×1200 | RGBA | `baf1c63eaa45` | Alpha 有效；光束边缘柔和 |
| `template_7_asset_people_frame_single_v1.png` | 515490 | 800×1200 | RGBA | `69df93f5489c` | Alpha 有效；内框透明；无人物 |

素材总计 6,007,358 字节。每张透明装饰均小于 1 MB；4 张背景均小于 250 KB。

## 4. 最终图片提示词

以下提示词均通过内置图片生成工具单独执行，一条提示词只生成一种素材。

### 4.1 主舞台背景

```text
Use case: stylized-concept
Asset type: 16:9 PowerPoint full-slide background for an annual awards ceremony cover
Primary request: an original luxurious red, black and gold awards-stage environment, symmetrical deep-red velvet curtains opening toward a dark central stage, subtle gold light rays and fine celebratory particles, polished black reflective floor, premium corporate gala atmosphere
Composition/framing: exact widescreen 16:9 landscape; keep the central 60% and upper-middle area visually quiet and dark for editable title text; decorative detail concentrated at far edges and bottom; no people
Lighting/mood: cinematic warm spotlights, elegant and restrained, high contrast
Color palette: deep crimson, near-black, antique gold
Constraints: no text, no letters, no numbers, no logos, no company marks, no zodiac animals, no watermark, no collage, no embedded frame, no certificate, fully original visual
```

### 4.2 深色内容背景

```text
Use case: stylized-concept
Asset type: 16:9 PowerPoint full-slide content background
Primary request: original premium dark annual awards ceremony background with a subtle charcoal-black textile texture, restrained deep-crimson gradient waves along the lower edge, very fine antique-gold particles and faint architectural light lines
Composition/framing: exact 16:9 landscape; central 75% and top title band must remain calm and low-detail for editable text and charts; no stage props in the central area
Lighting/mood: sophisticated, subdued, high readability
Color palette: near-black, burgundy, antique gold
Constraints: no text, letters, numbers, logos, people, trophies, zodiac symbols, watermark, collage
```

### 4.3 章节过渡背景

```text
Use case: stylized-concept
Asset type: 16:9 PowerPoint full-slide section transition background
Primary request: original dramatic red-black-gold ceremony transition scene with one sweeping crimson silk ribbon entering from the lower-left, a thin circular antique-gold halo offset to the right, sparse celebratory particles, deep black atmospheric background
Composition/framing: exact 16:9 landscape; left-center and center must provide a large quiet text-safe area; decorations stay near the perimeter
Lighting/mood: cinematic, celebratory, elegant
Color palette: deep crimson, black, warm gold
Constraints: no text, letters, numbers, logos, people, awards, zodiac symbols, watermark, collage
```

### 4.4 落幕背景

```text
Use case: stylized-concept
Asset type: 16:9 PowerPoint full-slide closing background
Primary request: original elegant annual awards ceremony closing scene, rich red curtains gently drawing inward at far sides, receding dark stage, warm golden bokeh and a soft central spotlight fading upward, premium black reflective floor
Composition/framing: exact 16:9 landscape; central 55% must be clear and dark enough for editable closing text; no people
Lighting/mood: graceful finale, warm, refined
Color palette: deep red, near-black, antique gold
Constraints: no text, letters, numbers, logos, years, zodiac animals, watermark, collage
```

### 4.5 红色帷幕

```text
Use case: stylized-concept
Asset type: reusable PowerPoint decorative cutout
Primary request: a single elegant deep-red velvet theater curtain swag with realistic folds and antique-gold trim, front-facing, complete object
Composition/framing: wide horizontal decoration, centered, generous transparent padding, no cropping
Lighting/mood: warm theatrical highlights, premium corporate gala
Color palette: crimson and antique gold
Constraints: genuinely transparent background with alpha channel; one object only; no text, letters, logos, people, watermark, shadow rectangle, border, collage
```

### 4.6 舞台台阶

```text
Use case: stylized-concept
Asset type: reusable PowerPoint decorative cutout
Primary request: a single symmetrical awards-stage bottom platform with three low red-carpet steps, polished black sides and thin antique-gold edge lights, front-facing, complete object
Composition/framing: wide low horizontal decoration, centered, generous transparent padding, no cropping
Lighting/mood: elegant ceremonial stage lighting
Color palette: deep red, black, antique gold
Constraints: genuinely transparent background with alpha channel; one object only; no text, logos, people, trophy, curtain, watermark, rectangle background, collage
```

### 4.7 红金灯笼

```text
Use case: stylized-concept
Asset type: reusable PowerPoint decorative cutout
Primary request: one refined Chinese-inspired red silk lantern with subtle antique-gold metal details and tassel, contemporary premium gala styling, complete object
Composition/framing: vertical cutout, centered, generous transparent padding, full tassel visible
Lighting/mood: warm inner glow, elegant not cartoonish
Color palette: crimson and antique gold
Constraints: genuinely transparent background with alpha channel; one object only; no characters, text, symbols, logos, zodiac animals, watermark, rectangle background, collage
```

### 4.8 金色奖杯

```text
Use case: stylized-concept
Asset type: reusable PowerPoint decorative cutout
Primary request: one original premium gold awards trophy, abstract rising flame and starless laurel-inspired silhouette on a dark-red stone base, front three-quarter view, complete object
Composition/framing: vertical product-style cutout, centered, generous transparent padding, no cropping
Lighting/mood: polished warm studio highlights, prestigious corporate gala
Color palette: brushed antique gold and deep red
Constraints: genuinely transparent background with alpha channel; one object only; no text, letters, numbers, logos, people, watermark, rectangle background, collage
```

### 4.9 金色桂冠

```text
Use case: stylized-concept
Asset type: reusable PowerPoint decorative cutout
Primary request: one complete symmetrical antique-gold laurel wreath, open at the top, refined metallic leaves, suitable for framing an award title or portrait
Composition/framing: centered front view, generous transparent padding, no cropping
Lighting/mood: polished warm studio highlights, premium ceremonial
Color palette: antique gold only
Constraints: genuinely transparent background with alpha channel; one object only; empty center; no text, letters, numbers, logos, trophy, people, watermark, rectangle background, collage
```

### 4.10 空白金色标题框

```text
Use case: stylized-concept
Asset type: reusable PowerPoint decorative cutout
Primary request: one empty ornate gold title frame for an annual awards ceremony, horizontally wide, subtle art-deco corners and thin dimensional metallic border, clean empty center
Composition/framing: centered front view, generous transparent padding, complete frame, no cropping
Lighting/mood: warm elegant highlights, premium and restrained
Color palette: antique gold with tiny deep-red accents
Constraints: genuinely transparent background with alpha channel; empty center; no text, letters, numbers, logos, people, watermark, rectangle background, collage
```

### 4.11 聚光灯

```text
Use case: stylized-concept
Asset type: reusable PowerPoint lighting-effect cutout
Primary request: one soft warm-gold theatrical spotlight beam viewed from above, a narrow luminous source widening into a subtle transparent cone with a faint floor glow, isolated effect
Composition/framing: tall vertical effect, centered, generous transparent padding, full beam visible
Lighting/mood: cinematic but subtle enough behind editable slide content
Color palette: warm gold
Constraints: genuinely transparent background with alpha channel; one effect only; no fixture, text, logos, people, objects, watermark, rectangle background, collage
```

### 4.12 单人相框

```text
Use case: stylized-concept
Asset type: reusable PowerPoint portrait-frame cutout
Primary request: one elegant single-person portrait frame for a corporate awards ceremony, vertical rounded-rectangle opening, slim antique-gold dimensional edge, small tasteful laurel accents at the lower corners, empty transparent photo opening
Composition/framing: centered front view, generous transparent padding, complete frame, no cropping
Lighting/mood: premium polished studio highlights
Color palette: antique gold with restrained deep-red accent
Constraints: genuinely transparent background with alpha channel including the inner photo opening; one frame only; no person, face, text, letters, numbers, logos, certificate, watermark, rectangle background, collage
```

## 5. 模板与代码结果

### 5.1 页面清单

| 类型 | 数量 | 说明 |
|---|---:|---|
| 封面 | 2 | 主舞台封面、桂冠聚光封面 |
| 目录 | 6 | 精确支持 2、3、4、5、6、10 项 |
| 章节过渡 | 4 | 标准、灯笼、帷幕、聚光四种构图 |
| 内容 | 8 | 2项、3项、4项、单结论、单图文、双图文、三人物、年度数字 |
| 结束 | 2 | 金框落幕、桂冠舞台落幕 |
| 合计 | 22 | `metadata.mvpSlideIds` 标记其中 12 页为 MVP |

### 5.2 槽位约定

- 文字槽使用 `textType`：`title`、`content`、`item`、`itemTitle`、`itemNumber`、`partNumber`。
- 可替换内容图使用 `imageType: "content"`。
- 背景和装饰图使用 `imageType: "decoration"`。
- 渲染器只在检测到新协议 `content/decoration` 时启用严格图片槽模式。
- 旧模板的 `pageFigure/itemFigure` 继续使用兼容逻辑，避免破坏 template_1～template_5。
- 内容图片不与文字分组，用户可以直接单击并使用“替换图片”；编号、标题、正文和项目装饰仍共享 `groupId`。

### 5.3 修改文件

- `backend/main_api/template/template_7.json`
- `backend/main_api/template/template_7.jpg`
- `backend/main_api/template/template_7_asset_*`
- `backend/main_api/main.py`
- `backend/main_api/workers/template_renderer.py`
- `backend/main_api/tests/test_template_7.py`
- `doc/红金年会颁奖PPT模板开发说明.md`
- `doc/红金年会颁奖PPT模板开发Goal.md`
- `doc/红金年会颁奖PPT模板素材与QA记录.md`

## 6. 自动化验证

### 6.1 后端

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests -q
```

结果：`382 passed in 45.33s`。

模板专项与渲染器回归：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_7.py backend/main_api/tests/test_template_renderer.py -q
```

结果：`40 passed in 0.90s`。专项测试额外覆盖字号门禁、0 张图片、年度数字语义、普通四项版式一致性、损坏 JSON、空图片地址，以及 `items`/`data.text` 两种输入在缺少内容槽位时的错误门禁。

### 6.2 前端

```powershell
npm run type-check
npm run test:unit -- --run
npm run build-only
```

结果：

- Vue/TypeScript 类型检查通过。
- `23` 个测试文件、`101` 个测试通过。
- Vite 生产构建通过。
- 构建保留项目已有的大包体告警；本任务未新增前端依赖或新代码块。

### 6.3 资源接口

- `GET /templates` 返回 `template_7`、名称“红金年会颁奖”和 `/api/data/template_7.jpg`。
- `GET /data/template_7.jpg` 返回 HTTP 200、`image/jpeg`。
- `GET /data/template_7.json` 返回 HTTP 200、`application/json`。
- 模板 JSON 为 187,061 字节，小于 1 MB；22 个页面及 312 个页面/元素 ID 全部唯一。
- 模板列表封面为 960×540、84,295 字节。
- JSON 中 Base64 图片数量为 0，WAV/WDP 引用数量为 0。
- 12 个素材文件全部被 JSON 引用，没有缺失或未引用的 template_7 素材。

## 7. 端到端 QA

### 7.1 模板选择与设备适配

检查尺寸：

- 1366×768。
- 1920×1080。
- 768×1024。
- 390×844。

结果：四种视口均无页面横向溢出。模板卡片可见，点击后类名变为 `template-card selected`，生成按钮保持可用。手机端模板列表采用单列滚动，并已滚动到 template_7 后完成选中。

截图：

- `.codex-tmp/template_7_goal/qa/template-list-1366x768.png`
- `.codex-tmp/template_7_goal/qa/template-list-1920x1080.png`
- `.codex-tmp/template_7_goal/qa/template-list-768x1024.png`
- `.codex-tmp/template_7_goal/qa/template-list-390x844.png`
- `.codex-tmp/template_7_goal/qa/template-list-390x844-template7-selected.png`

### 7.2 模板逐页检查

- 编辑器直接导入 `template_7.json` 后识别 22 页。
- 22 页均成功加载背景、装饰、文字和槽位。
- 未发现破图、异常字体、页面越界或未处理的控制台错误。
- 逐页截图：`.codex-tmp/template_7_goal/renders-final/`。
- 总览：`.codex-tmp/template_7_goal/qa/template_7_22page_final_montage.png`。

### 7.3 生成、分页、编辑和图片替换

- QA 语义输入覆盖 `cover`、`contents`、`transition`、`content`、`end`。
- 8 项内容自动拆成 2 页且两页保持同一普通文本版式；年度数字只在 `kind: metric` 时选择数字版式，最终生成 10 页。
- 单图页使用横图；三人物框使用竖图、方图、竖图，导出前后裁剪比例正常。
- 生成结果总览：`.codex-tmp/template_7_goal/qa/final-generated-montage.png`。
- 双击标题并把“年度优秀伙伴”改为“年度卓越伙伴”，页面立即显示新文本。
- 单击内容图片后出现“替换图片”按钮；替换后图片源变为新的 Base64 数据。
- 背景、人物相框、帷幕和其他装饰仍保留 `/api/data/template_7_asset_*` 地址。
- 文字反馈截图：`.codex-tmp/template_7_goal/qa/text-edit-feedback.png`。
- 图片反馈截图：`.codex-tmp/template_7_goal/qa/image-replace-feedback.png`。
- 手机端生成失败场景先显示加载反馈，失败后按钮恢复为可点击“生成PPT”，可使用同一模板重试；截图：`.codex-tmp/template_7_goal/qa/generation-retry-feedback-390x844.png`。

### 7.4 PPTX 导出与重新打开

- 导出文件：`.codex-tmp/template_7_goal/exports/template_7_final_qa.pptx`。
- 文件大小：6,221,803 字节。
- ZIP 完整性：`ZipFile.testzip()` 返回 `None`。
- OOXML 幻灯片数量：10。
- `PresentationFile.importPptx` 重新解析：10 页。
- 项目编辑器通过 PPTX 导入功能重新打开：10 页，控制台无警告和错误。
- 重新打开后右上角 `ANNUAL AWARDS` 保持单行，导出前后未出现标题换行回归。
- 重新打开后逐页截图：`.codex-tmp/template_7_goal/qa/final-reopened-renders/`。
- 重新打开总览：`.codex-tmp/template_7_goal/qa/final-reopened-montage.png`。

当前机器未安装 Microsoft PowerPoint 或 LibreOffice。演示文稿辅助 PNG 渲染脚本在该文件上无错误文本退出，因此最终视觉复核改用项目自身的 `pptxtojson` 导入链路；结构复核另由 `PresentationFile.importPptx` 完成。两条独立解析路径均识别为 10 页。

### 7.5 编辑器设备表现

- 1920×1080：完整桌面编辑器，无横向溢出。
- 768×1024：平板编辑器保留缩略图、画布和属性栏，无横向溢出。
- 390×844：自动切换为手机 PPT 预览，逐页纵向显示并保留“下载”按钮，无横向溢出。

## 8. 已知限制和后续可选优化

- 当前自动 QA 使用中性背景作为人物图片占位，不包含真实员工照片；上线真实活动前由用户自行替换。
- 模板不包含真实公司 Logo；如需品牌化，应由用户提供授权 Logo。
- 生产版 PPTX 使用多张透明 PNG，10 页 QA 导出约 6.22 MB；当前素材已满足单张透明装饰小于 1 MB 的建议值。
- 手机端是预览与下载模式，不提供完整桌面编辑工具，这是现有前端的响应式策略，不是 template_7 特例。
- 如需验证 Microsoft PowerPoint 原生兼容性，可在安装 PowerPoint 的验收机上再次打开导出物；当前已通过两条项目内解析路径。

## 9. 人工确认

自动验收状态：已通过。

人工确认状态：用户已于 2026-08-21 明确回复“确认完成”，Goal 已按闭合规则进入 `DONE`。本次闭合不包含 Git 提交、推送、PR、合并或部署。

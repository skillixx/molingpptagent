# 蓝曜星幕商务汇报 PPT 模板开发 Goal 执行提示词

> 本文保存后续开发时使用的执行提示词。本轮只编写文档，不创建 Goal，不生成素材，不修改代码，不运行测试，不启动服务。

## 使用方式

需要正式开始开发时，将下面“主执行提示词”完整发送到 `D:\moling\TrainPPTAgent` 项目任务中。

完整发送主执行提示词，表示授权创建并持续执行本文限定的本地开发 Goal，包括 9 项 GPT2 图片模板素材生成、固定数据测试和必要的本地 QA。

该授权不包含 Git 提交、推送、PR、合并、生产构建或部署。

## 主执行提示词

```text
请在 D:\moling\TrainPPTAgent 中创建并持续执行一个 Goal，完成“蓝曜星幕商务汇报”PPT 模板的 G0～G6 开发任务。

Goal objective：
将 C:\Users\sk20\Desktop\星空风格(1).pptx 的深蓝星空、青色水平光线和舞台地平线视觉语言，重建为一套包含 20 个稳定版式和 9 项原创装饰素材的 TrainPPTAgent 模板。模板必须可选择、可生成、可编辑、可换图、可导出、可重新导入并具备固定数据回归测试。G0～G6 的过程检查由测试和证据自动确认；全部通过后进入 READY_FOR_CONFIRMATION，收到用户明确确认后才执行闭合并完成 Goal。

不要设置 token_budget，除非我另行明确指定。

开始前必须完整读取并遵守：

1. AGENTS.md
2. doc\蓝曜星幕商务汇报PPT模板开发说明.md
3. doc\蓝曜星幕商务汇报PPT模板开发Goal.md
4. doc\蓝曜星幕商务汇报PPT模板开发Goal执行提示词.md
5. doc\Template.md
6. doc\PPT_Structure.md
7. backend\main_api\workers\template_renderer.py
8. backend\main_api\template_assets.py
9. backend\main_api\tests\test_template_renderer.py
10. backend\main_api\tests\test_template_assets.py
11. 与当前相邻模板相关的 JSON、规格、专项测试和必要 QA 记录

基础信息：

- 模板名称：蓝曜星幕商务汇报
- 候选模板 ID：template_23
- 参考 PPT：C:\Users\sk20\Desktop\星空风格(1).pptx
- 参考文件 SHA-256：22BA3CA2A866D7064A3FF568122FF3635BC758F9D5E87CDC5F41F23E05CF882B
- 页面比例：16:9
- 第一版范围：20 个版式、9 项装饰素材
- G6 自动检测状态：READY_FOR_CONFIRMATION
- 人工闭合状态：DEVELOPMENT_COMPLETE

一、执行原则

- 严格按 G0 → G1 → G2 → G3 → G4 → G5 → G6 顺序执行。
- G0～G6 是自动检查点，不是逐阶段人工门禁；无需等待逐阶段、逐页面、逐素材或逐测试确认。
- 唯一人工确认点位于 G6 之后。G6 全部通过时输出验收报告并等待用户明确确认，不得提前闭合 Goal。
- 每个阶段都要检查输入、实施任务、运行验证、保存证据并记录状态。
- 普通测试失败、文字溢出、素材不合格、图片裁切错误和局部兼容问题，在范围内自动诊断、修复和重验。
- G2 探针失败时自动修复和重验，满足条件后直接继续 G3，不请求人工确认。
- 涉及公共渲染能力时，先增加固定数据失败测试，再做最小修复。
- 保留用户已有修改，不覆盖无关文件，不清理未跟踪产物。
- 不执行 Git 提交、推送、PR、合并、生产构建或部署。

二、GPT2 图片模板和素材

本 Goal 的 9 项原创背景和透明装饰允许使用 GPT2 图片模板生成。

- 必须调用当时可用的图片生成技能或工具，不能用提示词或文字描述冒充图片结果。
- 工具未暴露实际模型名称时记录“工具未暴露”，不得猜测或伪造模型名称。
- GPT2 图片模板不可用时，可以使用其他授权明确的图片来源，但必须记录真实来源。
- 每项素材最多生成或重试 3 轮，达到规格和实际使用要求后停止迭代。
- 每项保存最终提示词、实际工具、实际模型或“工具未暴露”、原始输出、发布路径和检查结果。
- 图片生成授权只覆盖下面 9 项素材，不扩展到业务配图或规划外素材。

固定素材：

1. template_23_asset_bg_cover_v1.jpg，1920×1080，RGB JPEG，不超过 450KB。
2. template_23_asset_bg_content_v1.jpg，1920×1080，RGB JPEG，不超过 300KB。
3. template_23_asset_bg_section_v1.jpg，1920×1080，RGB JPEG，不超过 380KB。
4. template_23_asset_bg_end_v1.jpg，1920×1080，RGB JPEG，不超过 420KB。
5. template_23_asset_particle_field_v1.png，1600×900，RGBA PNG，不超过 800KB。
6. template_23_asset_horizon_glow_v1.png，1800×600，RGBA PNG，不超过 600KB。
7. template_23_asset_title_flare_v1.png，1800×180，RGBA PNG，不超过 350KB。
8. template_23_asset_image_halo_v1.png，1200×900，RGBA PNG，不超过 700KB。
9. template_23_asset_grid_arc_v1.png，1600×900，RGBA PNG，不超过 650KB。

素材不得包含文字、Logo、水印、人物面孔、品牌或可识别商标。透明素材必须具有真实 Alpha 通道，装饰不得干扰主要阅读区。

三、G0～G6 阶段任务

G0：预检与规格冻结

- 记录工作树、分支和用户已有修改。
- 核对参考 PPT 路径和 SHA-256。
- 扫描模板注册表和模板目录，确认 template_23 是否可用。
- ID 冲突时选择下一个可用编号，并同步规格、构建器、测试、资源和注册文件名。
- 确认字体、色板、20 个版式、9 项素材、测试入口和本地运行时。
- 创建机器可读模板规格，记录 G0 证据。

G1：9 项装饰素材

- 逐项生成或准备 4 张背景和 5 张透明装饰。
- 按开发说明检查构图、低干扰区、视觉差异和实际使用位置。
- 检查尺寸、体积、RGB/RGBA、Alpha、清晰度、安全区和来源记录。
- 每项素材至少被一个生产页面实际引用。
- 业务照片、图表、指标、标题和流程不得烘焙进装饰图。

G2：三页能力探针

- cover-horizon：验证背景、标题层级、装饰锁定、预览和 PPTX 往返。
- content-image-1：验证图片槽、横竖方图裁切、换图和装饰隔离。
- content-metrics-4：验证四指标、长标题、可编辑元素和多端预览。
- 三页必须能够导入、显示、编辑、保存重载、导出并重新导入。
- 探针失败时先增加失败测试，最小修复并重验；通过前不得扩展全部版式。

G3：20 个生产版式

必须精确生成：

cover-horizon
cover-visual
contents-2
contents-3
contents-4
contents-5
contents-6
contents-10
transition-particle-number
transition-lightline
content-focus-1
content-text-2
content-text-3
content-text-4
content-image-1
content-metrics-3
content-metrics-4
content-metrics-5
end-horizon
end-action

- 页面、元素和分组 ID 必须稳定且全局唯一。
- 标题、正文、编号、指标、标签、卡片和线条使用原生可编辑元素。
- imageType=content 只用于可替换业务图片。
- 背景和固定装饰独立锁定，换图不能覆盖装饰。
- 构建器连续执行两次应产生等价模板结构。
- 模板 JSON 不得包含 Base64 大图、本机绝对路径或缺失资源。

G4：项目集成

- 生成生产模板 JSON、模板预览图和发布素材。
- 按当前项目机制注册模板。
- 验证模板列表、静态资源、预览、编辑和导出入口。
- 不重构无关前后端代码，不修改其他模板。

G5：固定数据自动化测试

- 使用固定输入、Fake 或 Mock 和隔离环境。
- 不调用真实文本模型，不创建生产生成任务，不消耗真实文本生成 Token。
- 验证 20 个版式的 ID、类型、顺序和数量。
- 验证目录 2、3、4、5、6、10 项精确选版。
- 验证正文 2、3、4 项和指标 3、4、5 项选版。
- 验证图片裁切、替换和装饰保护。
- 验证 sourceTitle、标题限制、正文完整性和项目顺序。
- 验证 4 项长标题不会退化为 4 张单项页面。
- 验证页面增长守卫、错误输入、模板注册和资源读取。
- 只运行当前模板和实际受影响公共模块的测试。

G6：冻结候选和正式 QA

- 冻结当前候选后再生成正式证据。
- 检查 1920×1080、1366×768、768×1024、390×844 四个视口。
- 验证模板选择按钮的加载、成功、失败和重试反馈；未修改入口时只检查兼容性。
- 编辑标题和正文，替换横图、竖图和方图，并保存重载。
- 导出 PPTX，使用 PowerPoint 打开并保存副本，再重新打开或重新导入。
- 对比页面数量、文字、项目顺序、图片裁切、装饰、分组和字体结果。
- 保存 QA 截图、测试输出、PPTX、哈希、偏差和已知限制。
- 全部通过后自动把候选状态更新为 READY_FOR_CONFIRMATION，输出验收报告并等待用户明确确认。
- 收到用户明确确认后，执行闭合操作，把候选状态更新为 DEVELOPMENT_COMPLETE，并将 Goal 标记为 complete。

四、内容和语义硬性规则

- 中文使用微软雅黑，英文和数字使用 Arial。
- 页面类型和基础节点语义遵循 doc\PPT_Structure.md。
- 原始标题、正文信息和项目顺序不得丢失。
- 标题适配时保留 sourceTitle，不得简单截断或用省略号隐藏内容。
- 项目标题限制为：1 项 20 字、2 项 16 字、3 项 12 字、4 项及以上 10 字。
- 标题适配与正文分页必须分开计算。
- 4 项页面不能因为标题较长退化为 4 张单项页面。
- 文本适配必须幂等，重复执行不能持续缩小字号或改变项目顺序。
- 正文默认 16pt，必要标签不低于 12pt。
- 至少 70% 的内容区域保持低干扰。
- 不迁移参考 PPT 的动画、特殊字体、图片、Logo、水印和示例文字。

五、计划产物

- doc/template_specs/template_23.yaml
- utils/build_cyan_star_business_template.mjs
- backend/main_api/template/template_23.json
- backend/main_api/template/template_23.jpg
- backend/main_api/template/template_23_asset_*
- backend/main_api/tests/test_template_23.py
- utils/run_template_23_handler_qa.py
- utils/verify_template_23_pptx_roundtrip.mjs
- utils/verify_template_23_browser.cjs
- backend/main_api/main.py 中的模板注册，若当前仍使用该机制
- doc/assets/template_23_qa/ 中的素材记录和 QA 证据

公共渲染器默认不修改。只有新增失败测试证明必要时，才做最小修改并运行实际受影响回归。

六、阶段记录格式

每个阶段完成时记录：

[阶段] Gx：阶段名称
[状态] IN_PROGRESS / PASS / NEEDS_FIX / BLOCKED
[完成] 实际完成的文件、页面、素材或功能
[验证] 已运行的检查和真实结果
[问题] 失败、偏差、限制或阻断
[下一步] 下一个具体任务

不要用“代码已写”或“文档已写”代替实际功能和验证证据。

七、完成和交付报告

系统根据测试和证据自动确认 G0～G6 的过程结果。全部通过且验收报告完整后，将候选状态更新为 READY_FOR_CONFIRMATION，但不得将 Goal 标记为 complete。

只有收到用户明确确认验收通过后，才执行闭合操作、更新为 DEVELOPMENT_COMPLETE 并将 Goal 标记为 complete。

完成报告必须列出：

- 最终模板 ID 和 READY_FOR_CONFIRMATION 状态。
- G0～G6 各阶段状态和证据入口。
- 3 页探针和 20 页生产版式。
- 9 项素材的提示词、工具、实际模型或“工具未暴露”、路径、体积和哈希。
- 专项测试、受影响回归、四视口、编辑换图和 PPTX 往返结果。
- 新增和修改文件、失败修复、偏差和已知限制。
- 明确说明没有执行 Git 提交、推送、PR、合并和部署。

G6 自动检测完成只表示候选进入 READY_FOR_CONFIRMATION。用户明确确认后才完成 Goal 闭合并记录 DEVELOPMENT_COMPLETE。人工确认不授权提交、推送、创建 PR、合并或部署。
```

## 人工闭合提示词

检查 G6 验收报告后，如果确认候选可以闭合，可以发送：

```text
确认“蓝曜星幕商务汇报 PPT 模板开发”候选验收通过。请核对当前状态确实为 READY_FOR_CONFIRMATION，然后执行 Goal 闭合操作，记录 DEVELOPMENT_COMPLETE 并将 Goal 标记为 complete。此确认不授权 Git 提交、推送、PR、合并或部署。
```

## 继续执行提示词

如果 Goal 因正常的任务切换而暂停，后续可以发送：

```text
继续执行“蓝曜星幕商务汇报 PPT 模板开发”Goal。先读取当前 Goal 状态、开发说明、Goal 规划、执行提示词和最新阶段证据，从最后一个未完成阶段继续。不要重复已经通过且输入未变化的验证。仍然不执行 Git 提交、推送、PR、合并或部署。
```

## 只读状态检查提示词

只查看进度、不继续执行时，可以发送：

```text
只读检查“蓝曜星幕商务汇报 PPT 模板开发”Goal 的当前状态。列出已完成阶段、当前阶段、验证证据、未解决问题和下一步。不要生成图片，不要修改文件，不要运行测试，不要启动服务，不要改变 Goal 状态。
```

## 当前状态说明

- 执行提示词已经写好，但尚未发送执行。
- Goal 尚未创建。
- G0～G6 尚未开始。
- GPT2 图片模板尚未调用。
- 未修改模板代码，未运行测试，未启动服务。
- 未执行提交、推送、PR、合并或部署。

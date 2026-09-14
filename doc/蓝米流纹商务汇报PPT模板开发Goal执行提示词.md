# 蓝米流纹商务汇报 PPT 模板 G0～G9 自动执行提示词

> 这是后续开发时使用的 Goal 执行提示词。本轮只编写提示词，不执行 G0～G9，不生成素材，不修改代码，不启动服务。

## 主执行提示词

```text
在 D:\moling\TrainPPTAgent 中，连续完成“蓝米流纹商务汇报”PPT 模板的 G0～G9 阶段任务。

必须先读取并遵守以下文件：

1. AGENTS.md
2. doc\蓝米流纹商务汇报PPT模板开发说明.md
3. doc\蓝米流纹商务汇报PPT模板开发Goal.md
4. doc\蓝米流纹商务汇报PPT模板开发Goal执行提示词.md
5. doc\Template.md
6. doc\PPT_Structure.md
7. backend\main_api\workers\template_renderer.py
8. backend\main_api\template_assets.py
9. backend\main_api\tests\test_template_renderer.py
10. backend\main_api\tests\test_template_assets.py
11. template_19、template_20 的 JSON、规格、专项测试和必要 QA 摘要

模板名称：蓝米流纹商务汇报
候选模板 ID：template_21
参考 PPT：C:\Users\sk20\Desktop\创意风格 (56).pptx
参考文件 SHA-256：EE80AB40B1E168B3713E42A18EA7176C2A7AA38772E58151285A4CE2D72A543C
目标画布：1000 × 562.5，16:9
开发范围：G0～G9
开发完成状态：G8_PASS / G9_PENDING
最终交付状态：G9 自动检测通过后进入 READY_FOR_CONFIRMATION，等待人工确认

一、视觉保真要求

必须保持成品与原图和原 PPT 的视觉样式一致。原 PPT 是本模板唯一的视觉参考来源，开发者必须保持以下内容的一致性：

- 保持原 PPT 的蓝米色流体矿纹视觉语言和低饱和配色关系。
- 保持原 PPT 的 16:9 页面比例、白色内容区、深蓝标题和流纹边缘构图。
- 保持原 PPT 的封面、目录、章节、正文、图文、指标和结束页的页面节奏。
- 保持原 PPT 的标题层级、正文层级、英文小标题、编号关系和信息图密度。
- 保持原 PPT 的留白、对齐、边距、装饰方向、纹理密度和视觉重心。
- 保持封面和结束页的视觉呼应关系。
- 保持内容图片的构图位置、裁切方向、比例关系和装饰层级。
- 保持原 PPT 的整体气质，不得自由改成科技蓝、霓虹、油彩、水彩、玻璃拟态、密集卡片或其他风格。

生产素材可以替换为原创或授权明确的图片，但替换后必须保持原图或原 PPT 的视觉角色、构图方向、色彩关系、明暗层级和页面节奏一致。任何因版权、字体、编辑器兼容性或 PPTX 往返产生的偏差，都必须记录在偏差日志中，并尽可能保持原样式。

二、自动执行原则

严格按 G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7 → G8 → G9 顺序执行。无需等待逐阶段、逐页面、逐素材、逐样稿或逐测试确认。

每个阶段执行四步：

1. 检查输入。
2. 实施任务。
3. 运行当前阶段验证。
4. 记录证据并自动进入下一阶段。

普通测试失败、文字溢出、素材不合格、图片裁切错误、局部兼容问题和公共能力问题，必须先定位根因、增加必要失败测试、完成最小修复并重验。

G2 技术探针通过前不得扩展完整 MVP。G2 失败时自动修复和重验，不等待用户确认。

三、G0～G9 阶段任务

G0：预检与基线

- 检查当前工作树、分支和用户已有修改。
- 确认参考 PPT 存在，并核对 SHA-256。
- 检查 template_21 是否冲突；冲突时选择下一个可用 ID，并同步所有计划、测试、资源和注册文件。
- 确认模板渲染器、资源目录、测试入口和本地运行时。
- 输出 G0 基线记录。

G1：参考页映射和权利清单

- 审计参考 PPT 的全部 25 页。
- 每页标记为“采用、派生、重建或排除”。
- 记录图片、音频、动画、切换、字体、版权文字和示例内容的处理方式。
- 不复制源 PPTX 媒体字节到生产模板。
- 输出 reference-page-map.json、权利清单和偏差记录。

G2：三页技术探针

完成并验证：

- cover-marble-frame：验证 JSON 导入、标题编辑、标题框、装饰锁定和 PPTX 往返。
- content-text-4：验证四项密度、长标题、正文容量、项目顺序和分页。
- content-image-1：验证横图、竖图、方图裁切、图片替换和装饰保护。

三页必须能够导入、显示、编辑、保存重载和导出。固定装饰不能被业务图片替换。PPTX 导出后必须能够被项目同款解析器重新导入。

G3：规格和 9 项素材

生成或准备以下 9 项实际引用素材：

- template_21_asset_bg_cover_v1.jpg
- template_21_asset_bg_content_v1.jpg
- template_21_asset_bg_section_v1.jpg
- template_21_asset_bg_end_v1.jpg
- template_21_asset_marble_tile_blue_v1.jpg
- template_21_asset_marble_tile_ivory_v1.jpg
- template_21_asset_bottom_flow_v1.png
- template_21_asset_side_flow_v1.png
- template_21_asset_corner_flow_v1.png

模板所需的背景、裁切纹理和透明装饰可以使用 GPT2 图片模板生成。执行时使用当时可用的图片生成工具；如果工具没有暴露实际模型名称，记录“工具未暴露”，不得猜测模型名称。

每项素材必须通过格式、尺寸、RGB/RGBA、Alpha、体积、清晰度、安全区、构图方向和样式一致性检查。每项素材最多生成或重试 3 轮。不得使用 Python、SVG 路径脚本或程序化绘图生成流体装饰位图。

G4：代表性视觉样稿

完成 5 张样稿并逐页检查：

- 主封面。
- 4 项目录。
- 章节页。
- 4 项正文。
- 标准结束页。

样稿必须与原图或原 PPT 的色彩、构图、留白、安全区、标题层级、纹理方向和页面节奏保持一致。

G5：12 页 MVP

生成以下 12 个稳定页面：

- cover-marble-frame
- contents-2
- contents-3
- contents-4
- contents-5
- contents-6
- contents-10
- transition-marble-left
- content-text-2
- content-text-3
- content-text-4
- end-marble-frame

构建器必须确定性运行。连续执行两次必须得到相同 JSON。页面、元素和分组 ID 必须全局唯一。

G6：语义标注和专项测试

必须完成并验证：

- type、textType、groupId、imageType、allowedItemCounts 和 sourceTitle。
- content 图片与 decoration 装饰严格隔离。
- 目录 2、3、4、5、6、10 项精确选版。
- 正文 1、2、3、4 项选版。
- 长正文和超量项目无损分页。
- 原始标题、正文内容和项目顺序完整保留。
- 标题适配与正文分页分别计算。
- 四项页面不会因标题过长退化为四张单项页面。
- 横图、竖图、方图裁切和图片替换稳定。
- 无图输入不显示空图片槽。
- 缺失图片尺寸、多余图片、缺失资源和非法模板数据返回明确错误。

G7：18 页生产版和注册

在 MVP 基础上增加：

- cover-marble-minimal
- transition-marble-right
- content-focus-1
- content-image-1
- content-metrics-4
- end-action

生产版必须包含 2 个 cover、6 个 contents、2 个 transition、6 个 content 和 2 个 end。生成模板选择器封面，注册模板 JSON、封面和全部资源。

G8：冻结候选版本和正式 QA

冻结候选版本后一次性执行：

- 模板专项测试和受影响公共回归。
- 真实 Worker 生成五种页面类型。
- 标题和正文编辑、保存重载、内容图片替换和固定装饰保护。
- 导出失败反馈和重试入口。
- 1920×1080、1366×768、768×1024、390×844 四视口。
- PPTX 导出并使用项目同款解析器重新导入。
- 代表页面全尺寸视觉检查，并与原图或原 PPT 的样式进行对照。

G8 通过后记录 G8_PASS / G9_PENDING。

G9：最终验收与交付

自动检查冻结候选版本的以下内容：

- 页面、元素、分组和素材文件完整性。
- 9 项素材的格式、体积、Alpha、引用关系和权利记录。
- 18 页生产库存和五种页面类型。
- 专项测试、公共回归、真实 Worker、四视口、编辑换图和 PPTX 往返。
- 原图或原 PPT 样式一致性、偏差记录和已知限制。
- 证据目录、报告和文件状态完整。

G9 自动检测没有问题后，只能将状态更新为 READY_FOR_CONFIRMATION，并输出最终验收与交付报告。必须收到人工确认，才可以完成 G9、执行闭合操作并报告最终交付完成。没有人工确认时，不得标记 complete，不得报告 DONE。

四、全局硬性规则

- 必须保持原图或原 PPT 的视觉样式一致，任何样式偏差都必须记录原因和影响。
- 不复制参考 PPT 的图片、音频、动画、切换、特殊字体、Logo、水印和版权文字。
- 中文使用微软雅黑，英文和数字使用 Arial。
- imageType="content" 只用于可替换业务图片。
- imageType="decoration" 用于固定背景和装饰并锁定。
- 使用 sourceTitle 无损保存原始标题。
- 不得简单截断标题，不得丢失正文，不得改变项目顺序。
- 不得让标题适配导致多项页面退化为单项页面。
- 不得把 Base64 大图、本机绝对路径或缺失资源写入模板 JSON。
- 不得跳过测试、降低断言、删除失败用例或伪造证据。
- 不执行 Git 提交、推送、PR、合并、部署、生产备份、迁移、计费开启或回滚。
- 启动、停止或重启服务前，必须确认端口、PID、命令行、工作目录和项目归属。

五、阶段进度记录

每个阶段按以下格式记录：

[阶段] Gx：阶段名称
[状态] IN_PROGRESS / PASS / NEEDS_FIX / BLOCKED
[完成] 实际完成的文件、页面、素材或功能
[验证] 已运行的检查和真实结果
[问题] 失败、偏差、限制或阻断
[下一步] 下一个具体任务

六、最终交付报告

报告必须列出：

- 最终模板 ID、G8_PASS / G9_PENDING 或 READY_FOR_CONFIRMATION 状态。
- G0～G9 各阶段状态和实际证据。
- 三页探针、12 页 MVP、18 页生产版和页面映射。
- 9 项素材、提示词、工具、实际模型、源输出、路径、体积和哈希。
- 原图或原 PPT 样式一致性检查和偏差日志。
- 专项测试、公共回归、真实 Worker、四视口、编辑换图和 PPTX 往返结果。
- 新增和修改文件、已知限制、未授权动作和人工确认入口。
```

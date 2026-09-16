# 桃夭墨韵商务汇报 PPT 模板素材与 QA 记录

## 1. 当前候选

| 项目 | 结果 |
|---|---|
| 模板 ID | `template_22` |
| 当前候选标识 | `template_22-hotfix-be9af16783e9` |
| 当前候选 SHA-256 | `be9af16783e9b7f9916583c45addcf5739f871491b7be1d9a4e6d8a843028182` |
| 上次已确认候选 | `template_22-g8-db790bc36b0a` |
| 开发分支 | `codex/template-22-peach-ink` |
| 工作目录 | `D:\moling\TrainPPTAgent` |
| 基础提交 | `5987db70c827573769fea9eb130ff6d08ae8260e` |
| 页面库存 | 18 页 |
| 生产素材 | 9 项 |
| G0～G8 | 全部 `PASS` |
| 原 Goal 状态 | `DONE` |
| 当前热修复状态 | `HOTFIX_READY_FOR_CONFIRMATION` |
| 热修复人工确认 | `PENDING_AFTER_HOTFIX` |
| Git 交付 | 已授权提交并推送开发分支；未授权 PR、合并或部署 |

候选哈希按生产注册、正式 JSON、封面、九项素材、专项测试、机器规格和确定性构建器的文件路径与 SHA-256 联合计算。当前逐文件记录见 `doc/assets/template_22_qa/hotfix-candidate-manifest.json`；`frozen-candidate-manifest.json` 保留为原已确认候选的历史记录。

## 2. 素材记录

生产模板使用以下原创发布素材：

| 素材 | 格式 | 用途 | 结果 |
|---|---|---|---|
| `template_22_asset_bg_cover_v1.jpg` | RGB JPEG | 封面背景 | PASS |
| `template_22_asset_bg_content_v1.jpg` | RGB JPEG | 正文背景 | PASS |
| `template_22_asset_bg_section_v1.jpg` | RGB JPEG | 章节背景 | PASS |
| `template_22_asset_bg_end_v1.jpg` | RGB JPEG | 结束页背景 | PASS |
| `template_22_asset_scroll_roll_v1.png` | RGBA PNG | 卷轴装饰 | PASS |
| `template_22_asset_ink_title_frame_v1.png` | RGBA PNG | 水墨标题框 | PASS |
| `template_22_asset_ink_circle_frame_v1.png` | RGBA PNG | 水墨圆框 | PASS |
| `template_22_asset_ink_brush_band_v1.png` | RGBA PNG | 水墨笔刷横带 | PASS |
| `template_22_asset_petal_sweep_v1.png` | RGBA PNG | 桃花花瓣装饰 | PASS |

- 素材使用规划内图片生成工具首次生成后，通过裁切、缩放和压缩得到发布文件。
- 每项素材生成轮次均未超过 3 轮。
- 图片生成工具未暴露底层模型名称，记录为“工具未暴露”。
- 背景均为 RGB JPEG，透明装饰均具有真实 Alpha 通道。
- 参考 PPT 的源媒体、特殊字体、MP3、动画和转场未进入生产模板。
- 提示词、生成记录、源输出、发布文件和哈希见 `doc/assets/template_22_qa/asset-generation.json`、`image-prompts.md`、`originals/` 和 `asset-summary.json`。

## 3. 阶段证据

| 阶段 | 结果 | 主要证据 |
|---|---|---|
| G0 | PASS | `g0-baseline.json` |
| G1 | PASS | `reference-page-map.json`、`reference-rights-audit.json` |
| G2 | PASS | `probe-summary.json`、`probe-renders/`、探针编辑和 PPTX 往返文件 |
| G3 | PASS | `asset-summary.json`、`assets-contact-sheet.png` |
| G4 | PASS | `g4-sample-summary.json`、`sample-renders/sample-contact-sheet.png` |
| G5 | PASS | `g5-mvp-summary.json` |
| G6 | PASS | `g6-test-summary.json`、专项与公共回归结果 |
| G7 | PASS | `g7-production-summary.json`、`production-renders/production-contact-sheet.png` |
| G8 | PASS | `g8-summary.json`、`frozen-candidate-manifest.json` |

## 4. G8 正式验收结果

| 检查项 | 结果 | 说明 |
|---|---|---|
| 模板专项与受影响公共回归 | PASS | 96 项测试通过 |
| 前端类型检查 | PASS | `vue-tsc --build --force` 通过 |
| 生产构建确定性 | PASS | 两次构建和正式 JSON 的 SHA-256 一致 |
| 实际 Handler/Worker 链路 | PASS | 固定上游、真实处理器/渲染器/租约 Worker、临时 SQLite |
| 五种页面类型 | PASS | `cover`、`contents`、`transition`、`content`、`end` 均实际生成 |
| 文字编辑 | PASS | 封面标题和正文编辑后可保存重载 |
| 业务图片替换 | PASS | 内容图片替换成功且裁切协议保留 |
| 固定装饰保护 | PASS | 换图前后装饰元素保持不变 |
| 四视口 | PASS | 1920×1080、1366×768、768×1024、390×844 |
| JSON 保存重载 | PASS | 7 页固定验收文档及编辑内容完整保留 |
| PPTX 导出重导入 | PASS | 7 页、49 段全文、项目顺序和业务图片元素完整保留 |
| 横图、竖图和方图 | PASS | 编辑器实际依次换图；渲染器检查三种比例的居中裁切范围 |
| 跨页内容分组 | PASS | 每个 `groupId` 只属于一个页面，同组元素继续共享分组 |
| 错误路径反馈 | PASS | 缺失图片尺寸和超量行动项返回稳定 `TEMPLATE_DATA_INVALID` 错误码 |
| 模板列表与封面 | PASS | 注册唯一；封面 960×540，接口内容与候选文件哈希一致 |
| 模板选择与编辑入口 | PASS | 模板可见、可选择，编辑器入口正常 |
| 真实模型或生产写入 | 未发生 | 未调用真实文本/图片模型，未写生产队列、数据库或计费 |

浏览器证据见：

- `doc/assets/template_22_qa/viewports/`
- `doc/assets/template_22_qa/editor-renders/`
- `doc/assets/template_22_qa/browser-g8-summary.json`
- `doc/assets/template_22_qa/runtime/`
- `doc/assets/template_22_qa/template_22_g8_roundtrip.pptx`

## 5. 当前运行地址

- 模板选择：`http://127.0.0.1:5778/app`
- 编辑器：`http://127.0.0.1:5778/editor`
- 主 API：`http://127.0.0.1:6800`

当前分支以开发验收配置运行，关闭 SSO、持久化、计费和真实 Worker。主 API `/healthz`、模板列表、封面直连接口和前端代理接口已通过；`/readyz` 会因未启动 Outline、Content 和 PersonalDB 返回 503。该限制不影响本次模板候选检查，因为实际 Handler/Worker 已使用固定上游和隔离 SQLite 独立通过，并且本次验收明确禁止调用真实模型和生产数据。

## 6. 用户检查步骤

1. 打开 `http://127.0.0.1:5778/app`。
2. 找到“桃夭墨韵商务汇报”，确认封面正常并点击模板卡片。
3. 打开 `http://127.0.0.1:5778/editor` 检查编辑器入口。
4. 查看 `doc/assets/template_22_qa/production-renders/production-contact-sheet.png` 检查 18 页生产库存。
5. 查看 `doc/assets/template_22_qa/viewports/` 检查四种设备尺寸。
6. 如认可候选版本，明确回复确认开发完成；如需修改，指出页面或问题后继续当前 Goal。

用户已于 2026-09-16 明确确认当前候选开发完成，当前 Goal 可以闭合。该确认不授权自动提交、推送、创建 PR、合并或部署。

## 7. 2026-09-16 标题容量热修复

当前热修复候选为 `template_22-hotfix-be9af16783e9`，候选 SHA-256 为 `be9af16783e9b7f9916583c45addcf5739f871491b7be1d9a4e6d8a843028182`。该候选已完成受影响范围验证并获准推送开发分支，但尚未获得新的合并确认。

实际生成发现两个模板容量边界：四项正文页允许 10 个中文字，但默认行高的测算高度超过 54px 标题槽；墨圈章节页的 470px 标题框无法容纳 11 个中文字。修复保持最小字号和完整原文不变：四项正文标题行高调整为 1.05，墨圈章节标题框调整为 `left=380`、`width=540`。

新增两个公开渲染入口回归测试，先确认旧模板分别抛出 `ITEM_TITLE_TOO_LONG` 和 `TEMPLATE_DATA_INVALID`，再验证修复后完整标题、四项密度、正文顺序和章节版式均保留。模板与受影响公共回归共 98 项通过；两次生产构建和正式 JSON SHA-256 一致。原失败输入缓存重放分别通过 14→19 页和 3→4 页渲染，受影响页面视觉检查无重叠。

生产模板 JSON SHA-256 为 `8d4670e8c0ed4816def6575e728f5585007d27e7d3db739f8adaf15e5211db82`，公网资源与本地文件哈希一致，`/api/readyz` 为 200。详细证据见 `doc/assets/template_22_qa/hotfix-20260916-title-capacity.json`。已生成本地提交；尚未推送、创建 PR、合并或部署。

第一次热修复后 Worker 仍持有进程内模板缓存，日志继续显示旧的 `width=470`，因此修复文件虽然已经能从公网读取，新任务仍使用旧版式失败。最终已在任务队列为空时重新启动 Worker，清空 `PresentationTemplateRenderer._cache`；新 Worker 的创建时间晚于最终模板写入时间。

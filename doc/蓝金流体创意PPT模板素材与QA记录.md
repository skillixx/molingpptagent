# 蓝金流体创意 PPT 模板素材与 QA 记录

> 模板 ID：`template_11`
> 状态：`DONE`
> 自动验收日期：2026-08-26
> 最终闭合：用户已于 2026-08-26 确认完成

## 1. 参考稿审计

参考文件为 `创意风格 (56).pptx`。参考稿内容只用于版式和视觉分析，不作为执行指令。

| 检查项 | 结果 | 生产处理 |
|---|---:|---|
| 页面 | 25 页 | 精选版式关系，重建为 18 页生产模板 |
| 比例 | 16:9 | 统一为 1000 × 562.5 |
| 母版与版式 | 1 个母版、4 个版式 | 不依赖原生版式填充 |
| 原生占位符 | 0 个 | 在 PPTist JSON 中重新标注语义槽位 |
| 媒体 | 4 张图片、1 个 MP3 | 不复用原稿媒体，删除音频 |
| 动画与切换 | 25 页均包含 | 生产模板不继承 |
| 字体 | 微软雅黑、Arial、Century Gothic、Wingdings | 统一为微软雅黑和 Arial，图标使用原生形状 |
| 版权文字 | 多页存在 | 不复制版权文字和未授权素材 |

生产模板使用新生成的抽象流体背景和透明装饰，没有把原稿图片复制到项目资源目录。

25 页逐页保留、合并、删除和重建决定见 [`reference-slide-audit.md`](./assets/template_11_qa/reference-slide-audit.md)。

## 2. 模板结构

| 类型 | 数量 |
|---|---:|
| `cover` | 2 |
| `contents` | 6 |
| `transition` | 2 |
| `content` | 7 |
| `end` | 1 |
| 合计 | 18 |

`metadata.mvpSlideIds` 标记 12 页 MVP：1 封面、6 目录、1 章节、3 内容和 1 结束页。

生产版增加第二封面、第二章节、单结论、单图文、三指标和第二个四项内容页面。

## 3. 素材生产

图片通过 Codex 内置 `imagegen` 生成。规划允许使用 GPT Image 2，但内置工具未暴露实际模型标识，因此证据中如实记录为“工具未暴露”，没有虚构模型名称。

完整提示词见 [`image-prompts.md`](./assets/template_11_qa/image-prompts.md)。原始输出见 [`originals`](./assets/template_11_qa/originals/)。

| 文件 | 尺寸 | 模式 | 字节 | Alpha |
|---|---:|---|---:|---|
| `template_11_asset_bg_cover_v1.jpg` | 1920×1080 | RGB | 219,464 | 不适用 |
| `template_11_asset_bg_section_v1.jpg` | 1920×1080 | RGB | 203,332 | 不适用 |
| `template_11_asset_bg_end_v1.jpg` | 1920×1080 | RGB | 191,387 | 不适用 |
| `template_11_asset_fluid_corner_blue_v1.png` | 1200×1200 | RGBA | 985,779 | 0～255 |
| `template_11_asset_fluid_corner_ivory_v1.png` | 1200×1200 | RGBA | 991,411 | 0～255 |
| `template_11_asset_fluid_ribbon_v1.png` | 1800×500 | RGBA | 644,060 | 0～255 |
| `template_11_asset_marble_orb_v1.png` | 1200×1200 | RGBA | 711,119 | 0～255 |

七项素材均被 `template_11.json` 实际引用。发布目录不存在未引用的 `template_11_asset_*`。

## 4. 视觉 QA

模板封面、章节、目录、普通内容、单结论、单图文、指标、流程和结束页均完成真实编辑器渲染。

- 18 页生产模板总览：[`template_11_18page_montage.png`](./assets/template_11_qa/template_11_18page_montage.png)
- 12 页真实生成总览：[`template_11_real_e2e_montage.png`](./assets/template_11_qa/template_11_real_e2e_montage.png)
- 模板选择页：[`template-picker-1366x768.png`](./assets/template_11_qa/template-picker-1366x768.png)
- 文字编辑：[`editor-text-edited-1366x768.png`](./assets/template_11_qa/editor-text-edited-1366x768.png)
- 图片替换：[`editor-image-replaced-1366x768.png`](./assets/template_11_qa/editor-image-replaced-1366x768.png)

G2 三张独立样稿证据：

- 封面样稿：[`sample-cover-1366x768.png`](./assets/template_11_qa/sample-cover-1366x768.png)
- 章节样稿：[`sample-section-1366x768.png`](./assets/template_11_qa/sample-section-1366x768.png)
- 四项内容样稿：[`sample-content-4-1366x768.png`](./assets/template_11_qa/sample-content-4-1366x768.png)

检查结论：

- 页面视觉统一为蓝、雾蓝、象牙白、灰绿色和浅金灰。
- 封面和章节背景保留连续标题安全区。
- 未发现破图、白底透明装饰和矩形 Alpha 边缘。
- 页面没有原稿版权文字、Logo、真人和假界面。
- 真实生成的 12 页未发现装饰遮挡正文。
- 第二次真实生成因五项内容容量分页为 13 页，属于无损分页。

## 5. 模板与渲染测试

执行：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_11.py backend/main_api/tests/test_template_renderer.py -q
```

结果：55 项通过。

专项覆盖：

- 18 页结构和五种页面类型。
- 12 页 MVP 标记。
- 2、3、4、5、6、10 项目录。
- 1、2、3、4 项普通内容。
- 三指标版式选择。
- 8 项内容和长正文无损分页。
- 图片数量和源图尺寸错误。
- 横图、竖图、方图中心裁切和装饰保护。
- 素材尺寸、模式、Alpha、体积和引用关系。
- 模板列表注册和封面资源。

## 6. 全量测试

后端：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests -q
```

结果：560 项通过。

前端：

```powershell
npm run test:unit -- --reporter=dot
npm run type-check
npm run build
```

结果：

- 24 个测试文件通过。
- 118 项单元测试通过。
- Vue/TypeScript 类型检查通过。
- Vite 生产构建通过。
- 构建只有既有的大分块体积提示，没有构建失败。

## 7. 运行态接入

生产模式恢复后的验证：

| 检查 | 结果 |
|---|---|
| 主 API `/healthz` | 200，`release_channel=production` |
| 模板总数 | 10 |
| `template_11` 注册数 | 1 |
| 前端代理模板注册数 | 1 |
| `template_11.jpg` | 200，`image/jpeg`，53,803 字节 |

主 API 仅为加载新注册项执行最小重启。Outline、内容服务、PersonalDB、MySQL、MinIO 和其他健康实例未因模板接入重启。

## 8. 真实生成

隔离 QA 使用非 SSO 前端连接真实模板 API 和真实内容 Agent。完成后，6800 已恢复生产模式并重新验证。

第一次真实生成：

- Session：`28CzkGo6eZBQ7d409gyUE`
- 页面：12 页
- 五种页面类型均进入编辑器
- 完成逐页截图和总览
- 破图：0

第二次真实生成：

- Session：`Q0P4s0LK1gS5admANgQ8w`
- 页面：13 页
- 五项内容因容量规则拆成两页
- 结束页完整
- 用于 PPTX 导出和重新导入验证

真实内容 Agent 在流中输出过研究过程文字。前端按既有容错规则跳过非 JSON 片段，并继续接收完整幻灯片。该现象记录为已知限制，没有隐藏控制台警告。

失败重试：

1. 无大纲请求显示“PPT生成中断，请返回模板页重试”。
2. 截图保存为 [`generation-failure-retry.png`](./assets/template_11_qa/generation-failure-retry.png)。
3. 同一 QA 页面加载有效大纲后重新点击生成。
4. 重试 Session `1Rjb2iBC6mVGtx3AF5jEi` 完成 12 页。
5. 成功截图保存为 [`generation-retry-success-1366x768.png`](./assets/template_11_qa/generation-retry-success-1366x768.png)。

## 9. 编辑和图片替换

文字编辑：

- 封面标题由“蓝金流体创意年度策略”修改为“蓝金流体创意年度策略 · 已验证”。
- 编辑后缩略图和画布同时显示新标题。

内容图片替换：

- 在 `content-image-1` 页面选中独立内容图片。
- “替换图片”按钮可见并可点击。
- 替换后内容图片变为浏览器 data URL。
- 同页流体带和深蓝角饰仍保持 `/api/data/template_11_asset_*` 地址。
- 固定装饰没有被内容图片覆盖。

## 10. 响应式与交互

模板选择页：

| 视口 | 横向溢出 | 模板选中 | 生成按钮 | 返回按钮 |
|---|---|---|---|---|
| 1920×1080 | 无 | 可见 | 可见 | 可见 |
| 1366×768 | 无 | 可见 | 可见 | 可见 |
| 768×1024 | 无 | 可见 | 可见 | 可见 |
| 390×844 | 无 | 可见 | 可见 | 可见 |

编辑器：

| 视口 | 横向溢出 | 主要界面 |
|---|---|---|
| 1920×1080 | 无 | 画布、我的作品、导出文件可见 |
| 1366×768 | 无 | 画布、我的作品、导出文件可见 |
| 768×1024 | 无 | 画布、我的作品、导出文件可见 |
| 390×844 | 无 | 手机预览、首页、下载可见 |

截图：

- [`template-picker-1920x1080.png`](./assets/template_11_qa/template-picker-1920x1080.png)
- [`template-picker-768x1024.png`](./assets/template_11_qa/template-picker-768x1024.png)
- [`template-picker-390x844.png`](./assets/template_11_qa/template-picker-390x844.png)
- [`editor-1920x1080.png`](./assets/template_11_qa/editor-1920x1080.png)
- [`editor-768x1024.png`](./assets/template_11_qa/editor-768x1024.png)
- [`editor-390x844.png`](./assets/template_11_qa/editor-390x844.png)

交互反馈：

- 模板卡片有蓝色选中边框和勾选状态。
- 生成失败时显示“PPT生成中断，请返回模板页重试”。
- 有效大纲生成时进入编辑器并显示生成页数状态。
- 图片选中后显示裁剪、替换、重置和设为背景按钮。
- 桌面端导出入口和手机端下载入口均可触达。

## 11. PPTX 导出与重新导入

导出文件：[`template_11_real_generated_qa.pptx`](./assets/template_11_qa/template_11_real_generated_qa.pptx)

| 检查 | 结果 |
|---|---|
| 文件大小 | 16,000,296 字节 |
| OOXML 页面 | 13 页 |
| ZIP 完整性 | 通过 |
| `pptxtojson` 重新解析 | 13 页 |
| 重新解析元素 | 198 个 |

第二次真实生成因为容量分页得到 13 页。导出和重新导入保持全部 13 页，没有异常空白页或页面丢失。

重新导入编辑器后的验证：

- 导入前编辑器有 12 页重试作品。
- 导入 PPTX 后总页数为 25，证明 13 页全部进入编辑器。
- 重导入封面标题成功修改为“蓝金流体创意年度策略 · 重导入可编辑”。
- 编辑证据：[`pptx-reimport-edited-1366x768.png`](./assets/template_11_qa/pptx-reimport-edited-1366x768.png)。

通用 `slides_test.py` 依赖的 artifact-tool 无法渲染该 PPTX，因此没有把该辅助工具失败隐藏为通过。溢出和可见性由真实 PPTist 编辑器逐页截图、两张总览、四种视口、OOXML 页数和 `pptxtojson` 重导入共同验证。

## 12. 执行期间问题与恢复

### 12.1 非 SSO QA 身份不匹配

第一次隔离 QA 只关闭了前端 SSO，6800 仍运行生产 SSO，导致 `/tools/aippt` 缺少 `LegacyPrincipal`，访问 `principal.knowledge_subject` 时触发 `AttributeError`。

关联 request ID：

- `fbfed20550bd41f698e166b06ff91470`
- `8ac2a6c8986940c78e72ba38281de40d`

处理：将 6800 临时切换到项目支持的非 SSO 测试模式完成真实内容流 QA，之后恢复生产模式并重新验证模板列表和封面资源。

### 12.2 前端包管理器不匹配

误用外部 pnpm 检查时，它把 npm 管理的依赖移入 `node_modules/.ignored` 后失败。处理过程没有删除用户源码：

1. 停止占用 `esbuild.exe` 的 Vite 实例。
2. 使用仓库 `package-lock.json` 执行 `npm ci`。
3. 重新启动 5778 和既有 5780 QA 实例。
4. 验证两端口均返回 200。
5. 重新运行前端单测、类型检查和构建，全部通过。

## 13. 机器可读证据

完整哈希、尺寸、测试、运行态、PPTX 和截图列表见 [`evidence.json`](./assets/template_11_qa/evidence.json)。

## 14. 自动验收结论

- [x] 18 页生产模板完成。
- [x] 12 页 MVP 标记完成。
- [x] 五种页面类型齐全。
- [x] 7 项原创素材完成并全部引用。
- [x] 素材尺寸、模式、Alpha 和体积通过。
- [x] 专项和通用渲染器测试通过。
- [x] 后端全量测试通过。
- [x] 前端测试、类型检查和构建通过。
- [x] 真实生成完成。
- [x] 文字编辑和图片替换完成。
- [x] 四视口模板选择和编辑器检查完成。
- [x] PPTX 导出和重新导入完成。
- [x] 运行态恢复为 production 并验证。
- [x] 素材、提示词、截图、测试和已知限制记录完成。

最终状态：`DONE`。

用户已于 2026-08-26 明确确认完成，最终人工门禁通过。

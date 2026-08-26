# 清新校园教育 PPT 模板素材与 QA 记录

## 1. 记录信息

| 项目 | 内容 |
|---|---|
| 模板 ID | `template_10` |
| 模板名称 | 清新校园教育 |
| 参考文件 | `C:\Users\sk20\Desktop\创意风格 (9).pptx` |
| 参考文件 SHA-256 | `089C001CB6027278C8E1D9BA3C87301FA6503D95723D1F33255B9E3665261FAA` |
| 当前阶段 | G7：最终自动验收完成 |
| 当前状态 | `READY_FOR_CONFIRMATION` |
| 记录日期 | 2026-08-26 |

本文件只记录当前执行取得的证据。旧模板的历史测试数量、端口、截图和结论不作为 `template_10` 的完成证据。

## 2. G0 预检与基线

### 2.1 工作区

- 当前分支：`main`。
- 当前基线提交：`c06efbe docs: record AI neon template verification`。
- 用户已有未跟踪目录：`.codex-tmp/`、`.codex_tmp/`，执行期间保留不动。
- 当前新增规划文档：`清新校园教育PPT模板开发说明.md`、`清新校园教育PPT模板开发Goal.md`。
- `backend/main_api/template/` 中不存在 `template_10*` 文件。
- 主 API、测试和前端源码中没有已注册的 `template_10`。

### 2.2 服务与依赖

| 组件 | 当前证据 | 结论 |
|---|---|---|
| 前端 | `127.0.0.1:5778`，Vite Node 进程监听 | 已运行 |
| 主 API | `127.0.0.1:6800/healthz` 返回 200 | 已运行 |
| 模板接口 | `127.0.0.1:6800/templates` 返回 200 | 已运行 |
| 模板静态资源 | `template_9.jpg` 返回 200、`image/jpeg` | 基线正常 |
| Outline Agent | `127.0.0.1:10001/.well-known/agent.json` 返回 200 | 已运行 |
| Content Agent | `127.0.0.1:10011/.well-known/agent.json` 返回 200 | 已运行 |
| 持久 Worker | 存在 `backend.main_api.workers.main` 进程 | 已运行 |
| MySQL | `trainppt-mysql` 容器运行，主机 `SELECT 1` 成功 | 已运行 |
| MinIO | `trainppt-minio` 容器运行，端口 19000/19001 | 已运行 |

当前健康实例不重启。G7 前重新盘点，只启动当时实际缺失的最小服务集合。

### 2.3 测试基线

执行命令：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/main_api/tests/test_template_9.py backend/main_api/tests/test_template_renderer.py -q
```

结果：`56 passed in 4.14s`。

## 3. G1 参考模板审计

### 3.1 文件结构

项目现有 `pptxtojson` 导入库成功解析全部 25 页，逻辑尺寸约为 959.875 × 540.125，共识别 464 个展开后元素。

| 检查项 | 数量 | 处理结论 |
|---|---:|---|
| 幻灯片 | 25 | 建立逐页映射，筛选为 12 页 MVP 和 18 页生产版 |
| 母版 | 10 | 不直接复用，只作为视觉参考 |
| 版式 | 48 | 归并为五种项目页面类型 |
| 主题 | 11 | 收敛为一套绿色教育主题 |
| 原生页面占位符 | 0 | 在 PPTist 中重新标注语义槽 |
| 图片 | 11 | 不发布原稿图片，使用原创素材或内容图片槽 |
| 图表 | 3 | 按 `layoutKind: metrics` 重建 |
| SmartArt | 1 | 使用 PPTist 原生形状重建 |
| 嵌入工作簿 | 3 | 删除，不发布 |
| MP3 | 1 | 删除，不发布 |

原稿使用多套中英文字体并在几乎每页包含动画。生产版统一使用微软雅黑和 Arial，不继承复杂动画。

### 3.2 版权与来源处理

- 原稿的校园照片、卡通人物、音频和非标准字体授权未被当前文件证明。
- 生产模板不复用这些媒体，只保留颜色、层级和构图关系。
- 封面儿童群像、树叶、草坡、校园涂鸦和用品装饰使用原创生成素材。
- 内容照片不固化为装饰，使用 `imageType: content` 由 Agent 或用户替换。
- 所有生成素材必须保存提示词、工具实际暴露的模型信息、原始输出和人工检查结果。
- 不生成校名、校徽、Logo、真实人物、证书、假数据或可被误认为真实证据的截图。

### 3.3 逐页处理结论

| 参考页 | 处理结论 |
|---|---|
| 1 | 重建主封面 `COV-01`，使用原创树冠、草坡和儿童群像 |
| 2 | 提取目录关系，扩展为 `DIR-02/03/04/05/06/10` |
| 3、9、15、20 | 归并为 `SEC-01` 和 `SEC-02` |
| 4 | 重建为 `CNT-04` |
| 5～8 | 精选四项层级，删除英文占位和重复布局 |
| 10 | 重建为 `CNT-03` |
| 11、14 | 重建为 `CNT-MET-03`，不复用嵌入图表 |
| 12～13 | 归并为普通四项内容 |
| 16 | 提取单结论结构 `CNT-01` |
| 17～19 | 提取第二个四项构图 `CNT-04B` |
| 21 | 作为单结论长文本参考，超量正文由渲染器分页 |
| 22、24 | 与四项内容页合并，避免重复 |
| 23 | 使用普通 `title/items` 表达四步流程 |
| 25 | 重建结束页 `END-01`，删除来源文字和原媒体 |

## 4. 页面范围

### 4.1 12 页 MVP

`COV-01`、`DIR-02`、`DIR-03`、`DIR-04`、`DIR-05`、`DIR-06`、`DIR-10`、`SEC-01`、`CNT-02`、`CNT-03`、`CNT-04`、`END-01`。

### 4.2 18 页生产版新增

`COV-02`、`SEC-02`、`CNT-01`、`CNT-IMG-01`、`CNT-MET-03`、`CNT-04B`。

## 5. 素材生产记录

| 文件 | 生成方式 | 原始输出 | 发布路径 | 检查状态 |
|---|---|---|---|---|
| `template_10_asset_bg_cover_v1.jpg` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_bg_cover_v1-original.png` | 1920×1080，RGB，156,557 字节 | 通过 |
| `template_10_asset_bg_section_v1.jpg` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_bg_section_v1-original.png` | 1920×1080，RGB，264,776 字节 | 通过 |
| `template_10_asset_bg_end_v1.jpg` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_bg_end_v1-original.png` | 1920×1080，RGB，221,199 字节 | 通过 |
| `template_10_asset_leaf_canopy_v1.png` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_leaf_canopy_v1-original.png` | 1800×400，RGBA，436,261 字节 | 通过 |
| `template_10_asset_grass_wave_v1.png` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_grass_wave_v1-original.png` | 1800×420，RGBA，236,032 字节 | 通过 |
| `template_10_asset_children_group_v1.png` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_children_group_v1-original.png` | 1600×700，RGBA，1,032,484 字节 | 通过 |
| `template_10_asset_school_doodles_v1.png` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_school_doodles_v1-original.png` | 1920×1080，RGBA，360,867 字节 | 通过 |
| `template_10_asset_corner_supplies_v1.png` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_corner_supplies_v1-original.png` | 1200×1200，RGBA，770,617 字节 | 通过 |
| `template_10_asset_brush_accent_v1.png` | 内置 `image_gen`，模型标识未暴露 | `originals/template_10_asset_brush_accent_v1-original.png` | 1800×500，RGBA，437,668 字节 | 通过 |

透明 PNG 的 Alpha 极值均为 0～255。最终提示词见 [`image-prompts.md`](./assets/template_10_qa/image-prompts.md)，原始输出保存在 `doc/assets/template_10_qa/originals/`，九项发布素材均被 `template_10.json` 实际引用。

## 6. G2～G5 模板实现

- 正式模板：`backend/main_api/template/template_10.json`，177,849 字节。
- 模板列表封面：`template_10.jpg`，960×540、RGB、79,121 字节。
- 生产版共 18 页：2 个封面、6 个目录、2 个章节、7 个内容页、1 个结束页。
- `metadata.mvpSlideIds` 精确包含 12 页。
- 生产模板含 317 个元素，页面 ID 和元素 ID 全部唯一。
- 图片使用 `/api/data/`，不包含 Base64 大图、本机路径和临时目录。
- 内容图片槽独立于文字分组，使用 `imageType: content`、`strictImageCount` 和 `requireSourceDimensions`。
- 固定素材使用 `imageType: decoration` 并锁定。
- 模板已在 `backend/main_api/main.py` 注册，隔离 API 返回唯一 `template_10`，封面返回 `image/jpeg`。
- 18 页总览：[`template_10_18page_montage.png`](./assets/template_10_qa/template_10_18page_montage.png)。

语义 MVP 使用生产渲染器生成 12 页，覆盖五种页面类型、三指标、单图文和 8 项分页。8 项正文拆为两页且顺序不变；固定装饰保持项目资源地址。

## 7. G6 自动化测试

| 范围 | 结果 |
|---|---|
| `test_template_10.py`＋通用渲染器 | 53 项通过 |
| 全部模板相关测试 | 177 项通过，8.25 秒 |
| `backend/main_api/tests` 全量 | 521 项通过，54.97 秒 |
| 前端类型检查、单测、构建 | 未运行；本轮未修改前端源码 |

专项测试覆盖页面结构、MVP 标记、目录与内容容量、指标选版、长正文、8 项分页、0/1 张内容图、独立图片槽、中心裁切、素材规格、注册和旧模板回归。

## 8. G7 真实持久任务

最终模板版本的真实 Worker 任务：

| 项目 | 结果 |
|---|---|
| Task ID | `335b9ad5-12f7-42c8-bf64-d2e9d665dccf` |
| Presentation ID | `1ff40c57-4281-4e8f-9be5-8c6c9800930c` |
| 状态 | `succeeded` |
| 进度 | 100% |
| 尝试次数 | 1 |
| 错误码 | 无 |
| 页数 | 12 |
| 页面类型 | cover 1、contents 1、transition 3、content 6、end 1 |
| 固定装饰 | 21 个，全部保持 `template_10_asset_*` 地址 |

真实作品总览：[`template_10_real_e2e_montage.png`](./assets/template_10_qa/template_10_real_e2e_montage.png)。

## 9. 编辑、换图和失败重试

- 真实生成副本标题修改为“人工智能支持下的校园学习创新·编辑验收”，显式保存后重新加载仍存在。
- 内容图片通过真实“替换图片”按钮换为 Data URL，保存并重新加载后仍存在。
- 换图后 20 个固定装饰全部保持项目资源地址。
- 图片槽最初与文字共用 `groupId`，编辑器只显示多选样式；已定位并修复为独立图片槽，并新增专项断言。
- 隔离 QA 关闭对象存储后，导出历史显示失败提示和“刷新”按钮；本地 PPTX 导出仍成功。
- 证据：[`editor-text-edited-1366x768.png`](./assets/template_10_qa/editor-text-edited-1366x768.png)、[`editor-image-replaced-1366x768.png`](./assets/template_10_qa/editor-image-replaced-1366x768.png)、[`export-archive-retry.png`](./assets/template_10_qa/export-archive-retry.png)。

## 10. 响应式检查

| 视口 | 模板页 scroll/client | 编辑器 scroll/client | 模板选中 | 生成/返回 | 保存/导出 |
|---|---:|---:|---|---|---|
| 1920×1080 | 1920/1920 | 1920/1920 | 通过 | 可见 | 可见 |
| 1366×768 | 1366/1366 | 1366/1366 | 通过 | 可见 | 可见 |
| 768×1024 | 768/768 | 768/768 | 通过 | 可见 | 可见 |
| 390×844 | 390/390 | 390/390 | 通过 | 可见 | 可见 |

平板使用编辑器顶部下载入口；手机进入专用 PPT 预览并提供“下载”按钮。四种视口均无横向溢出，模板卡片选中、生成、返回、保存和导出入口均可触达。

## 11. PPTX 导出与重新导入

| 文件 | 字节 | 页数 | SHA-256 |
|---|---:|---:|---|
| `template_10_mvp_qa.pptx` | 9,585,074 | 12 | `35d82680b14492b21da23d735fb11ae9cbc58b4891443417df80724c79cc33b1` |
| `template_10_real_editor_qa.pptx` | 8,140,355 | 12 | `8ea660338359fc84c5656bb2ed12f1ce6d803ca2d9e94aec71039f0f1d2c3c9d` |

两个文件均由真实编辑器导出，并使用项目同款 `pptxtojson` 重新导入。重新导入后页数、标题、正文和图片均存在；真实编辑版本保留“编辑验收”标题。

## 12. 最终自动审计

机器可读证据：[`evidence.json`](./assets/template_10_qa/evidence.json)。

最终审计结果：

- 18 页生产结构和 12 页 MVP 标记通过。
- 9 项素材尺寸、模式、体积、Alpha 和引用关系通过。
- 模板注册、封面、README 入口和专项测试通过。
- 14 项要求截图全部存在。
- 真实任务、编辑、换图、失败重试、四种视口和 PPTX 往返通过。
- 状态更新为 `READY_FOR_CONFIRMATION`。

已知限制：

- 内置 `image_gen` 未暴露实际模型标识，按事实记录为“工具未暴露”。
- 隔离 QA 未启用对象存储，因此导出历史加载失败；界面提供刷新重试，本地 PPTX 导出成功。
- 提交、推送、PR、合并和部署属于独立发布流程，不作为 G0～G7 自动验收的一部分；实时状态以 Git 与远端仓库记录为准。

## 13. 生产模板可见性故障与恢复

用户截图显示生产模板页只有 `template_1`～`template_9` 中已启用的 8 个模板，没有“清新校园教育”。

确认的失败路径：

1. 生产 6800 `/templates` 返回 8 项，不含 `template_10`。
2. 隔离 6802 `/templates` 返回 9 项，包含唯一 `template_10`。
3. `backend/main_api/main.py` 已包含注册项，但生产 6800 进程启动于 2026-08-25 13:42，注册代码修改于 15:39。
4. 主 API 没有热重载，因此生产前端 5778 继续显示旧进程内存中的模板列表。

恢复操作：

- 只停止并重启生产 6800 主 API，前端、Worker、两个 Agent、MySQL 和 MinIO 均保持运行。
- 首次启动暴露根 `.env` 的生产 `RELEASE_COMMIT` 不是有效 40 位提交哈希；没有修改 `.env`，只为新进程注入当前提交 `c06efbeb91c03b5051f7485c3d26e46817590f93`。

恢复证据：

- 6800 `/healthz` 返回 200，`release_channel=production`。
- 6800 `/templates` 返回 9 项，`template_10` 恰好 1 项。
- 5778 `/api/templates` 返回 9 项，`template_10` 恰好 1 项。
- 5778 `/api/data/template_10.jpg` 返回 200、`image/jpeg`、79,121 字节。
- 主机数据库 `SELECT 1` 成功，10001/10011 Agent 卡返回 200，Worker PID 集合未变化。

已经打开的模板页面仍保留重启前获取的列表，需要刷新页面后才会显示新模板。

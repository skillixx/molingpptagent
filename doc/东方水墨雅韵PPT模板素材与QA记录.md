# 东方水墨雅韵 PPT 模板素材与 QA 记录

> 模板 ID：`template_12`
> 当前状态：`DONE`
> 记录日期：2026-08-27
> 参考文件：`中国风格(01).pptx`

## 1. G0～G1 基线与参考稿审计

- 工作区存在既有 `.codex-tmp/`、`.codex_tmp/` 和 `doc/assets/template_10_qa/originals/` 未跟踪内容，均保留不动。
- `template_12` 在执行前未被正式模板占用。
- 前端 5778、主 API 6800、隔离 API 6802、Worker 9100 均返回 HTTP 200。
- `trainppt-mysql` 和 `trainppt-minio` 容器保持运行，没有重启健康实例。

参考稿机器审计：

| 项目 | 结果 |
|---|---|
| 页面 | 21 页 |
| 画布 | 720×405，16:9 |
| 图片元素 | 36 |
| 文本元素 | 31 |
| 形状元素 | 62 |
| 组合元素 | 16 |
| 母版 / 版式 | 1 / 11 |
| 包内媒体 | 25 |
| 嵌入字体文件 | 11 |
| 图表 / SmartArt / 嵌入对象 | 0 / 0 / 0 |

字体审计发现多种方正书法字体和叶根友字体。生产模板不依赖参考稿嵌入字体，动态文字统一使用项目稳定字体。

参考稿媒体包含水墨山水、折扇、印章、圆形框景和月夜素材。由于授权来源不明，生产模板全部使用本次生成的原创素材。

审计证据：

- `.codex-tmp/template_12_goal/reference-audit/reference-summary.json`
- `.codex-tmp/template_12_goal/reference-media-montage.png`

## 2. G2 原创素材

生成方式：Codex 内置 `imagegen`。实际模型标识未暴露，记录为“工具未暴露”。

完整提示词见 [`image-prompts.md`](./assets/template_12_qa/image-prompts.md)。

| 素材 | 尺寸 | 模式 | Alpha | 字节数 | 结果 |
|---|---:|---|---|---:|---|
| `template_12_asset_bg_cover_v1.jpg` | 1920×1080 | RGB | — | 177779 | 通过 |
| `template_12_asset_bg_section_v1.jpg` | 1920×1080 | RGB | — | 149209 | 通过 |
| `template_12_asset_bg_end_v1.jpg` | 1920×1080 | RGB | — | 128824 | 通过 |
| `template_12_asset_mountain_band_v1.png` | 1800×550 | RGBA | 0～255 | 703480 | 通过 |
| `template_12_asset_brush_accent_v1.png` | 1800×420 | RGBA | 0～255 | 346210 | 通过 |
| `template_12_asset_folding_fan_v1.png` | 1400×900 | RGBA | 0～255 | 1029515 | 通过 |
| `template_12_asset_ink_circle_v1.png` | 1200×1200 | RGBA | 0～255 | 822541 | 通过 |
| `template_12_asset_seal_red_v1.png` | 512×512 | RGBA | 0～255 | 138700 | 通过 |

人工检查：

- 三张背景均保留可编辑标题安全区。
- 透明素材没有白色矩形底板。
- 正式素材没有文字、数字、Logo、水印、真实公章或可识别真人。
- 第一版红印章因存在近似字形被淘汰，未发布。
- 发布目录只保留 8 项被 `template_12.json` 实际引用的素材。

## 3. G3～G5 模板结构与视觉

当前产物：

- `backend/main_api/template/template_12.json`
- `backend/main_api/template/template_12.jpg`
- `backend/main_api/template/template_12_asset_*`
- `utils/build_chinese_ink_template.mjs`

结构检查：

| 项目 | 结果 |
|---|---|
| 画布 | 1000×562.5 |
| 总页数 | 18 |
| 页面类型 | cover 2、contents 6、transition 2、content 7、end 1 |
| MVP 标记 | 12 页 |
| 页面 ID | 全部唯一 |
| 元素 ID | 全部唯一 |
| 素材引用 | 与 8 项发布素材集合完全一致 |
| JSON 体积 | 小于 1MB |

静态视觉检查：

- 18 页总览已生成并检查。
- 封面、目录、章节、单结论、2～4 项内容、单图文、指标、替代四项和结束页均可读。
- 未发现破图、素材拉伸、明显文字越界或装饰覆盖正文。
- 第一页最终截图已生成 960×540 RGB JPEG 模板封面。

证据：

- `doc/assets/template_12_qa/renders/slide-01.png` ～ `slide-18.png`
- `doc/assets/template_12_qa/renders/template_12_18page_montage.png`
- `doc/assets/template_12_qa/renders/template_12_semantic_qa_montage.png`

## 4. G4～G6 自动验证

- 生产渲染器已根据真实语义生成 12 页 QA 文档。
- `test_template_12.py` 最终结果：`39 passed`。
- 全部模板测试最终结果：`255 passed`。
- 后端完整测试最终结果：`599 passed`。
- 已验证精确 MVP ID、六种目录容量、1～4 项内容、指标选版、8 项分页、长正文、缺槽失败、未使用组清理、内容图与装饰隔离、三种图片比例裁切、资源规格和 API 注册。

## 5. G7 真实生成、编辑与多设备 QA

最终真实持久任务：

| 项目 | 结果 |
|---|---|
| Task ID | `da618952-248a-4031-9391-ed6a2d1516f8` |
| Presentation ID | `385b93ff-ed5f-4a81-8b35-d5a31056093b` |
| 状态 | `succeeded`，进度 100% |
| 尝试次数 | 2；首次 Agent 请求失败后自动重试成功 |
| 最终页数 | 10 |
| 装饰图片 | 20，全部为 `template_12_asset_*` |

编辑器 QA：

- 标题编辑已真实保存到数据库。
- 内容图片已替换为 Data URL，22 个固定装饰仍保留项目资源地址。
- 1920×1080、1366×768、768×1024、390×844 四种视口均无横向溢出。
- 模板卡片选中、生成和返回按钮可见；返回按钮已真实导航到大纲页。
- 导出历史关闭时显示清晰失败状态，刷新按钮已真实点击，重试提示保持可见。
- 两个 PPTX 均通过编辑器同款 `pptxtojson` 解析：MVP 12 页，真实任务 10 页。
- MVP PPTX 已通过项目 UI 重新导入隔离草稿，导入后标题可再次编辑，图片和可编辑元素存在，控制台无错误。

PPTX 证据：

| 文件 | 页数 | 字节数 | SHA-256 |
|---|---:|---:|---|
| `template_12_mvp_qa.pptx` | 12 | 11751770 | `b7ebbdc50af70d601262f65e90c34c7317e8baf529a22f343a67056a87ee2989` |
| `template_12_real_editor_qa.pptx` | 10 | 11053329 | `a8be5c70290f2af3d5ebfe9023ca188ddbe355d1640712183e74a80b822b653d` |

长期保存路径：`doc/assets/template_12_qa/exports/`。`.codex-tmp` 中的副本仅用于自动化脚本运行，不作为唯一交付位置。

## 6. G8 最终审计

- 正式 6800 API 和 5778 前端代理均唯一公开 `template_12`。
- 正式封面接口返回 960×540 JPEG。
- 持久 Worker 已重载最终模板，真实章节页包含半透明宣纸安全底板。
- `.codex-tmp/template_12_goal/final_audit.py` 已通过。
- `doc/assets/template_12_qa/evidence.json` 状态为 `READY_FOR_CONFIRMATION`。

## 7. 当前已知限制

- 内置图片生成工具未暴露实际模型标识，因此不能确认实际模型名称。
- 隔离 QA 关闭归档存储时，导出历史和归档接口返回 404；界面提供刷新重试，本地 PPTX 导出成功。该错误不来自模板。
- 最终真实任务第一次 Agent 请求失败，任务系统自动重试并在第二次尝试成功；历史错误码保留用于审计。
- UI 重导入在隔离的 12 页 QA 草稿上追加 12 页，因此界面显示 24 页；导入后的新增标题、图片和元素可以继续编辑。
- 未提交、推送、创建 PR、合并或部署。

## 8. 最终人工确认

- G0～G8 自动验收全部通过。
- 用户已明确回复“确认完成”。
- Goal 状态更新为 `DONE / complete`。

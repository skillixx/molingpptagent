# 深蓝霓虹城市项目策划 PPT 模板 G8 执行报告

## 1. 结论

`template_24` 已完成 G0～G8 的本地开发和自动验收，状态为 **`G8_PASS / G9_PENDING`**。当前候选为 **`template24-g8-f1fdf1cdaaa0`**。以上为 G8 验收时状态；用户现已回复“确认完成”，G9 已完成确认归档，详见[G9 闭合记录](./深蓝霓虹城市项目策划PPT模板G9闭合记录.md)。

本报告的阶段编号依据用户实际发送的执行提示词：G1 包含素材生产、G3 包含 MVP、G5 为专项测试、G6 为生产注册、G7 为功能 QA、G8 为最终核验。早期规划中的不同阶段划分不再作为执行依据。

## 2. 交付物

| 产物 | 当前结果 | 文件 |
|---|---|---|
| 正式模板 | 18 个版式，1000 × 562.5 | [template_24.json](../backend/main_api/template/template_24.json) |
| MVP | 12 个基础版式 | [mvp.json](./assets/template_24_qa/mvp.json) |
| 技术探针 | 封面、四项正文、单图文 3 页 | [probe.json](./assets/template_24_qa/probe.json) |
| 选择器封面 | 来自实际编辑器封面截图 | [template_24.jpg](../backend/main_api/template/template_24.jpg) |
| 9 项装饰素材 | 4 张背景、2 张纹理、3 张真实透明 PNG | [素材和完整提示词](./assets/template_24_qa/asset-generation.json) |
| 构建器 | 支持 probe、mvp、production；重复构建字节一致 | [构建器](../utils/build_neon_city_project_template.mjs) |
| 机器规格 | 页面库存、颜色、字体、图片语义和素材尺寸 | [template_24.yaml](./template_specs/template_24.yaml) |
| 模板注册 | 主 API 中唯一注册 template_24 | [main.py](../backend/main_api/main.py) |
| 专项测试 | 32 项城市模板测试 | [test_template_24.py](../backend/main_api/tests/test_template_24.py) |
| 总览 | 18 页实际编辑器截图合成 | [生产版总览](./assets/template_24_qa/production-verified/contact-sheet.png) |
| PPTX 验证稿 | 18 页，包含编辑与换图验收内容 | 本地 `doc/assets/template_24_qa/production-verified/roundtrip.pptx`（不随 Git 提交） |

生产版类型数量：2 个封面、6 个目录、2 个章节、6 个内容页、2 个结束页。业务图片使用 `imageType: content`；背景和装饰使用 `imageType: decoration`，与业务分组隔离。

## 3. 阶段结果

| 阶段 | 结果 | 证据 |
|---|---|---|
| G0 | PASS：源文件哈希、候选 ID 与项目入口核对完成 | [基线](./assets/template_24_qa/g0-baseline.json) |
| G1 | PASS：25 页映射，9 项素材实际生成，尺寸、格式和 Alpha 核验 | [页面映射](./assets/template_24_qa/reference-page-map.json)、[素材记录](./assets/template_24_qa/asset-generation.json) |
| G2 | PASS：三页探针编辑、换图、保存重载及项目重导入 | [探针证据](./assets/template_24_qa/probe-verified/summary.json) |
| G3 | PASS：12 页 MVP 与确定性构建；MVP 为生产版的精确子集 | [构建结果](./assets/template_24_qa/determinism-summary.json) |
| G4 | PASS：五张代表样稿包含在实际编辑器逐页检查中 | [18 页总览](./assets/template_24_qa/production-verified/contact-sheet.png) |
| G5 | PASS：32 项专项 + 72 项受影响回归，共 104 项通过 | [JUnit 结果](./assets/template_24_qa/tests.xml) |
| G6 | PASS：18 页生产版、9 项引用资源和选择器封面注册一致 | [运行入口检查](./assets/template_24_qa/runtime/runtime-summary.json) |
| G7 | PASS：实际 Worker 领取并完成隔离任务，产出覆盖五类页面的 7 页文稿 | [Worker 结果](./assets/template_24_qa/real-handler-summary.json)、[生成文稿往返](./assets/template_24_qa/worker-output-verified/summary.json) |
| G8 | PASS：当前候选字节、接口响应、测试和导出证据交叉核验 | [G8 汇总](./assets/template_24_qa/g8-summary.json)、[冻结清单](./assets/template_24_qa/frozen-candidate-manifest.json) |
| G9 | 已获用户“确认完成”的确认 | 已归档闭合记录，未执行 Git 交付 |

G2 早期发现的封面越界、正文小字号、纹理遮挡业务图片，以及阶段选版兼容问题，已增加失败测试并修正。最终证据以 `probe-verified`、`production-verified` 和冻结清单为准；早期 `g2-browser` 文件只保留作过程记录。

## 4. 内容完整性和往返验证

- 目录容量 2、3、4、5、6、10 项以及 11 项分页验证通过。
- 1～4 项正文与 8 项正文验证通过；长原题在正文中完整保留，8 项样例仍为两张四项页。
- 长正文样例的全文和项目顺序验证通过，没有截断尾部内容。
- 四指标数值来自固定输入，未被项目编号覆盖；缺失值返回明确错误。
- 行动结束页 0～3 项验证通过。
- 横图、竖图、方图的源尺寸、居中裁切和装饰保护验证通过。
- 在编辑器修改标题与正文、换图后，导出 JSON 并在新页面导入，完整 slides 数据一致。
- 18 页生产版与 7 页 Worker 输出均经过实际编辑器导出 PPTX、项目实际导入函数重新导入；逐页全文和图片数量保留，业务图片槽位位置误差在验证容差内。
- 注入一次 PPTX 写出失败后，编辑器显示“导出失败”，加载状态复位；恢复写出后重试成功。失败未被记为成功下载。

## 5. 素材生成记录

9 项图片均实际调用内置 `image_gen` 生成，每项调用 1 次，没有超出最多 3 轮的约定。工具未暴露底层模型名称，记录为 **“工具未暴露”**，不声称已经证明使用了某个具体模型。

原始输出保存在 `doc/assets/template_24_qa/originals/`；完整提示词、工具原始文件路径、规范化后的资源尺寸、源图与成品哈希及实际引用页均记录在素材清单。部分背景原始尺寸约为 1672 × 941，成品按约定规范化为 1920 × 1080；不将规范化尺寸冒充模型原生输出尺寸。

正式文件位于 `backend/main_api/template/template_24_asset_*`。仅复用生成图进行机械尺寸与格式处理，没有复制源 PPTX 媒体，没有生成规划外业务图片。

## 6. 验收环境和实际限制

| 项目 | 实际方式 |
|---|---|
| 前端 | 当前工作区 Vite 开发服务，`http://127.0.0.1:5778` |
| 模板与静态资源 API | 当前 `main.py` 的本地 test 配置，`http://127.0.0.1:6800`；不读取生产 `.env`，不连接生产数据库 |
| 选择器身份 | 浏览器登录身份夹具；模板列表、封面、JSON 和资源由真实本地 API 返回 |
| Worker | 真实任务租约、PersistentTaskWorker、处理器、模板渲染器；固定上游响应，临时隔离 SQLite 与捕获型作品仓库 |
| 文本模型 | 未调用；本报告不声称完成了在线文本模型、外部 Agent 或生产计费验收 |
| 编辑保存 | 本地 JSON 导出与新页面真实导入，不涉及云端作品写入 |
| 设备 | 前端源码未修改，按规划未扩大四视口整改；桌面与手机早期探针截图仅作补充观察 |

PPTX 重新导入保留全文、图片和槽位；编辑器的字体主题、字重与部分细线显示可能发生变化。本任务不承诺逐像素一致，也没有声称已在 PowerPoint 桌面应用中完成打开、保存验收。

本地测试 API 不提供生产登录。直接访问编辑器若进入登录失败页，不能据此判断模板损坏；可先查看总览、模板 JSON 与导出验证稿。生产 SSO、生产持久化、远程部署和全站 UI 整改均未纳入本次完成结论。

## 7. 复核与闭合

可复核脚本：

- [浏览器编辑、换图与导出重导入](../utils/verify_template_24_browser.cjs)
- [模板列表与选择状态](../utils/verify_template_24_runtime.cjs)
- [隔离 Worker 验证](../utils/run_template_24_handler_qa.py)
- [G8 最终核验与候选清单](../utils/finalize_template_24_qa.py)

G8 历史验收状态保留为 `G8_PASS / G9_PENDING`；当前状态已更新为 `G9_COMPLETE`，人工确认及归档记录见 G9 文档。提交、推送、PR 创建、合并、部署及生产操作仍需覆盖对应动作的授权。

# template_21 远程提交与合并审查

日期：2026-09-14。

## 结论

原有三个 P1 合并阻塞项已经按用户要求修复。独立复审未发现本次修复仍有明确阻塞项。
干净 LF 检出完整回归已通过，当前代码与离线验收层面建议可以合并到 main；实际合并仍待用户授权。
本次仅提交和推送功能分支，不合并 main，不部署或重启运行服务，不调用真实模型。

## 最新修复验收

代码候选：`9dfbc66f0d441839a31de730529edf3c90c5b302`。

- 生成收尾：仅接受本次 Controller 核对计划页数、推进页码、生成数量与页型后发出的完成证明，仍等待 Runner 正常结束。普通最终回复、错误、取消、缺少证明或部分计划不能冒充成功。
- 行动结束页：独立原生文字槽，0～3 项自动或显式选版可达，标题与正文按顺序保留，超过上限明确报错。
- 四指标：接入 metrics 版式协议，标签、实际数值、说明分别填充；支持 0、百分数、负值与旧式 title/text。上游已归一化的长原题保留在说明中，不混入数值。空说明不再连带删除整组指标。
- 指标页沿用白色内容平面，避免正文压在深蓝流纹上；没有关闭溢出或分页保护。

| 最新检查 | 结果 |
| --- | --- |
| Windows 工作区完整后端回归 | 1195 passed，2 failed，3 条依赖弃用警告 |
| 两项失败 | 仍为下文 template_19/20 的既有 LF/CRLF 字节比较差异 |
| 当前候选受影响测试 | 188 passed |
| 真实 ADK Runner/Loop/Controller 联测 | 固定 Writer，无模型调用；2 页计划仅执行 1 轮失败，2 轮完成 |
| 前端全量 Vitest / vue-tsc | 142 passed / PASS |
| 四视口 | 1920×1080、1366×768、768×1024、390×844，指标页和行动页检查通过 |
| 编辑换图、JSON 保存重载 | PASS，固定装饰保留，未写真实作品 |
| 项目原生 PPTX 导出重导入 | 8 页；编辑标题、指标数值及行动文字完整保留 |
| 干净 LF 检出回归 | 1197 passed，3 条依赖弃用警告；未跳过测试、未修改历史模板 |

固定样本覆盖封面、目录、章节、四项正文、四指标、业务图片、行动结束与普通结束。
浏览器认证为模拟响应，真实 API 写请求全部阻止。截图只含固定测试文案，位于 `assets/template_21_qa/blocker-fixes/`。
导出物保存在本地 `output/template21-blockers-qa/`，不上传数据库、用户原 PPT 或日志。

可复现命令：

```powershell
python -m pytest backend/main_api/tests backend/slide_agent/test_adk_agent_executor.py backend/slide_agent/test_generation_utils.py backend/slide_agent/test_generation_completion_integration.py backend/slide_agent/test_ppt_writer_validation.py -q
npm --prefix frontend run test:unit
npm --prefix frontend run type-check
python utils/verify_template_21_blockers.py output/template21-blockers-qa
# 使用已有本地测试前端、已安装 Playwright 和 Chrome；必要时用 PLAYWRIGHT_PACKAGE_PATH 指向包目录。
node utils/verify_template_21_browser.cjs output/template21-blockers-qa
```

没有执行真实模型生成或生产部署验收。实际合并与部署仍需分别获得用户授权。
干净检出关闭了 Git 的自动换行转换，复用了已安装的前端依赖；源代码与候选提交一致，未使用本地未跟踪 QA 文件补齐测试。

## 初次审查历史记录（整改前）

以下问题、测试计数和证据限制保留为整改前记录；最新状态以上方表格为准。

基线：`2179a1070a9875b40334f13bd72577307a137b7c`，审查时与远程 main 一致。
分支：`codex/template-21-generation-fixes`。

## 提交范围

- template_21 注册、18 个生产版式、3 页探针/12 页 MVP 构建能力。
- 9 项发布素材、旧封面兼容资源、新缩略图及蓝白封面 v2。
- 中文封面、目录、正文、结束页的容量与行高修复及回归测试。
- 已生成作品的默认封面旧地址读取兼容，不批量修改数据库或用户换图。
- 正文 Agent 正常结束时发送终态的修复、终态日志及模拟事件测试。
- 原始规划文档和机器规格。它们描述目标，不是当前完整通过验收的证据。

未提交历史模板 18～20 的未跟踪 QA、源 PPT、日志、数据库、浏览器会话、环境配置或本地导出物。
本机 NO_PROXY 启动配置未写入仓库；部署时仍需确认 localhost/127.0.0.1 请求不走外部代理。

## 当前验证

| 检查 | 结果 |
| --- | --- |
| 后端 main_api 测试及正文 Agent 执行器/生成工具/校验测试 | 1155 passed，2 failed，3 个依赖弃用警告 |
| 两个失败的归属 | template_19/20 JSON 构建字节比较，LF 与 CRLF 不同；相关文件与远程 main 的 JSON 内容相同 |
| 前端 Vitest 全量 | 26 个测试文件，142 passed |
| 前端 vue-tsc | PASS |
| 前端 Vite 本地隔离目录构建 | PASS，有既有大包体积警告；未部署 |
| git diff --check | PASS |

上述通过数不能替代需求验收。下列独立输入复现仍发现功能问题。

## 阻止合并的问题

### P1：生成收尾仍可能把未完成计划标为 completed

`backend/slide_agent/adk_agent_executor.py:100-107,168-170` 以任意一次最终输出加 Runner 正常耗尽判断成功，
没有核对 `slides_plan_num`、`current_slide_index` 与已生成内容数量。
实际 LoopAgent 存在 200 次迭代上限，耗尽次数也会正常返回，不代表计划已完成。

独立审查使用真实 ADK Event / A2A TaskUpdater 和模拟 Runner / session 离线复现：
`plan=10 generated=1 final=completed`。无网络、模型、真实任务或计费调用。

合并前应要求可验证的计划完成状态或明确的 Controller 成功信号，并覆盖部分输出后正常 EOF 的反例。
不能仅以“已有页面”作为成功条件。现有错误/取消/空事件测试没有覆盖此分支。

### P1：行动结束页丢失行动信息

需求要求结束页支持 0～3 个行动项。构建器的 `end-action` 与普通结束页使用同一函数，
没有行动项槽位，也没有相应选版约束。

固定输入：`type=end`，`data.variant=action`，`data.items=["First action", "Second action"]`。
实际结果：渲染成功但选为 `end-marble-frame`，两项行动信息都没有出现在成品文本中。

合并前应补齐行动版式和选版/数量契约，并验证 0～3 项完整保留、超过上限明确报错。
不能通过删除规格或忽略输入来消除这个问题。

### P1：四指标版式未接入语义选版

构建器创建了 `content-metrics-4`，但没有声明公共渲染器使用的 metrics 版式协议。

固定输入：`type=content`，`data.layoutKind=metrics`，四个包含 title/value/text 的指标项。
实际结果：`TEMPLATE_DATA_INVALID`，上下文 `layout_kind=metrics`。

合并前应接入指标版式契约及数值/说明字段填充，并验证四指标可达、普通正文不会误选。

## 证据限制

- 9 月 11 日旧冻结版本之后，模板文字位置、容量、行高和背景都已发生变化。
  旧 G8/G9 文件和 SHA256 不能视为当前版本完整验收通过。
- 最近封面版本兼容已在真实编辑器配合模拟旧作品响应验证，不会触发模型或写真实作品。
- 本次没有新调用收费模型，没有重新执行当前版本完整四视口、编辑换图与 PPTX 往返。
  合并前还需对最终修复候选版本完成相应验收。
- 不自动创建 PR，不合并 main，不部署，不开启计费。

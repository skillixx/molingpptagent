# TrainPPTAgent 积分闭环一次性 Goal 提示词

> 用途：创建一个持续 Goal，依次完成 BG01-BG07。
> 执行依据：[TrainPPTAgent 积分闭环 Goal 阶段开发计划](./TrainPPTAgent积分闭环Goal阶段开发计划.md)
> 技术依据：[TrainPPTAgent 对接墨灵积分技术需求与阶段规划](./TrainPPTAgent对接墨灵积分技术需求与阶段规划.md)

## 使用说明

把下面整段内容作为一次 Goal 的目标提示词。该 Goal 会在每个阶段完成后提交并推送一次、输出总结、压缩恢复上下文，然后自动继续下一阶段。

生产迁移、部署、服务重启、真实扣分、处理历史持有单、历史补偿、打开计费和扩大灰度不属于自动授权范围。执行到这些边界时必须暂停并取得本次明确授权；获得授权后继续同一个 Goal。

## 一次性 Goal 提示词

```text
创建并持续执行一个 Goal：完成 TrainPPTAgent 墨灵积分扣除生产闭环。

工作仓库：D:\molinggithub\TrainPPTAgent
只允许修改 TrainPPTAgent；不得修改 D:\molingproject\molin。

权威文档按以下顺序读取：
1. molin_docs/TrainPPTAgent积分闭环Goal阶段开发计划.md
2. molin_docs/TrainPPTAgent对接墨灵积分技术需求与阶段规划.md
3. molin_docs/TrainPPTAgent计费策略契约.md
4. molin_docs/app/billing-integration-spec.md

总目标：严格按 BG01 -> BG02 -> BG03 -> BG04 -> BG05 -> BG06 -> BG07 顺序，完成资产入口权益绑定、服务端会话、预占、生成、结算、失败释放、不确定结果对账、非生产集成、生产预部署、真实应用 UAT 和灰度验收。

执行原则：
1. 开始时读取 Goal 计划的状态块、当前 Goal 卡和最近完成记录，并检查 git status、当前分支、远程引用和最近提交。
2. 保留工作区已有修改，不重置、不清理、不覆盖、不暂存其他任务文件。
3. 第一次执行时，在不丢失当前修改的前提下创建或切换到 codex/trainppt-billing-closed-loop；后续阶段始终沿用该分支。
4. 一次只实施 current_goal。当前 Gate 未通过，不得开发下一 Goal，也不得提前标记 completed。
5. 代码遵循仓库现有架构；非显而易见的业务、并发和安全规则使用简洁中文注释。涉及前端时必须兼顾 1440、1024、768、390 四档屏幕，所有按钮都有明确反馈。
6. 权益只能来自墨灵可信启动票据并由服务端固化；缺少 entitlement_id 时计费任务必须 fail closed，禁止按 user_id + product_id 猜测或回退到其他资产。
7. 每个计费任务必须遵守 reserve -> 生成 -> settle/release 的单终态约束；不确定结果进入 billing_pending，并使用原 hold_id 对账，禁止重新 reserve。
8. 自动化测试、Mock、非生产集成、平台真实受理、余额变化、应用端到端和生产灰度证据必须分级报告，不得互相替代。
9. 每个 Goal 完成开发后，运行该阶段专项测试和必要的全量回归；检查迁移、git diff、敏感信息和未跟踪文件。
10. 验证通过后，把完成内容、测试命令与结果、证据等级、外部动作、遗留风险和下一 Goal 写入 Goal 计划的“Goal 完成记录”，并推进状态块。
11. 每个 Goal 只创建一个 Goal 级提交，格式为 type(billing): BGxx 中文摘要；只暂存该 Goal 文件。
12. 每个 Goal 完成时将当前分支推送到 origin，并核对本地 HEAD 与远程分支提交一致。提交或推送失败时不得宣布完成或进入下一 Goal。
13. 每次推送后向我总结：阶段结果、测试证据、提交哈希、远程分支、真实外部影响、遗留风险和下一 Goal。
14. 每次总结后压缩上下文，只保留仓库分支、当前 Goal、已过 Gate、最近提交、测试基线、外部状态、未授权事项、风险和下一条命令；然后自动继续下一个依赖已满足的 Goal，不要求我逐阶段重复发消息。
15. 不更新 Codex 长期 memory 文件。上下文压缩写入仓库 Goal 文档和 Git 历史；除非我明确要求更新长期 memory。

Git 授权：
- 我授权你为 BG01-BG07 的阶段成果创建 Goal 级提交，并推送到 origin/codex/trainppt-billing-closed-loop。
- 该授权不包括强制推送、覆盖远程历史、合并 main、删除分支、创建发布、部署生产或修改墨灵仓库。
- 远程出现未知新提交或冲突时停止，保留现场并报告，不得覆盖。

必须暂停等待我明确授权的边界：
- 连接生产数据库执行迁移或其他写操作；
- 部署、重启生产服务或切换生产流量；
- 任何真实积分预占、结算、释放或补偿；
- 处理既有 42 积分活动持有单或历史错误权益扣分；
- 将 BILLING_ENABLED 打开、扩大白名单或全量启用；
- 合并到 main 或创建正式发布。

真实扣分规则：
- 每次真实 UAT 前重新确认 user_id、asset_id、entitlement_id、product_id、单次金额和累计上限。
- 此前针对资产 990206 的“最多 3 积分”授权不自动延续到本 Goal。
- 任一身份不一致、金额超限、重复持有单、余额异常或终态不确定时立即停止新的写入。

阻塞规则：
- 能在仓库内解决的测试或代码问题继续修复，不要只停在分析。
- 缺少外部环境或人工授权时，将当前 Goal 标记 blocked，记录已完成证据、阻塞条件和恢复后的第一步。
- 不得用 Mock 或直连接口成功冒充应用端真实闭环。

总完成条件：BG01-BG07 全部通过；每个阶段都有已验证的远程提交和总结；生产应用成功、失败释放、异常对账、监控、灰度和回滚均有真实证据。达到后才把 Goal 标记 complete，并给出最终发布总结和仍需人工确认的事项。
```

## 中断后继续提示词

```text
继续 TrainPPTAgent 积分闭环 Goal。
读取 molin_docs/TrainPPTAgent积分闭环Goal阶段开发计划.md 的状态块、最近完成记录和当前 Goal 卡，核对本地 HEAD 与 origin/codex/trainppt-billing-closed-loop，然后从第一个未完成验收项继续。保留已有修改，仍按每 Goal 测试、更新文档、单提交、单次推送、总结和上下文压缩的规则执行。
```

## 只检查状态提示词

```text
只读检查 TrainPPTAgent 积分闭环 Goal 状态，不修改代码、Git 或外部系统。报告当前 Goal、已通过 Gate、本地与远程提交是否一致、测试基线、生产计费和 Worker 状态、阻塞项、真实积分影响及下一步。
```

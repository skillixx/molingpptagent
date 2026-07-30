# TrainPPTAgent 积分非生产联调验收报告（BG04）

> 状态：开发验证完成，Gate C4 仍处于 verification
> 联调日期：2026-07-30
> 应用仓库：`D:\molinggithub\TrainPPTAgent`
> 工作分支：`codex/trainppt-billing-closed-loop`

## 1. 环境与边界

| 项目 | 当前证据 | 结论 |
|---|---|---|
| 墨灵上游 | 墨灵仓库 `infra/CLAUDE.md` 将 `8.130.9.163:8080` 标识为测试服务器，服务端使用 `infra/.env.test` | 可作为非生产协议联调目标 |
| TrainPPTAgent 本地模式 | 未跟踪私有配置使用 `APP_ENV=test`、隔离 SQLite `0008`、测试对象存储，API/前端/Agent/Worker 均在本地运行 | 本地开发实例身份清晰；`BILLING_ENABLED=false`，不会产生新计费动作 |
| 内部鉴权 | `moling_auth_preflight` 返回 `status=accepted` | Token 与 IP 主闸只读预检通过 |
| 写入授权 | 已明确批准 BG04 测试服真实写入，最多消耗 1 积分 | 授权已执行完毕并达到消耗上限，后续不得再增加 `quota_used` |
| 历史持有单 | 目标权益当前 `quota_reserved=42` | 作为联调前基线保留，不处理、不补偿；本轮必须保证增量预占归零 |

本报告不记录内部令牌、登录票据、完整响应正文或其他凭据。测试服真实写入也属于外部积分动作，仍须遵守人工授权门。

## 2. 目标作用域

| 字段 | 值 |
|---|---:|
| `user_id` | `479` |
| `asset_id` | `990206` |
| `entitlement_id` | `990306` |
| `product_id` | `73` |
| 单次金额 | `1` |
| 本阶段计划实际消耗上限 | `1` |

任何字段不一致、余额异常、出现新活动持有单或终态不确定时，停止后续写入。不得切换权益、换幂等键重试或处理历史 `42` 积分持有单。

## 3. 联调矩阵

| 编号 | 场景 | 证据等级 | 状态 | 当前证据或待办 |
|---|---|---|---|---|
| C4-01 | 内部 Token/IP 主闸 | 非生产真实只读 | 通过 | `status=accepted` |
| C4-02 | 用户商品权益列表 | 非生产真实只读 | 通过 | 返回 3 条权益，包含 `user_id=479`、`entitlement_id=990306` |
| C4-03 | 指定权益余额 | 非生产真实只读 | 通过 | `usable=true`，已用 `2052`，预占基线 `42` |
| C4-04 | 权益不归属 | 非生产真实只读 | 通过 | 使用错误用户查询目标权益，被 `MolingAuthenticationError` 拒绝 |
| C4-05 | 错误内部 Token | 非生产真实只读 | 通过 | 被 `MolingAuthenticationError` 拒绝 |
| C4-06 | 一次性票据与资产权益绑定 | 测试平台 + 本地隔离应用 | 通过 | 测试应用入口临时切到本地，票据被消费且隔离 Session 固化 `479/15/73/990306`；入口随后恢复 |
| C4-07 | `reserve -> settle` | 非生产真实写入 | 通过 | `hold_id=840`，结算 1；已用 `2052 -> 2053`，预占 `42 -> 42` |
| C4-08 | `reserve -> release` | 非生产真实写入 | 通过 | `hold_id=841`，释放后已用保持 `2053`，预占 `42 -> 42` |
| C4-09 | 余额不足 | 非生产真实写入 | 待测试数据 | 需要平台方提供余额不足且归属正确的测试权益，禁止在高余额目标上构造超大请求 |
| C4-10 | 超时与同键恢复 | 本地故障注入 + 非生产真实写入 | 部分通过 | 本地行为已由 BG03 覆盖；真实写入均为明确终态，未主动制造不确定持有单 |
| C4-11 | Worker 重启恢复 | 本地隔离应用 | 通过 | Worker 停止期间任务持久入库；新 Worker 启动后认领并生成 5 页，任务和作品成功终态；可控失败同步作品 `failed` |
| C4-12 | 双边流水与新增持有单归零 | 双方非生产证据 | 部分通过 | 平台确认 `840=settled/1`、`841=released/0`、新增 holding 为 0；本地任务计费操作为 0，但尚无应用真实计费任务的双边映射 |

## 4. UAT 工具加固

`backend/main_api/tools/real_billing_uat.py` 已在本阶段增加：

- 显式选择 `settle` 或 `release`，确认文本绑定终态动作；
- 结算后要求已用额度增加指定金额，释放后要求已用额度不变；
- 两种动作都要求 `quota_reserved` 回到执行前基线；
- 余额不足、鉴权失败等明确拒绝直接失败，不伪装成未知预占；
- 终态响应不确定时保留原 `hold_id` 与对应动作幂等键，不执行另一终态动作；
- 预占成功后的明确终态拒绝返回 `finalization_rejected`，保留 `hold_id` 和动作键供人工核对；
- 命令返回非零时不得自动开始下一笔真实写入。

本阶段还补齐了此前阻断应用闭环的真实 Worker 处理器：

- 复用现有大纲 A2A Agent 和正文 A2A Agent，不引入新的模型供应商接口；
- 将 Agent 结构化页面转换为编辑器可读取的基础可编辑文档；
- 使用当前任务 `lock_token`、租约有效期、owner 和作品状态共同围栏结果写入；
- 只读产物探测供 Worker 崩溃恢复和计费对账复用；
- 普通任务进入最终失败或死信时同步作品状态，避免作品永久停留在“生成中”；
- 生成已落库但结算待确认时，产物探测仍能识别非空文档并继续原 `settle`，不会误走释放；
- 配置模板和生产 Compose 仅补处理器工厂引用，`TASK_WORKER_ENABLED=false` 与 `BILLING_ENABLED=false` 未改变。

应用入口同时完成以下收口：

- 墨灵 SSO 构建的模板页调用 `POST /api/presentations`，不再直接调用旧正文流式接口；
- 文件知识库、网络搜索和模板选择随持久任务冻结；
- 网络失败重试复用同一客户端幂等键；
- 创建后进入作品状态页，自动轮询 `generating` / `billing_pending`，就绪后加载服务端作品；
- 非 SSO 本地开发路径仍保留旧流式模式，不改变现有离线调试能力。

当前渲染器提供稳定的基础文字版可编辑页面，保留 `template_id`，但尚未复刻前端随机模板排版、图表和图片素材替换。该限制不影响积分事务验证，但必须在产品视觉验收中单独评估，不能把基础渲染等同于最终模板品质。

专项测试：

```text
python -m pytest backend/main_api/tests/test_real_billing_uat.py -q
11 passed

python -m pytest backend/main_api/tests/test_billing_policy.py \
  backend/main_api/tests/test_moling_client.py \
  backend/main_api/tests/test_real_billing_uat.py \
  backend/main_api/tests/test_billing_orchestrator.py \
  backend/main_api/tests/test_billing_reconciliation.py -q
79 passed, 1 warning

python -m pytest backend/main_api/tests/test_presentation_handler.py \
  backend/main_api/tests/test_task_worker.py \
  backend/main_api/tests/test_billing_orchestrator.py \
  backend/main_api/tests/test_billing_reconciliation.py -q
40 passed, 1 warning

python -m pytest backend/main_api/tests -q
320 passed, 1 warning

npm run test:unit
94 passed

npm run build
vue-tsc 与 Vite production build 通过

npx eslint <本阶段前端变更文件>
0 error，2 条既有 warning

python -m compileall -q backend/main_api
通过；production/UAT Compose YAML 解析通过
```

当前机器没有 Docker CLI，因此没有执行 `docker compose config` 或镜像构建；YAML 解析不能替代实际 Compose 验证。自动化结果属于本地 Fake Client 证据，不替代 C4-07、C4-08 的非生产真实写入。

## 5. 真实写入与平台对账

| 动作 | 预占键 | 终态键 | 平台终态 | 额度结果 |
|---|---|---|---|---|
| 结算 | `uat:ppt:990206:20260730072041:08f0be3cca1b:reserve` | `uat:ppt:990206:20260730072041:08f0be3cca1b:settle` | `hold_id=840`、`settled_amount=1` | `quota_used 2052 -> 2053`，`quota_reserved 42 -> 42` |
| 释放 | `uat:ppt:990206:20260730072058:5d396cc827bd:reserve` | `uat:ppt:990206:20260730072058:5d396cc827bd:release` | `hold_id=841`、`settled_amount=0` | `quota_used 2053 -> 2053`，`quota_reserved 42 -> 42` |

平台测试数据库只读复核：两笔均归属 `entitlement_id=990306`、`user_id=479`，`settled_at` 已设置；这两个 `hold_id` 中 `holding` 数量为 0。目标权益最终为 `quota_total=10000`、`quota_used=2053`、`quota_reserved=42`、`status=active`。

真实影响仅为结算笔消耗 1 积分，已达到本次授权上限。释放笔未增加已用额度；历史 42 积分预占未处理。

## 6. 浏览器入口与 Session 证据

使用已登录测试账号检查墨灵“我的资产”页面：

- 资产列表显示 `asset_id=990206`、`product_id=73`、套餐 `85`、状态“生效中”；
- 权益额度显示 `entitlement_id=990306`、`asset_id=990206`、类型 `ppt_ai_credits`、商品 `73`、已用 `2052 / 10000 credits`、状态“可用”；
- 墨灵测试应用 `15` 的 `access_url` 曾临时切换到本地前端；入口生成的一次性票据在受控脚本中按 `479/15/73/990306` 声明瞬时匹配并由本地 `/enter` 消费，未写入文件或报告；
- 本地隔离 SQLite 的最新 Session 为 `user_id=479`、`app_id=15`、`product_id=73`、`entitlement_id=990306`，证明资产级权益已由服务端固化；
- 本地 `/enter` 返回 302 并签发独立 HttpOnly Session Cookie；本地计费操作表仍为 0；
- 验证完成后测试应用 `access_url` 已恢复为原公网地址并再次只读确认，浏览器资产页已释放控制并保持用户原页面。

公网 TrainPPTAgent 数据库此前只读检查显示 `alembic_version=20260723_0007`，`app_sessions` 没有 `entitlement_id`。该结果只用于证明公网实例不能承接本轮资产级验收；本阶段没有迁移、重启或修改公网实例。

本轮通过临时本地入口补齐了测试平台票据到隔离 0008 Session 的协议证据，但计费保持关闭，因此仍不能替代应用真实计费任务的 C4 双边流水验收。

## 7. 本地开发验收补充

- 隔离数据库从空库迁移到 `20260730_0008`；测试 MySQL 因账号无建库权限仅做只读身份检查，未修改既有 `ppt_ai_app`。
- API `/readyz` 的 Outline、Content、PersonalDB、database、storage 和 moling 探针全部为 `up`。
- 真实 A2A 持久任务成功生成 5 页，任务 `succeeded/completed`、作品 `ready`、`billing=null`。
- Worker 完全停止期间任务仍可由 API 持久入库，新 Worker 启动后恢复并生成 5 页。
- 可控非法持久输入进入任务与作品 `failed`，未调用外部模型。
- 测试对象存储写、读、摘要校验、删全部通过，无本轮对象残留。
- 三个任务期间本地计费操作始终为 0；墨灵只读复核保持 `quota_used=2053`、`quota_reserved=42`。

## 8. 后续执行顺序

1. 取得余额不足且归属正确的测试权益；禁止在高余额权益上构造超大预占。
2. 取得新的应用计费 UAT 积分授权后，临时开启隔离实例计费，执行应用 Worker 的成功、释放和真实超时同键对账。
3. 逐任务归档应用任务 ID、幂等键、`hold_id` 与平台流水，并确认新增活动持有单归零。
4. 部署当前按用户要求暂缓；需要时再使用 `docker-compose.uat.yml` 和运行手册，不得迁移或重启公网生产实例。

## 9. 当前结论

BG04 的代码开发和本地无积分验收已完成：真实测试票据在隔离 0008 Session 固化 `990306`，持久任务成功、失败、Worker 重启恢复和测试对象存储均通过，且没有新增积分消耗。此前平台真实结算、释放和持有单核对证据仍有效。余额不足测试数据、真实超时同键对账以及应用计费任务双边流水仍缺少授权或测试资源，因此 Gate C4 保持 `verification`，不能进入 BG05；当前代码可以形成远程开发基线，但不得写成 C4 全部验收完成。

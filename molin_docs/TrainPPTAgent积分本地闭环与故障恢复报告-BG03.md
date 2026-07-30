# TrainPPTAgent 积分本地闭环与故障恢复报告 BG03

> 验证日期：2026-07-30
> 阶段结论：通过
> 证据等级：本地 SQLite + Fake Moling 自动化
> 外部影响：无真实扣分、无生产迁移、无部署

## 1. 闭环结论

本地计费链路满足：

```text
任务创建时固化指定权益
  -> 单次 reserve
  -> Agent 执行并探测持久化结果
  -> 有结果 settle / 无结果 release / 无法判断 billing_pending
  -> 使用原 hold_id 和原幂等键对账
  -> settled、released 或 manual_required 单终态
```

普通任务 Worker 在 reserve 完成前不能领取收费任务；对账 Worker 不具备 reserve 接口，因此不能在恢复过程中产生第二次预占。

## 2. 场景证据矩阵

| 场景 | 自动化证据 | 关键断言 |
|---|---|---|
| 正常成功 | `test_success_reserves_before_agent_persists_then_settles_once` | reserve 先于 Agent；结果持久化后只 settle 一次 |
| 额度不足 | `test_insufficient_reserve_fails_without_agent_call` | 不调用 Agent，不产生持有单 |
| 平台原子拒绝 | `test_platform_atomic_60005_does_not_switch_entitlement_or_call_agent` | 不切换其他资产 |
| 明确失败 | `test_agent_or_persistence_failure_releases_once` | 使用原持有单只 release 一次 |
| reserve 超时 | `test_write_timeout_enters_billing_pending_without_guessing_or_compensation` | 不生成、不换权益、不补偿 |
| settle 超时 | `test_settle_timeout_never_releases_or_reports_success` | 不错误 release，不提前报告成功 |
| release 超时 | `test_release_timeout_freezes_task_without_retrying_release` | 保持释放方向，等待对账 |
| 结果探测异常 | `test_persistence_probe_error_freezes_reserved_task_for_reconciliation` | 不猜测 settle/release |
| 双 Worker reserve | `test_concurrent_prepare_only_calls_platform_reserve_once` | 仅一个认领者调用平台 |
| 本地提交失败 | `test_platform_success_but_local_terminal_commit_failure_is_frozen` | 保存原 hold，进入待对账 |
| Agent 超时 | `test_agent_timeout_probes_then_releases_without_retrying_agent` | 探测后释放，不重复生成 |
| 幂等重放 | `test_settle_timeout_already_applied_replays_same_key_and_recovers` | 重用原 settle key |
| 重启和退避 | `test_restart_preserves_exponential_backoff_and_stops_at_max_retries` | 重试次数和时间持久化 |
| 对账并发 | `test_concurrent_reconciliation_claim_has_only_one_winner` | 只有一个 Worker 获胜 |
| 慢调用租约 | `test_slow_platform_call_is_not_replayed_before_inflight_lease` | 在途调用不会并行重放 |
| 最后一次认领后崩溃 | `test_crash_after_final_claim_eventually_converges_to_manual_review` | 自动转人工，不永久悬挂 |
| 未知 reserve | `test_unknown_reserve_never_replays_and_requires_manual_review` | 禁止第二次 reserve |
| 重复创建请求 | `test_concurrent_billing_request_creates_one_task_and_operation` | 一个任务、一个计费操作 |

## 3. 可观测性

新增 `BillingOperationalSnapshot`，只提供以下聚合计数：

- `pending_count`：待处理或在途对账操作；
- `stale_hold_count`：超过在途租约且仍持有 `hold_id` 的操作；
- `manual_required_count`：已停止自动写入、等待人工处理的操作；
- `error_count`：带稳定错误分类的操作。

对账 Worker 最多按 `base_interval_seconds` 周期输出一次 `billing_reconciliation_snapshot`。有陈旧持有单、人工介入或错误时使用 warning，否则使用 info。

日志只包含四个计数，不包含：

- 用户 ID；
- 资产或权益 ID；
- `hold_id`；
- reserve/settle/release 幂等键；
- 平台原始错误正文或 Token。

测试 `test_worker_logs_only_aggregate_billing_snapshot` 已冻结该边界。

## 4. 测试结果

```text
专项：计费编排、对账、作品幂等、任务 Worker
结果：74 passed, 1 warning

主 API 全量：backend/main_api/tests
结果：306 passed, 1 warning
```

唯一警告为既有 Starlette `httpx` TestClient 弃用提醒。

## 5. Gate C3 结论

C3 通过：成功、明确失败、结果不确定、并发、重启、平台超时和本地提交失败均有自动化证据；同一任务不会双预占、双结算或同时结算和释放；对账可使用原动作收敛或转人工；关键积压可通过脱敏聚合日志观察。

本结论不等于非生产墨灵集成通过，也不等于生产计费可开启。下一阶段 BG04 必须使用双方认可的非生产环境完成真实协议联调。

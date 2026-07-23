# TrainPPTAgent 墨灵预付计费策略契约

> 状态：`T18_FROZEN`
> 当前开关：`BILLING_ENABLED=false`
> 边界：本文件冻结权益解析和金额策略；T16实现收费任务幂等，T17实现reserve/settle/release，T18实现未知终态对账。

## 1. 金额决策

- O-01按推荐默认关闭为“运营配置项”：整套PPT预占读取`PPT_GENERATION_RESERVE_POINTS`，仓库不提供生产数字、不写死金额。
- O-02按推荐默认关闭为“第一版固定积分”：成功结算读取`PPT_GENERATION_SETTLE_POINTS`，必须为正整数且不得超过预占积分。
- 只有显式`BILLING_ENABLED=true`才强制两个值存在；在真实运营值未确认期间保留空值并维持`false`，因此当前代码不能产生真实计费。
- 平台接口仍以decimal字符串传输；本地整数配置在调用边界转为精确`Decimal`，禁止float。

## 2. 权益选择矩阵

按以下顺序处理`GET /api/internal/user-entitlements`返回的候选：

1. 只接受服务端配置商品；调用方不能用参数跨商品查询。
2. 响应中的每个`user_id`必须等于请求主体，否则作为平台协议错误拒绝整批数据。
3. 过滤`status != active`、`usable=false`和已到期权益。
4. `remaining=null`表示不限量；有限额度必须由单个权益覆盖完整预占额。
5. 不拆分多个权益；两个各6积分的权益不能组合承担10积分请求。
6. 足额候选按最早`expires_at`优先，永久权益排最后；到期时间相同按`entitlement_id`升序，保证确定性。

| 场景 | 结果 |
|---|---|
| 无active/usable/未过期权益 | `BILLING_ENTITLEMENT_UNAVAILABLE` |
| 有有限权益但没有单个足额候选 | `BILLING_ENTITLEMENT_INSUFFICIENT` |
| 有足额有限权益 | 选最早过期的单个权益 |
| 只有不限量权益 | 选不限量权益 |
| 平台原子reserve并发返回`60005` | 映射`BILLING_ENTITLEMENT_INSUFFICIENT`，不得换权益自动重复扣 |
| 平台返回跨用户/跨权益余额 | `BILLING_PLATFORM_PROTOCOL_ERROR`或客户端协议错误 |

## 3. 余额与并发边界

`entitlement-balance`只用于UX软提示。即使只读余额显示足额，T17仍必须调用平台原子`reserve`，不得实现“查余额→本地判断→直接运行Agent”。平台在余额查询后返回`60005`是正常并发终态：拒绝任务进入Agent，不自动拆分、不换另一个权益重试、不把Mock或先前余额写成扣费成功。

## 4. 错误与日志

- 错误对象只保留稳定本地code、retryable和平台数字code；不复用下游message、响应正文、令牌或额度明细。
- 内部token只在`X-Internal-Token`请求头使用，不写日志、测试快照或本文。
- 商品、用户和权益作用域不匹配按协议错误处理，不能“尽量继续”。

## 5. T15验证边界

- 自动化选择矩阵覆盖无权益、多个权益、过期、剩余不足、不限量、固定结算上限和平台`60005`。
- 2026-07-23使用现有本地Session主体对真实墨灵执行只读权益列表与余额调用：返回3个权益、3个可用候选并完成1次余额读取；验证脚本只输出数量和布尔值，不输出用户ID、权益ID、额度、令牌或下游正文。
- 该只读结果不是reserve、settle、release或真实扣费证据；`BILLING_ENABLED`仍为`false`。

## 6. T16收费任务与幂等边界

- 客户端`Idempotency-Key`只在服务端Session用户作用域内唯一；不同用户使用同一个客户端值不会互相冲突或泄露记录。
- 同一用户只有完整业务载荷一致时才能复用；标题、正文、语言、模型、模板或计费模式变化均返回稳定409，不能把新请求绑定到旧作品。
- 计费开启时，作品、生成任务和`billing_operations`意图在一个数据库事务中写入；任一写入失败全部回滚。
- 初始状态固定为作品`billing_pending`、任务`billing_required/awaiting_reserve`、计费意图`planned`。T08 Worker只领取`pending`，因此reserve前Agent调用次数必须为0。
- reserve、settle、release分别使用`ppt:{task_id}:reserve|settle|release`，三个键不可复用。网络重试、并发POST和前端刷新只返回原任务与原计费意图。
- 幂等复用核对不可变的owner、业务载荷、商品、金额和三把稳定键；不得要求计费记录仍停留在`planned`，否则reserve后的刷新会被误判为冲突。
- 本阶段未调用真实平台reserve/settle/release；本地真实SQLite证明唯一约束、迁移保留、并发原子性和Worker闸门，不等于真实扣费验收。

## 7. T17 reserve/settle/release编排

状态主链：

```text
planned → reserving → reserved → settling → settled
                         └────→ releasing → released
任一平台写响应或本地终态提交不确定 → billing_pending
```

- 常驻Worker从持久`planned`意图开始预占；数据库条件更新决定唯一执行者，平台调用发生在事务外。只有reserve成功并保存hold后，任务才能由`billing_required`推进为可领取的`pending`。
- Agent正常返回后仍须只读确认作品产物已持久化；确认存在才settle，明确不存在或明确生成失败才release。Agent抛错、取消或超时同样先探测，禁止把“异常”直接等同为“无产物”。
- 产物探测自身异常时不settle也不release，动作记为`inspect`并冻结`billing_pending`，由T18恢复判断。
- reserve、settle、release分别使用T16生成的独立稳定键；相同动作重复进入时，已到达本地终态直接复用，不再调用平台。两个进程并发发现同一`planned`意图时，仅数据库赢家调用一次reserve。
- 平台写调用成功但本地终态条件提交未完成时，记录对应`*_LOCAL_COMMIT_FAILED`并冻结；reserve路径同时保存平台返回hold，settle/release保留原hold和动作键。若数据库整体不可用，原`reserving|settling|releasing`证据保持不变，T18只能用原键恢复，不能生成新reserve键。
- settle/release响应中的`status`和本次`settled_amount`证明当前hold终态；`quota_reserved`是该权益所有并发hold的聚合值，其他任务仍占用时可以非零，不能误判为本次失败。
- `BILLING_ENABLED=false`只阻止新收费任务和新reserve。计费运行配置仍完整时，Worker继续settle/release遗留hold；配置不足时任务领取查询和条件更新双重排除所有带计费记录的任务，禁止裸跑Agent。
- 额度不足（含平台原子`60005`）在Agent前明确失败；不换权益、不调用Agent。reserve/settle/release响应丢失或协议不明时不执行猜测性补偿，进入T18待对账。
- O-03采用独立配置`SLIDE_REGENERATION_POINTS`；真实值和单页收费入口未确认前保持空值且不开放该收费能力，不能复用整套PPT金额。
- T17全部写路径只用MockTransport/Fake客户端与真实本地SQLite验证；没有对真实墨灵产生积分写入，`BILLING_ENABLED=false`、`TASK_WORKER_ENABLED=false`。

## 8. T18 未知终态对账

```text
billing_pending ──到期认领──→ reconciling ──同键成功──→ settled/released
       ↑                              └──失败且未达上限──→ 指数退避
       └──────────────────────────────── 达上限/不可安全判定 ──→ manual_required
```

- 平台未提供按hold查询预付终态的接口，因此未知reserve禁止自动重放，直接进入`manual_required`；settle/release只能重放T16已持久化的原幂等键。
- 退避次数、下次时间和动作都持久化，服务重启不会从零开始。默认最多8次，可由`BILLING_RECONCILE_MAX_RETRIES`配置，合法范围1～100；退避按配置周期指数增长并封顶1小时。
- 对账退避与平台调用租约分离。生产租约覆盖pool、connect、write、read四段配置超时并增加调度余量；`reserving/settling/releasing/reconciling`未超过租约时不得由另一Worker重放。
- 最后一次认领后进程崩溃时，租约和退避均到期才原子转`manual_required`，不会永久悬挂，也不会在原调用仍可能进行时提前宣告人工状态。
- `GET /api/tasks/{task_id}`只按服务端Session owner查询。公开计费摘要仅含status、action、retry_count、next_retry_at和manual_required，不返回hold、幂等键、权益ID或金额。
- `BILLING_ENABLED=false`继续阻止新收费任务和新reserve；仅在平台运行配置完整时允许常驻Worker用原键收尾历史hold。
- T18以Fake平台账本和真实本地SQLite验证状态、并发与重启，不是墨灵真实积分流水。真实写入及应用记录对账保留到T23/G5，当前生产计费仍关闭。

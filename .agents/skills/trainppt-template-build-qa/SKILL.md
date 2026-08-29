---
name: trainppt-template-build-qa
description: Build, test, repair, and QA TrainPPTAgent production templates from an approved machine-readable template specification, including image assets, PPTist semantic JSON, registration, automated tests, real generation, responsive verification, PPTX round-trip checks, and evidence. Do not use for planning-only requests or Git release operations.
---

# TrainPPTAgent 模板开发、测试与 QA

消费状态为 `READY_FOR_BUILD` 的机器可读规格，把模板实现推进到可人工验收的 `READY_FOR_CONFIRMATION`。模板规划、Git 发布、服务重启和生产部署不属于本 Skill。

## 路由

先判断用户意图，再读取对应 reference：

| 模式 | 适用请求 | 必须读取 | 副作用边界 |
|---|---|---|---|
| `build` | 按批准规格开发模板、生成素材并接入项目 | [build-workflow.md](references/build-workflow.md)、[template-contract.md](references/template-contract.md)、[asset-policy.md](references/asset-policy.md)、[qa-matrix.md](references/qa-matrix.md) | 仅在用户当前请求明确授权后修改模板、测试与注册代码 |
| `repair` | 修复已确认的模板验收问题 | 同 `build`，并读取失败证据 | 只修改问题直接涉及的文件，不扩大模板范围 |
| `test-only` | 只运行模板与受影响测试 | [qa-matrix.md](references/qa-matrix.md) | 不修复、不改生产文件 |
| `audit-evidence` | 只读审计已有测试与 QA 证据 | [qa-matrix.md](references/qa-matrix.md)、[evidence-schema.md](references/evidence-schema.md) | 只读 |
| `run-qa` | 执行真实生成、编辑、换图、视口和 PPTX 往返 | [qa-matrix.md](references/qa-matrix.md)、[evidence-schema.md](references/evidence-schema.md) | 需明确授权真实 QA；只创建测试任务、临时导出和指定证据 |
| `close` | 用户明确确认后更新 Goal 文档状态 | [evidence-schema.md](references/evidence-schema.md) | 只更新用户授权的 Goal 状态；确定性脚本绝不输出 `DONE` |

如果请求包含“只写文档”“不执行”“不操作”“不生成图片”或“不修改代码”，停止本 Skill，改用 `trainppt-template-planning`。如果请求涉及 Commit、Push、PR、合并、重启或部署，交给 `trainppt-safe-release`，不得从模板开发授权推导这些权限。

## 开始前门禁

在任何实现或真实 QA 副作用前：

1. 读取规格原始字节并确认 `status: READY_FOR_BUILD`、`spec_version: 1`。
2. 运行 `scripts/validate-development-spec.py`；由主 Agent 用显式参数表达当前消息授予的代码、图片或真实 QA 权限，不能把规格里的未来授权需求当作实时授权。
3. 重新计算规格 SHA-256 与参考文件哈希。模板 ID 被占用、参考文件变化、规格哈希漂移、页面/视觉/版权/素材角色变化或 QA 门禁降低时停止并返回规划 Skill。
4. 记录现有 Git 改动，保护用户文件；重新发现当前模板目录、注册入口、渲染器和测试入口。
5. 需要独立验收时读取 [subagent-contracts.md](references/subagent-contracts.md)，只创建只读 `build-qa-auditor`。

规格不满足或权限不足时，不尝试“尽量继续”。分别以契约阻断、权限阻断或环境不可用报告真实原因。

## 实施顺序

`build` 与 `repair` 按以下语义阶段推进，阶段编号不依赖历史 G0～G8：

1. 开发预检。
2. 按素材 manifest 生产和审计资产。
3. 构建 MVP，运行 JSON、资源、注册和专项测试。
4. 用真实持久 Worker 通过 MVP 生成门禁。
5. 扩展生产版并唯一注册模板。
6. 运行专项、通用 renderer/assets 与当前受影响后端回归；只有修改前端源码时才强制前端类型检查、单测和生产构建。
7. 执行真实 E2E、四视口、编辑保存、内容图替换、装饰保护与失败重试。
8. 导出、解析并重新导入 PPTX，验证继续编辑能力。
9. 用显式输出路径收集精简证据，再运行最终门禁。

每一阶段失败都回到直接责任阶段修复；不得降低断言、缩小规格、静默丢内容或用占位资产强行通过。

## 确定性脚本

脚本均参数化、默认不修改生产文件，并向标准输出写结构化 JSON：

- `validate-development-spec.py`：规格、哈希、ID、参考文件和实时授权门禁。
- `validate-template-json.py`：模板结构、页面库存、ID、语义槽位和危险路径。
- `audit-template-assets.py`：引用集合、图片尺寸/模式/Alpha/体积和哈希。
- `verify-template-registration.ps1`：注册唯一性、标题、JSON 与封面路径。
- `run-template-tests.ps1`：动态发现并运行专项、通用或后端测试；不执行规格中的任意命令文本。
- `verify-template-api.ps1`：只读验证模板列表、JSON、封面、外置资源和可选前端代理。
- `verify-pptx-roundtrip.py`：验证 PPTX 包结构、页数及可选的产品重导入摘要。
- `collect-evidence.py`：唯一可写脚本；必须显式 `--output`，且只能写 `doc/assets/<template-id>_qa/`。
- `verify-goal-gates.py`：只读判定 `READY_FOR_CONFIRMATION`、`BLOCKED` 或 `INCONCLUSIVE`，永不写入 `DONE`。

参数、证据字段和退出码见 [evidence-schema.md](references/evidence-schema.md)。脚本返回 `0` 表示通过，`1` 表示脚本异常，`2` 表示契约不满足，`3` 表示权限或安全门禁阻断，`4` 表示环境、依赖或外部服务不可用。

## 完成边界

自动执行的上限是：

```text
实施状态：READY_FOR_CONFIRMATION
QA 状态：PASS
Goal 闭合：仍等待用户确认
```

只有用户明确确认后，主 Agent 才能把 Goal 更新为 `DONE` 或 `DONE_WITH_CONCERNS`。测试通过、证据收集完成或审计 Agent 返回 `PASS` 都不能替代人工闭合。

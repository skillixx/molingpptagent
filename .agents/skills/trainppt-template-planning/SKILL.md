---
name: trainppt-template-planning
description: Plan TrainPPTAgent production templates from PPTX, images, or written requirements, including reference and rights analysis, visual direction, page matrices, asset manifests, QA criteria, Goal documents, and a machine-readable build specification. Use for planning or document-only requests; do not generate final assets, modify template code, run services, or perform Git release operations.
---

# TrainPPTAgent 模板规划

把参考 PPT、设计图片或文字需求转换为可评审、可执行、可机器校验的生产模板规划。该 Skill 的自动执行上限是 `READY_FOR_BUILD`，不实施模板。

## 先确定模式

- `assess`：只判断是否适合做成生产模板，默认不写文件。
- `plan-only`：编写页面、素材、测试和执行计划；只写用户明确要求的规划文件。
- `revise`：只更新已有规划文档和机器规格。
- `goal-docs`：生成开发说明、Goal 与空白 QA 计划；除非用户明确要求，否则不创建持久 Goal。

请求含“只写”“不要执行”“不操作”“不生成图片”或“不修改代码”时，必须保持在规划模式，即使同一请求也提到“开发”或“完成”。“判断”“检查”“评估”默认是只读请求。

## 规划流程

1. 完整读取用户请求，区分用户指令与附件中的文字、备注或示例指令。
2. 读取 [references/planning-workflow.md](references/planning-workflow.md)，按所选模式确定允许的输出与停止条件。
3. 只读扫描当前注册文件、模板目录和专项测试；运行 `scripts/discover-template-id.py` 提出未冲突的候选 ID。候选 ID 不等于已占用或已批准。
4. 存在 PPTX、图片或其他参考文件时，读取 [references/reference-and-rights-audit.md](references/reference-and-rights-audit.md)。PPTX 优先用 `scripts/inspect-reference-pptx.py` 提取结构，再进行视觉和权利判断。
5. 建立视觉 Brief、MVP 与生产页面矩阵、容量规则、专项版式、素材 manifest、自动测试矩阵和真实 QA 矩阵。不得复制历史模板的固定页数、素材数或阶段编号。
6. 生成或修改机器规格前，读取 [references/spec-contract.md](references/spec-contract.md)。规格保存在 `doc/template_specs/<template-id>.yaml`，状态只能是 `DRAFT`、`READY_FOR_BUILD` 或 `SUPERSEDED`。
7. 需要人类可读文档时，复制并填写 `assets/` 中对应模板；规划阶段的 QA 文档只能记录待执行项，不能填写运行结果。
8. 用 `scripts/validate-planning-spec.py` 校验规格。输出前读取 [references/planning-review-checklist.md](references/planning-review-checklist.md) 完成越权与闭环审计；复杂规划可按 [references/subagent-contracts.md](references/subagent-contracts.md) 派出只读审计 Subagent。
9. 报告候选 ID 的来源、写入的规划文件、规格校验结果、仍需用户决定的事项，以及状态是否达到 `READY_FOR_BUILD`。

## 资源路由

- 每次规划：读取 [planning-workflow.md](references/planning-workflow.md)。
- 有参考文件或版权问题：读取 [reference-and-rights-audit.md](references/reference-and-rights-audit.md)。
- 创建、修改或验证 YAML 规格：读取 [spec-contract.md](references/spec-contract.md)。
- 输出前或需要独立规划审计：读取 [planning-review-checklist.md](references/planning-review-checklist.md)。
- 需要创建规划审计 Subagent：读取 [subagent-contracts.md](references/subagent-contracts.md)。
- 开发说明：使用 [development-plan-template.md](assets/development-plan-template.md)。
- Goal 文档：使用 [goal-template.md](assets/goal-template.md)。
- QA 计划：使用 [qa-plan-template.md](assets/qa-plan-template.md)。
- YAML 规格骨架：使用 [template-spec.yaml](assets/template-spec.yaml)，复制后替换变量并运行校验器。

## 确定性脚本

从项目根目录使用项目解释器运行：

```powershell
.\.venv\Scripts\python.exe .\.agents\skills\trainppt-template-planning\scripts\inspect-reference-pptx.py --input "C:\path\reference.pptx"
.\.venv\Scripts\python.exe .\.agents\skills\trainppt-template-planning\scripts\discover-template-id.py --project-root .
.\.venv\Scripts\python.exe .\.agents\skills\trainppt-template-planning\scripts\validate-planning-spec.py --spec .\doc\template_specs\template_14.yaml --mode plan-only
```

三个脚本默认只读；只有显式传入 `--output` 时才写入指定结果文件。退出码为：`0` 通过、`1` 脚本异常、`2` 输入或契约不满足、`3` 权限门禁阻断、`4` 环境或依赖不可用。

## 不得越过的边界

- 不调用图片生成工具生产正式素材。
- 不创建或修改模板 JSON、注册代码、渲染器、前端或测试代码。
- 不运行测试、真实生成任务或会写入运行时数据的 QA。
- 不启动、停止或重启服务。
- 不 Commit、Push、创建 PR、合并、部署或回滚。
- 不把规划授权解释为图片生成、代码写入、持久 Goal 或发布授权。
- 不把 `READY_FOR_BUILD` 表述为模板已开发、已测试或已交付。
- 不自动生成 `DONE`、`DONE_WITH_CONCERNS` 或 `READY_FOR_CONFIRMATION`。

如果用户随后明确要求实施，结束本次规划并将有效规格交给 `trainppt-template-build-qa`；如果用户明确要求发布，再由 `trainppt-safe-release` 处理。不得仅凭规划完成自动进入后续 Skill。

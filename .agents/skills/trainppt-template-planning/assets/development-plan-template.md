# {{template_name}} PPT 模板开发说明

## 1. 文档状态

| 项目 | 内容 |
|---|---|
| 模板名称 | `{{template_name}}` |
| 候选模板 ID | `{{template_id}}`，仅为候选，不代表已占用 |
| 机器规格 | `doc/template_specs/{{template_id}}.yaml` |
| 规格状态 | `{{DRAFT_or_READY_FOR_BUILD}}` |
| 规划日期 | `{{yyyy-mm-dd}}` |
| 本文范围 | 只定义开发计划，不生成图片、不修改代码、不运行服务、不执行 Git 发布 |

## 2. 目标与非目标

### 目标

- {{template_goal_1}}
- {{template_goal_2}}

### 非目标

- 不在规划阶段生产正式图片或模板 JSON。
- 不在规划阶段修改注册、渲染器、前端或测试代码。
- 不在规划阶段运行真实任务、提交代码、合并或重启服务。

## 3. 输入与参考审计

| 参考文件 | SHA-256 | 类型 | 权利状态 | 规划动作 |
|---|---|---|---|---|
| `{{reference_path}}` | `{{sha256}}` | `{{kind}}` | `{{rights_status}}` | `{{reuse_redraw_regenerate_replace_exclude}}` |

可复用的抽象规律：

- {{reusable_pattern}}

禁止直接带入生产模板的内容：

- {{forbidden_carryover}}

## 4. 当前项目发现

| 项目 | 当前发现 | 发现依据 |
|---|---|---|
| 模板目录 | `{{template_dir}}` | 当前仓库扫描 |
| 注册入口 | `{{registration_file}}` | 当前仓库扫描 |
| 渲染器 | `{{renderer_file}}` | 当前仓库扫描 |
| 候选 ID | `{{template_id}}` | 注册、文件、素材和专项测试联合扫描 |

## 5. 视觉 Brief

- 主题与语气：{{visual_theme}}
- 受众与场景：{{audience_and_scenario}}
- 主辅色：{{palette}}
- 标题与正文字体：{{fonts}}
- 最小字号：{{minimum_font_sizes}}
- 标题、正文、图片和装饰安全区：{{safe_zones}}
- 禁止内容：{{forbidden_content}}

## 6. 页面系统

### MVP 页面矩阵

| 页面类型 | 数量 | 容量或变体 | 验证目的 |
|---|---:|---|---|
| {{page_type}} | {{count}} | {{capacities_or_variants}} | {{gate}} |

### 生产版页面矩阵

| 页面类型 | 数量 | 选择条件 | 说明 |
|---|---:|---|---|
| {{page_type}} | {{count}} | {{selection_rule}} | {{purpose}} |

专项版式：

| ID | 用途 | 确定性选版规则 |
|---|---|---|
| `{{layout_id}}` | {{purpose}} | {{selection_rule}} |

容量与溢出策略：

- 目录容量：{{contents_capacities}}
- 正文容量：{{content_capacities}}
- 超量策略：无损分页，保留字符和顺序，不以不可读字号压缩内容。

## 7. 素材清单

| ID | 角色 | 文件名 | 格式/尺寸 | Alpha | 体积上限 | 安全区 | 权利动作 | 重试上限 |
|---|---|---|---|---|---:|---|---|---:|
| `{{asset_id}}` | {{role}} | `{{filename}}` | {{format_and_dimensions}} | {{alpha}} | {{max_bytes}} | {{safe_zone}} | {{rights_action}} | {{max_attempts}} |

提示词约束：{{prompt_constraints}}

## 8. 语义与渲染契约

- 页面类型：{{page_types}}
- 文字槽类型：{{text_types}}
- 内容图片：`imageType: content`
- 固定装饰：`imageType: decoration`
- 图片分组：内容图片保持独立可替换。
- 内容溢出：`paginate-without-loss`

## 9. 开发阶段与门禁

1. 开发前重新核验规格哈希、参考哈希、候选 ID 和仓库协议。
2. 按 manifest 生产并审计素材。
3. 构建 MVP 并通过真实生成门禁。
4. 扩展生产版并完成注册。
5. 运行专项测试和受影响回归。
6. 完成真实任务、四视口、编辑、换图、失败重试和 PPTX 往返。
7. 汇总精简证据，自动状态最多到 `READY_FOR_CONFIRMATION`。
8. 用户明确确认后才能闭合为 `DONE` 或 `DONE_WITH_CONCERNS`。

## 10. 测试与 QA 计划

| 完成条件 ID | 自动测试或 QA 案例 | 预期证据 |
|---|---|---|
| `{{criterion_id}}` | `{{case_id}}` | {{evidence_type}} |

目标视口：{{viewports}}

## 11. 交付物

- 规划规格：`doc/template_specs/{{template_id}}.yaml`
- 模板 JSON：`backend/main_api/template/{{template_id}}.json`
- 封面与外置素材：`backend/main_api/template/{{template_id}}*`
- 专项测试：`backend/main_api/tests/test_template_{{n}}.py`
- QA 证据：`doc/assets/{{template_id}}_qa/evidence.json`

以上生产文件是后续开发 Skill 的预期产物，不是本文已完成的产物。

## 12. 权限与开放决策

后续实施必须重新取得：图片生成、代码修改和真实 QA 的当前授权。Commit、Push、PR、合并、重启和生产发布不包含在模板开发授权中。

开放决策：

- {{open_decision_or_none}}

已知限制：

- {{known_limit_or_none}}

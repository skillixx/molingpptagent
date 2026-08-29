# 规划规格契约

本文件定义 `doc/template_specs/<template-id>.yaml` 的第一版契约。创建、修改或验证规格时读取。示例值仅表示字段形状，不是模板默认参数。

## 1. 文件与编码

- 路径：`doc/template_specs/<template-id>.yaml`。
- 编码：UTF-8 无 BOM。
- 换行：LF。
- `spec_version`：整数 `1`。
- 顶层必须是 YAML 映射，不能使用自定义 YAML 类型。
- 路径字段使用字符串；项目内路径优先相对项目根目录。

## 2. 顶层字段

| 字段 | 类型 | 要求 |
|---|---|---|
| `spec_version` | integer | 必须为 `1` |
| `status` | string | `DRAFT / READY_FOR_BUILD / SUPERSEDED` |
| `created_at` | date/string | 必填 |
| `updated_at` | date/string | 必填 |
| `project` | mapping | 项目发现结果 |
| `template` | mapping | 候选 ID、名称、参考和画布 |
| `visual` | mapping | 主题、颜色、字体和安全区 |
| `pages` | mapping | MVP、生产版和专项版式 |
| `semantics` | mapping | 页面、文字、图片和分页协议 |
| `assets` | mapping | 生成偏好、重试上限与素材项 |
| `completion_criteria` | list | 带稳定 ID 的完成条件 |
| `qa` | mapping | 案例、视口、命令和覆盖映射 |
| `planning_run_permissions` | mapping | 本次规划运行权限快照 |
| `required_build_authorizations` | mapping | 后续实施需要重新取得的授权 |
| `open_decisions` | list | 仍会改变方案的用户决策 |
| `known_limits` | list | 已知但不阻断规划的限制 |

规格不得包含实施进度、QA 结果、运行任务 ID、测试通过数、`DONE` 或 `READY_FOR_CONFIRMATION`。这些属于后续 Skill 和证据文件。

## 3. 项目与模板

`project` 必填：

```yaml
project:
  root: "D:\\moling\\TrainPPTAgent"
  template_dir: "backend/main_api/template"
  registration_file: "backend/main_api/main.py"
  renderer_file: "backend/main_api/workers/template_renderer.py"
```

`template` 必填：

```yaml
template:
  id: "template_14"
  id_status: "candidate"
  name: "示例生产模板"
  category: "example"
  requirements_summary: "模板用途、受众和核心表达"
  reference_files:
    - path: "C:\\path\\reference.pptx"
      sha256: "64位小写十六进制"
      rights_status: "unknown"
      planned_action: "redraw-and-regenerate"
  canvas:
    width: 1000
    height: 562.5
  cover:
    width: 960
    height: 540
```

规则：

- ID 必须匹配 `template_<正整数>`，状态必须是 `candidate`。
- 候选 ID 在开发开始前仍要重新扫描，规格不会占号。
- `requirements_summary` 和 `reference_files` 至少一个提供有效信息。
- `READY_FOR_BUILD` 的现存参考文件必须有真实 SHA-256。
- 画布与封面宽高必须为正数。

## 4. 视觉、页面与语义

`visual` 至少定义：`theme`、非空 `palette`、非空 `fonts`、非空 `safe_zones`、`forbidden_content`、`logo_policy` 和 `people_policy`。

`pages` 结构：

```yaml
pages:
  mvp:
    inventory:
      cover: 1
      contents: 1
      transition: 1
      content: 3
      end: 1
    contents_capacities: [3, 4, 5]
    content_capacities: [1, 2, 3, 4]
  production:
    inventory:
      cover: 2
      contents: 3
      transition: 2
      content: 8
      end: 1
  specialty_layouts:
    - id: "metrics"
      purpose: "关键指标展示"
      selection_rule: "内容含指标数据时选择"
```

示例数量不能作为默认值。实际规格由当前用途确定。`inventory` 的键与值必须非空、值为非负整数，且每个阶段的总页数大于零。容量列表必须是去重的正整数。

`semantics` 至少定义：

- 非空 `page_types` 与 `text_types`；
- `content_image_type: content`；
- `decoration_image_type: decoration`；
- 非空 `minimum_font_sizes`；
- `overflow_policy: paginate-without-loss`；
- `grouping_policy: content-images-independent`。

## 5. 素材 manifest

```yaml
assets:
  generator_preference: "gpt-image-2"
  max_total_generation_attempts: 20
  items:
    - id: "cover-background"
      role: "background"
      filename: "template_14_asset_bg_cover_v1.jpg"
      format: "JPEG"
      dimensions: [1920, 1080]
      max_bytes: 350000
      alpha_required: false
      safe_zone: "左侧标题区域保持低细节"
      prompt_constraints:
        - "无文字"
        - "无 Logo"
      rights_action: "regenerate"
      max_attempts: 3
```

每项必须有唯一 `id` 和 `filename`。角色、格式、尺寸、体积、Alpha、安全区、提示约束、权利动作和单项重试上限都要明确。规划只描述生成要求，不写实际生成结果。

## 6. 完成条件与 QA 覆盖

```yaml
completion_criteria:
  - id: "criterion-page-inventory"
    description: "页面库存与规格一致"
  - id: "criterion-responsive"
    description: "四种视口无横向溢出且关键按钮可触达"

qa:
  content_cases:
    - id: "case-page-inventory"
      purpose: "验证页面类型和数量"
  image_counts:
    - id: "case-image-counts"
      values: [0, 1, 3]
  viewports:
    - id: "viewport-desktop"
      width: 1440
      height: 900
    - id: "viewport-mobile"
      width: 390
      height: 844
  export_roundtrip_required: true
  affected_test_commands:
    - ".\\.venv\\Scripts\\python.exe -m pytest backend/main_api/tests/test_template_<N>.py"
  coverage_map:
    criterion-page-inventory: ["case-page-inventory"]
    criterion-responsive: ["viewport-desktop", "viewport-mobile"]
```

所有案例 ID 在 `content_cases`、`image_counts`、`viewports` 或保留 ID `export-roundtrip` 中唯一。每个完成条件必须出现在 `coverage_map`，并至少映射一个存在的案例。测试命令是规划字符串，不能在规划 Skill 中执行。

## 7. 权限字段

规划运行权限必须完整且全部为 `false`：

```yaml
planning_run_permissions:
  allow_image_generation: false
  allow_code_changes: false
  allow_git_commit: false
  allow_git_push: false
  allow_merge_main: false
  allow_service_restart: false
  allow_production_deploy: false
```

后续授权只声明需要重新确认什么，不代表已经获得授权：

```yaml
required_build_authorizations:
  image_generation: true
  code_changes: true
  real_task_execution: true
  final_manual_close: true
```

## 8. 状态与开放决策

- `DRAFT`：字段可能完整，但仍有阻断性 `open_decisions` 或尚未完成审计。
- `READY_FOR_BUILD`：校验通过，`open_decisions` 为空，参考哈希和权利动作完整。
- `SUPERSEDED`：已被另一份明确指向的新规格替代；不允许作为实施输入。

状态不会证明用户已经授权实施。开发 Skill 开始时仍要检查当前请求、ID、参考哈希和仓库漂移。

## 9. 哈希与漂移

1. 完成 `READY_FOR_BUILD` 文件后，确保 UTF-8 无 BOM和 LF。
2. 对完整原始字节计算 SHA-256。
3. `spec_sha256` 不写回规格，避免自引用。
4. 将哈希记录在 Goal 执行记录和后续 `evidence.json`。
5. 开发前和最终验收前重新计算；不一致时停止并返回规划检查。

模板 ID 被占用、参考哈希变化、页面类型变化、视觉或版权策略变化、素材角色减少或 QA 门禁降低，均需要返回规划 Skill 重新形成有效规格。

## 10. 验证

```powershell
.\.venv\Scripts\python.exe .\.agents\skills\trainppt-template-planning\scripts\validate-planning-spec.py --spec .\doc\template_specs\template_14.yaml --mode plan-only
```

校验器验证结构、状态、页面和素材非空、QA 闭环与权限；它不替代参考权利判断、视觉评审或候选 ID 冲突扫描。

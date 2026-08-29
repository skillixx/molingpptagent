# QA 证据 Schema 与脚本接口

本文件在收集、审计或判定证据时读取。第一版 `evidence_schema_version` 为整数 `1`。

`collect-evidence.py` 与 `verify-goal-gates.py` 必须共同使用内部 `_qa_contract.py`，避免证据收集和最终门禁出现两套 QA 规则。

## 标准路径

```text
doc/assets/<template-id>_qa/evidence.json
```

`collect-evidence.py` 只允许在显式 `--output` 指向上述目录或其子目录时写入；已存在文件默认不覆盖，只有显式 `--force` 才能替换目标证据文件。

## 顶层字段

```json
{
  "evidence_schema_version": 1,
  "template_id": "template_14",
  "generated_at": "2026-08-29T00:00:00Z",
  "qa_status": "PASS",
  "implementation_status": "READY_FOR_CONFIRMATION",
  "spec": {
    "path": "doc/template_specs/template_14.yaml",
    "sha256": "...",
    "reference_files": []
  },
  "implementation": {
    "template_json": {},
    "page_types": {},
    "slides": 0,
    "elements": 0
  },
  "checks": {},
  "qa": {},
  "artifacts": [],
  "known_limitations": []
}
```

## `checks`

每个脚本报告以稳定名称保存：

```text
development_spec
template_json
assets
registration
tests
api
pptx_roundtrip
```

每项至少包含：

```json
{
  "status": "PASS | FAIL | INCONCLUSIVE",
  "source": "相对路径",
  "sha256": "报告文件哈希",
  "summary": {}
}
```

任何必需检查缺失或状态不是 `PASS`，都不能进入 `READY_FOR_CONFIRMATION`。

## `qa`

真实 QA manifest 由主 Agent 根据真实操作生成，最低结构：

```json
{
  "e2e": {
    "status": "succeeded",
    "progress": 100,
    "template_id": "template_14",
    "declared_slide_count": 0,
    "actual_slide_count": 0,
    "page_types_covered": []
  },
  "editor": {
    "text_saved": true,
    "text_persisted_after_reload": true,
    "content_image_replaced": true,
    "decorations_preserved": true
  },
  "failure_feedback": {
    "visible": true,
    "button_recovered": true,
    "retry_available": true
  },
  "responsive": [
    {
      "class": "desktop | laptop | tablet | mobile",
      "viewport": "1920x1080",
      "client_width": 1920,
      "scroll_width": 1920,
      "buttons_reachable": true,
      "feedback_visible": true
    }
  ],
  "runtime": {
    "template_unique": true,
    "template_json_ok": true,
    "cover_ok": true,
    "assets_ok": true
  },
  "pptx": {
    "structure_valid": true,
    "slide_count_matches": true,
    "parsed_by_product": true,
    "reimported": true,
    "editable_after_reimport": true
  }
}
```

四种 `class` 必须各出现一次以上；每项 `scroll_width <= client_width` 且按钮与反馈为真。

## QA 状态推导

- 任一报告或明确 QA 布尔门禁失败：`FAIL`。
- 没有明确失败，但报告、字段或四视口不完整：`INCONCLUSIVE`。
- 所有必需检查与真实 QA 门禁通过：`PASS`，实施状态可为 `READY_FOR_CONFIRMATION`。

不得在证据脚本中生成 `DONE` 或 `DONE_WITH_CONCERNS`。

## 脚本统一接口

- 项目根、模板 ID、规格、模板 JSON、证据目录均由参数传入。
- 标准输出是 UTF-8 JSON；诊断信息写标准错误。
- 不输出数据库 URL、用户名、密码、Token、Cookie、Authorization 或业务正文。
- 重复运行不删除用户文件；除 `collect-evidence.py` 外不写文件。

退出码：`0` 通过；`1` 脚本异常；`2` 契约不满足；`3` 权限或安全门禁阻断；`4` 环境、依赖或外部服务不可用。

## 脚本调用参考

| 脚本 | 关键参数 | 输入与输出 | 副作用 |
|---|---|---|---|
| `validate-development-spec.py` | `--project-root --spec [--template-id] --mode`，实时授权使用三个 `--authorize-*` 标志 | 读取 YAML、参考文件、注册和 Git 状态；输出 JSON | 无 |
| `validate-template-json.py` | `--project-root --template-id --template-json [--spec]` | 读取模板与可选规格；输出 JSON | 无 |
| `audit-template-assets.py` | `--project-root --template-id --template-json [--spec] [--template-dir]` | 读取模板、manifest、封面和素材；输出 JSON | 无 |
| `verify-template-registration.ps1` | `-ProjectRoot -TemplateId [-RegistrationFile] [-TemplateDir] [-ExpectedName]` | 读取注册源文件、JSON 和封面；输出 JSON | 无 |
| `run-template-tests.ps1` | `-ProjectRoot -TemplateId [-Scope template|affected|backend] [-PythonPath] [-PlanOnly]` | 安全发现 pytest 路径；输出 JSON 与精简测试尾部 | 不改生产文件；测试只写系统临时目录，禁用 pytest 缓存 |
| `verify-template-api.ps1` | `-BaseUrl -TemplateId [-ExpectedName] [-FrontendBaseUrl] [-TimeoutSeconds]` | 只发 GET，验证列表、JSON、封面和资源；输出 JSON | 无服务写入 |
| `verify-pptx-roundtrip.py` | `--pptx [--expected-slides] [--roundtrip-json] [--require-product-roundtrip]` | 读取 PPTX 和产品解析摘要；输出 JSON | 无 |
| `collect-evidence.py` | `--project-root --template-id --spec --template-json --report name=path --output`，可选 `--qa-manifest --artifact --known-limitation --force` | 汇总报告并输出 JSON 结果 | 仅写显式 `doc/assets/<template-id>_qa/evidence.json` |
| `verify-goal-gates.py` | `--evidence --template-id [--project-root] [--expected-spec-sha256]` | 读取证据并输出判断 | 无；永不写 Goal |

可复制命令：

```powershell
.venv\Scripts\python.exe .agents\skills\trainppt-template-build-qa\scripts\validate-development-spec.py --project-root . --spec doc\template_specs\template_14.yaml --mode build --authorize-code-changes --authorize-image-generation --authorize-real-qa
.venv\Scripts\python.exe .agents\skills\trainppt-template-build-qa\scripts\validate-template-json.py --project-root . --template-id template_14 --template-json backend\main_api\template\template_14.json --spec doc\template_specs\template_14.yaml
.venv\Scripts\python.exe .agents\skills\trainppt-template-build-qa\scripts\audit-template-assets.py --project-root . --template-id template_14 --template-json backend\main_api\template\template_14.json --spec doc\template_specs\template_14.yaml
& .agents\skills\trainppt-template-build-qa\scripts\verify-template-registration.ps1 -ProjectRoot . -TemplateId template_14
& .agents\skills\trainppt-template-build-qa\scripts\run-template-tests.ps1 -ProjectRoot . -TemplateId template_14 -Scope template
& .agents\skills\trainppt-template-build-qa\scripts\verify-template-api.ps1 -BaseUrl http://127.0.0.1:6800 -TemplateId template_14
.venv\Scripts\python.exe .agents\skills\trainppt-template-build-qa\scripts\verify-pptx-roundtrip.py --pptx .codex-tmp\template_14\qa.pptx --expected-slides 12 --roundtrip-json .codex-tmp\template_14\reimport.json --require-product-roundtrip
.venv\Scripts\python.exe .agents\skills\trainppt-template-build-qa\scripts\collect-evidence.py --project-root . --template-id template_14 --spec doc\template_specs\template_14.yaml --template-json backend\main_api\template\template_14.json --qa-manifest .codex-tmp\template_14\qa-manifest.json --report development_spec=.codex-tmp\template_14\spec-report.json --output doc\assets\template_14_qa\evidence.json
.venv\Scripts\python.exe .agents\skills\trainppt-template-build-qa\scripts\verify-goal-gates.py --project-root . --template-id template_14 --evidence doc\assets\template_14_qa\evidence.json
```

## 示例

```powershell
.venv\Scripts\python.exe .agents\skills\trainppt-template-build-qa\scripts\validate-template-json.py `
  --project-root . --template-id template_14 `
  --template-json backend\main_api\template\template_14.json `
  --spec doc\template_specs\template_14.yaml
```

```powershell
& .agents\skills\trainppt-template-build-qa\scripts\run-template-tests.ps1 `
  -ProjectRoot . -TemplateId template_14 -Scope template
```

```powershell
.venv\Scripts\python.exe .agents\skills\trainppt-template-build-qa\scripts\collect-evidence.py `
  --project-root . --template-id template_14 --spec doc\template_specs\template_14.yaml `
  --template-json backend\main_api\template\template_14.json `
  --qa-manifest .codex-tmp\template_14\qa-manifest.json `
  --report development_spec=.codex-tmp\template_14\spec-report.json `
  --output doc\assets\template_14_qa\evidence.json
```

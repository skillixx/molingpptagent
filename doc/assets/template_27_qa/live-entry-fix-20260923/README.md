# 日常入口缺少唯美清新模板：运行态修复记录

状态：已修复。日期：2026-09-23。

## 原因与复现

用户截图中的日常模板列表停在 `template_26`。实际读取发现：

- 日常入口 `5778/api/templates` 与主 API `6800/templates` 返回 25 个模板，没有 `template_27`。
- 隔离验收入口 `5779/api/templates` 与 `6801/templates` 返回 26 个模板，包含 `template_27`。
- 当前源码已注册 `template_27`，但 6800 进程在注册代码修改前启动，且未启用热重载。

此前交付验证了隔离入口，遗漏了日常主 API 重新加载；并非模板或素材没有生成，也不是前端筛选逻辑遗漏。

## 处理

1. 核对 6800 的 PID、命令行、工作目录和项目归属，确认它来自当前项目 `backend/main_api`。
2. 只读检查宿主数据库与在途任务：`SELECT 1` 成功，pending/running 任务数为 0。
3. 仅重新启动本地主 API，保留当前 release identity，没有修改 `.env`、模板、前端或其他运行中的服务。
4. 首次重启后发现本机 HTTP 依赖受 Windows 系统代理影响：相同请求使用系统代理返回 502，直连返回 200。确认服务地址本身正确后，给新 API 进程设置 `NO_PROXY=127.0.0.1,localhost,::1`，未修改系统代理。

本机后续启动主 API 时应保留本地地址的代理绕过设置。进程级 `RELEASE_COMMIT` 与 `RELEASE_CHANNEL` 保持原本地服务的有效值，不代表进行了生产发布。

## 修复后证据

- 日常模板列表包含“蓝紫光斑·唯美清新”，编号 `template_27`。
- 封面图片 HTTP 200，模板 JSON HTTP 200，包含 21 个版式。
- `/readyz` 返回 ready；outline、content、personaldb、database、moling 均为 up。
- 浏览器通过日常 5778 入口实际读取模板列表与素材，卡片显示且点击后进入 selected 状态，编辑器入口正常。仅验收浏览器身份使用固定夹具，模板数据与资源未被模拟。
- 未修改已确认候选的代码或素材，没有提交、推送、合并或部署。

证据文件：`before.json`、`proxy-probe.json`、`after-ready-final.json`、`browser/runtime-summary.json` 和 `browser/runtime-template-selected.png`。`after-http.json` 保留首次重启后代理问题尚未恢复的中间观测，以最终就绪结果为准。

用户可刷新 [日常模板选择页](http://127.0.0.1:5778/app) 查看新增卡片。已经打开的页面需要重新请求列表，必要时使用 Ctrl+F5。

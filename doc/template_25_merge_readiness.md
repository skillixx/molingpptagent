# template_25 远程交付与 main 合并评估

## 范围

交付分支为 `codex/blueblack-city-pitch-template`，审查基线为远程 `main` 的 `958d267bbf5ea008397aa7425ec3e726424f2825`。

包含模板注册、24 个可编辑版式、五张背景与封面、确定性构建器、相关渲染兼容规则、专项测试、验收工具及必要文档。只按明确文件清单提交，不包含其他模板的未跟踪产物、原始参考文件、运行日志或大体积本地导出物。

用户已确认原 T8 候选 `template25-da624b852daa`。下述审查修正保留原模板 JSON、封面、图片和 24 页固定样稿的输出，历史确认记录不被重写。

## 审查修正

1. 专项布局收到一一对应的业务图片时，如果自身没有对应图片槽，保序降级为普通图文页，避免返回成功却丢图。
2. 在标题归一化后按专项实际文字槽位判断容量；放不下时降级并无损分页。已能容纳完整内容的专项页不再被普通正文容量估算拆坏。
3. 指标缺少可选说明时只删除空说明框，保留名称和数值所在业务组；已覆盖 template_21～template_25。
4. 浏览器换图检查按实际页面 ID 定位，支持同一版式在文档中出现多次。
5. 为正式 `template_25.json` 固定 LF，保持跨平台构建产物字节稳定。

前两项仅在模板显式启用 `unsupportedLayoutPolicy=ordinary` 时生效；旧模板默认分页路径不变。对齐、字体、背景和版式几何没有发生变更。

## 验证

| 检查 | 结果 |
|---|---|
| 模板专项、公共渲染、资源与 template_21～24 回归 | 302 passed，1 deselected |
| 仅含暂存文件的独立副本 | 同一检查再次得到 302 passed，1 deselected；模板重建字节一致 |
| 独立合并前复核 | 已报告的丢图、长正文和对比容量边界问题均复现后修复，无剩余已确认阻塞项 |
| 原确认成品 | 24 版式 JSON、封面和五张图片与原确认哈希一致；原 24 页固定样稿渲染结果相同 |
| 修正路径浏览器验证 | 11 页固定输入通过编辑、换图、保存重开、PPTX 往返及四视口检查 |
| 修正路径文字样式 | 72 个文字对象在往返后保留内容、对齐和字重 |
| GitHub 设置快照 | main 未启用分支保护，未发现生效分支规则或 Actions 工作流；没有配置中的远程检查结果 |

排除的 `test_template_23_reference_registration_and_cover_are_available` 是远程 main 已有、未修改的测试，依赖当前机器缺失的桌面“星空风格(1).pptx”。没有制造替代附件或将排除项计为通过。

## 合并判断

**可以合并到 main。** 功能提交 `193c2cedb2962bfdcf4fb6d7d811f814a9dd9c23` 已推送到上述远程分支，GitHub API 已核对该提交与本地一致。检查时远程 main 仍为本文件的审查基线；功能提交领先 1 个提交、落后 0 个提交，`git merge-tree --write-tree origin/main HEAD` 无冲突，远程 main 是功能提交的祖先，可快进合并。

代码审查与本地验证未发现剩余合并阻断。本评估后的文档记录提交不改变已验证代码。实际合并未执行。

仓库当前没有 Actions 工作流，因此不能把本地通过表述为“远程 CI 通过”。若远程 main、提交内容或分支规则发生变化，应重验对应影响。

本次授权包括提交、推送和合并判断，不包括创建 PR 或实际合并到 main，也不包括生产构建、部署或其他生产操作。

## 证据入口

- [验收与复现说明](./assets/template_25_qa/README.md)
- [交付验证摘要](./assets/template_25_qa/ship-verification.json)
- [测试记录](./assets/template_25_qa/ship-tests.xml)
- [新路径浏览器摘要](./assets/template_25_qa/ship-browser/summary.json)
- [新路径往返样式](./assets/template_25_qa/ship-roundtrip-style.json)
- [原人工确认记录](./assets/template_25_qa/closure.json)

# 生产模板契约

本文件在模板实现、结构审计或修复时读取。规格是页面数量、库存和容量的权威来源；本文件只定义不随模板实例变化的协议。

## 顶层结构

模板 JSON 必须是对象，至少包含：

```json
{
  "id": "template_<正整数>",
  "title": "可读模板名称",
  "width": 1000,
  "height": 562.5,
  "theme": {},
  "slides": [],
  "metadata": {}
}
```

画布尺寸、标题和页面库存必须匹配批准规格，不把示例值当作默认值。

## 页面协议

- 页面 `id` 在模板内唯一且稳定。
- 页面 `type` 必须属于规格声明的类型；常见类型是 `cover`、`contents`、`transition`、`content`、`end`。
- 每页 `elements` 是数组；元素 `id` 在整个模板内全局唯一。
- 规格的生产页面库存必须与 JSON 精确一致。
- `metadata.mvpSlideIds` 中每个 ID 必须真实存在且不重复；集合应与规格的 MVP 声明一致。

## 文本槽位

可由 renderer 填充的文本元素使用明确的 `textType`，例如：

- `title`：页面标题；
- `content`：摘要或正文；
- `item`：目录项或内容项；
- `itemNumber`：目录编号；
- `partNumber`：章节编号。

视觉标签可以不作为语义槽，但不得伪装成可填充内容。不得依靠低于规格最小字号来容纳超量文本；长文本必须按 renderer 协议无损分页，连接分页结果应保持原字符与顺序。

## 图片槽位

- Agent 可替换的内容图片必须标记 `imageType: content`。
- 固定背景和装饰必须标记 `imageType: decoration`。
- 内容图保持独立可替换，不与装饰错误共享分组。
- 装饰图不能被语义内容图片替换。
- 严格图片布局的内容图数量、内容项数量和版式容量必须一致；过量或缺失尺寸应产生明确错误。
- 横图、竖图和方图都应按安全区裁切，不拉伸失真。

## 资源协议

- 发布资源通过 `/api/data/<安全文件名>` 引用。
- 路径文件名必须与目标模板命名空间一致。
- JSON 禁止本机绝对路径、`file://`、`.codex-tmp`、`.codex_tmp`、大 Base64/Data URL 和目录穿越片段。
- 发布目录中目标模板的素材集合必须与 JSON 引用集合一致；封面 `<template-id>.jpg` 单独校验。
- 不保留无引用的目标模板发布素材。

## 禁止内容

生产 JSON 不得包含：

- `Lorem ipsum`、`点击添加`、`XXX` 等示例占位文本；
- 旧模板的资源命名空间；
- 未授权 Logo、人物肖像、付费素材或版权不明内容；
- 未经验证的大 Base64 图片；
- 临时文件路径或用户本机目录。

## Renderer 修改边界

先用真实测试证明当前 renderer 无法满足批准规格，再做最小兼容性修改。不得为单一模板复制 renderer、绕过公共协议或破坏旧模板。修改 renderer 后必须运行通用 renderer/assets 和所有受影响模板回归。

## 确定性校验

- `validate-template-json.py`：顶层结构、库存、ID、槽位和危险路径。
- `audit-template-assets.py`：发布资源集合与图片属性。
- `verify-template-registration.ps1`：唯一注册和封面。

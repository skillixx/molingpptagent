import { describe, expect, it, vi } from 'vitest'

import {
  assertCompleteSlideGeneration,
  expectedSlideCountFromOutline,
  GenerationIncompleteError,
  GenerationStreamError,
  consumeTextResponse,
  isUsableMarkdownOutline,
} from '../generationStream'


describe('generation stream', () => {
  it('根据大纲结构计算完整PPT的最少页数', () => {
    const outline = `# Linux 入门

## 基础认知
### Linux 是什么
- 认识内核
### 常见发行版
- 对比发行版

## 安装配置
### 安装 Linux
- 下载镜像`

    // 封面 + 目录 + 两张章节页 + 三张内容页 + 结束页。
    expect(expectedSlideCountFromOutline(outline)).toBe(8)
  })

  it('空白或不规范大纲不伪造预期页数', () => {
    expect(expectedSlideCountFromOutline('')).toBe(0)
    expect(expectedSlideCountFromOutline('Linux 入门')).toBe(0)
  })

  it('收到结束信号时拒绝把缺页结果标记为完成', () => {
    expect(() => assertCompleteSlideGeneration(5, 18)).toThrow(GenerationIncompleteError)
    expect(() => assertCompleteSlideGeneration(18, 18)).not.toThrow()
    expect(() => assertCompleteSlideGeneration(20, 18)).not.toThrow()
  })

  it('拒绝后端错误响应，不把错误 JSON 当作生成内容', async () => {
    const response = new Response('{"code":"INTERNAL_ERROR"}', { status: 500 })
    const onChunk = vi.fn()

    await expect(consumeTextResponse(response, onChunk)).rejects.toBeInstanceOf(
      GenerationStreamError,
    )
    expect(onChunk).not.toHaveBeenCalled()
  })

  it('按顺序消费成功文本流', async () => {
    const response = new Response('# Linux 入门\n## 安装与配置')
    const chunks: string[] = []

    const content = await consumeTextResponse(response, chunk => chunks.push(chunk))

    expect(content).toBe('# Linux 入门\n## 安装与配置')
    expect(chunks.join('')).toBe(content)
  })

  it.each([
    '我来先搜索一些关于Linux入门教程的资料，以便生成一个全面的大纲。',
    '{"code":"INTERNAL_ERROR","message":"服务暂时不可用"}',
    '普通文本，没有标题结构',
  ])('拒绝不完整大纲：%s', content => {
    expect(isUsableMarkdownOutline(content)).toBe(false)
  })

  it('接受带 Markdown 标题的完整大纲', () => {
    expect(isUsableMarkdownOutline('# Linux 入门教程\n## 1. Linux 简介')).toBe(true)
  })
})

import { readFileSync } from 'node:fs'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AIPPTSlide } from '@/types/AIPPT'
import type { PPTTextElement, Slide } from '@/types/slides'
import useAIPPT from '../useAIPPT'
import message from '@/utils/message'

vi.mock('@/store', () => ({ useSlidesStore: () => ({}) }))
vi.mock('../useAddSlidesOrElements', () => ({ default: () => ({}) }))
vi.mock('../useSlideHandler', () => ({ default: () => ({ isEmptySlide: { value: true } }) }))
vi.mock('@/utils/message', () => ({ default: { error: vi.fn() } }))

// 使用正式模板和公开生成接口，仅隔离画布测量及不参与生成的编辑器状态。
const template = JSON.parse(readFileSync('../backend/main_api/template/template_26.json', 'utf8'))
const text = (slide: Slide, role?: string) => slide.elements
  .filter((e): e is PPTTextElement => e.type === 'text' && (!role || e.textType === role))
  .map(e => new DOMParser().parseFromString(e.content, 'text/html').body.textContent || '')
const input = (count = 4, kind?: string) => ({ type: 'content', data: {
  title: '指标验证', ...(kind ? {} : { layoutKind: 'metrics' }),
  items: Array.from({ length: count }, (_,i) => ({ title: `指标${i}`, text: `说明${i}`, value: i, unit: i ? '小时' : '', ...(kind ? { kind } : {}) })),
} })
const generate = (data: unknown, slides = template.slides) => [...useAIPPT().AIPPTGenerator(slides, [data as AIPPTSlide])]

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ measureText: (value: string) => ({ width: value.length * 12 }) } as any)
})

describe('独立指标单位的本地生成协议', () => {
  it('四项指标保留零值、独立单位、说明及原始输入', () => {
    const data = input()
    const original = JSON.stringify(data)
    const [slide] = generate(data)
    expect(text(slide, 'itemNumber')).toEqual(['0', '1', '2', '3'])
    expect(text(slide, 'itemUnit')).toEqual(['', '小时', '小时', '小时'])
    expect(text(slide, 'itemTitle')).toEqual(data.data.items.map(i => i.title))
    expect(text(slide, 'item')).toEqual(data.data.items.map(i => i.text))
    expect(JSON.stringify(data)).toBe(original)
  })

  it.each(['metric', 'number', 'stat'])('识别 kind=%s 的指标输入', kind => {
    expect(text(generate(input(4, kind))[0], 'itemNumber')).toEqual(['0', '1', '2', '3'])
  })

  it('三项回退正文仍保留数值单位与说明', () => {
    const data = input(3)
    const original = JSON.stringify(data)
    const slides = generate(data)
    const contents = slides.flatMap(s => text(s, 'item')).join('\n')
    expect(contents).toContain('0')
    expect(contents).toContain('1小时')
    expect(contents).toContain('2小时')
    data.data.items.forEach(i => expect(contents).toContain(i.text))
    expect(slides.flatMap(s => text(s, 'itemUnit'))).toEqual([])
    expect(JSON.stringify(data)).toBe(original)
  })

  it.each([1, 5, 13])('%s 项指标回退保留每一项而不留下单项模板示例', count => {
    const data = input(count)
    const content = generate(data).flatMap(s => text(s)).join('\n')
    data.data.items.forEach(item => {
      expect(content).toContain(item.title)
      expect(content).toContain(`${item.value}${item.unit}`)
      expect(content).toContain(item.text)
    })
    expect(content).not.toContain('安全要点')
  })

  it('普通正文即使指标库存在前也不会被填入指标示例页', () => {
    const data = input()
    delete (data.data as any).layoutKind
    const slides = [...template.slides].sort((a,b) => Number(b.metricUnitField === 'unit') - Number(a.metricUnitField === 'unit'))
    expect(text(generate(data, slides)[0], 'itemUnit')).toEqual([])
  })

  it('指标角色按业务组绑定，不依赖对象存储顺序', () => {
    const slides = structuredClone(template.slides)
    const metrics = slides.find((s: any) => s.metricUnitField === 'unit')
    metrics.elements.reverse()
    const [slide] = generate(input(), slides)
    const titles = slide.elements.filter((e): e is PPTTextElement => e.type === 'text' && e.textType === 'itemTitle')
    for (const title of titles) {
      const group = { ...slide, elements: slide.elements.filter(e => e.groupId === title.groupId) }
      const index = Number(text(group, 'itemTitle')[0].replace('指标', ''))
      expect(text(group, 'itemNumber')).toEqual([String(index)])
      expect(text(group, 'item')).toEqual([`说明${index}`])
    }
  })

  it('null 单位只清空单位框，说明和数值仍存在', () => {
    const data = input() as any
    data.data.items.forEach((item: any) => { item.unit = null })
    const [slide] = generate(data)
    expect(text(slide, 'itemUnit')).toEqual(['', '', '', ''])
    expect(text(slide, 'itemNumber')).toEqual(['0', '1', '2', '3'])
    expect(text(slide, 'item')).toEqual(['说明0', '说明1', '说明2', '说明3'])
  })

  it.each([null, true, {}, Number.NaN, Number.POSITIVE_INFINITY])('无效数值 %s 明确失败而不伪造指标', value => {
    const data = input() as any
    data.data.items[0].value = value
    expect(() => generate(data)).toThrow('指标缺少有效名称或数值')
  })

  it('未声明独立单位协议的历史库存保持原行为', () => {
    const metrics = structuredClone(template.slides.find((s: any) => s.metricUnitField === 'unit'))
    delete metrics.metricUnitField
    const [slide] = generate(input(), [metrics])
    expect(text(slide, 'itemNumber')).toEqual(['01', '03', '02', '04'])
    expect(text(slide, 'itemUnit')).toEqual(['%', '%', '%', '%'])
  })

  it.each([3, 4])('%s 项指标携带业务图时显示明确错误且不返回丢图结果', count => {
    const data = { ...input(count), images: [{ src: 'https://example.invalid/business.png', width: 1200, height: 800 }] }
    const original = JSON.stringify(data)
    expect(() => generate(data)).toThrow('本地指标生成暂不支持同时包含业务图片，请使用云端生成或将图片拆成独立图文页')
    expect(message.error).toHaveBeenCalledWith('本地指标生成暂不支持同时包含业务图片，请使用云端生成或将图片拆成独立图文页')
    expect(JSON.stringify(data)).toBe(original)
  })

  it('普通四项指标填充不改变任何图片装饰或非文字字段', () => {
    const original = template.slides.find((s: any) => s.metricUnitField === 'unit') as Slide
    const [slide] = generate(input())
    expect(slide.elements.filter(e => e.type !== 'text')).toEqual(original.elements.filter(e => e.type !== 'text'))
    // 文字只更新内容和既有字号适配字段，保持角色、位置、业务组及尺寸。
    for (const element of slide.elements) {
      const source = original.elements.find(e => e.id === element.id)!
      const { content: _content, lineHeight: _lineHeight, ...rest } = element as PPTTextElement
      const { content: _sourceContent, lineHeight: _sourceLineHeight, ...sourceRest } = source as PPTTextElement
      expect(rest).toEqual(sourceRest)
    }
  })
})

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { PPTLineElement, Slide } from '@/types/slides'
import { useSlidesStore } from '@/store'
import useExport from '@/hooks/useExport'

const { addShape } = vi.hoisted(() => ({ addShape: vi.fn() }))
vi.mock('pptxgenjs', () => ({ default: class {
  layout = ''
  addSlide() { return { addShape } }
  write() { return Promise.resolve(new Blob(['pptx-test'])) }
} }))
vi.mock('file-saver', () => ({ saveAs: vi.fn() }))

const line = (extra: Partial<PPTLineElement> = {}): PPTLineElement => ({
  id: 'line-fixture', type: 'line', left: 20, top: 40, start: [0, 0], end: [100, 0],
  width: 2, color: '#7088BF', style: 'solid', points: ['', ''], ...extra,
})

async function exportLine(element: PPTLineElement) {
  const slides: Slide[] = [{ id: 'line-slide', elements: [element] }]
  await useExport().exportPPTX(slides, false, true)
  return addShape.mock.calls[0]
}

describe('PPTX 原生直线导出', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useSlidesStore().setViewportSize(1000)
    addShape.mockClear()
  })

  it.each([
    { start: [0, 0], end: [100, 0], x: .2, y: .4, w: 1, h: 0, flipH: false, flipV: false },
    { start: [0, 0], end: [0, 100], x: .2, y: .4, w: 0, h: 1, flipH: false, flipV: false },
    { start: [100, 0], end: [0, 0], x: .2, y: .4, w: 1, h: 0, flipH: true, flipV: false },
    { start: [0, 100], end: [0, 0], x: .2, y: .4, w: 0, h: 1, flipH: false, flipV: true },
    { start: [100, 0], end: [0, 80], x: .2, y: .4, w: 1, h: .8, flipH: true, flipV: false },
    { start: [25, 15], end: [85, 65], x: .45, y: .55, w: .6, h: .5, flipH: false, flipV: false },
  ])('保留水平、垂直及斜线的原生类型和方向：%j', async fixture => {
    const [kind, options] = await exportLine(line({ start: [fixture.start[0], fixture.start[1]], end: [fixture.end[0], fixture.end[1]] }))
    // 水平自定义路径的高度为零，重新导入会成为不可见图形；必须写出原生 line。
    expect(kind).toBe('line')
    for (const key of ['x', 'y', 'w', 'h', 'flipH', 'flipV'] as const) expect(options[key]).toBe(fixture[key])
    expect(options.points).toBeUndefined()
  })

  it('保留直线的颜色、线宽和箭头方向', async () => {
    const [, options] = await exportLine(line({ points: ['arrow', ''], style: 'dashed' }))
    expect(options.line).toMatchObject({ color: '#7088bf', beginArrowType: 'arrow', endArrowType: 'none', dashType: 'dash' })
    expect(options.line.width).toBeCloseTo(1.44)
  })

  it.each([
    line({ broken: [50, 0], end: [100, 100] }),
    line({ broken2: [50, 50], end: [100, 100] }),
    line({ curve: [50, 80] }),
    line({ cubic: [[30, 60], [70, 60]] }),
  ])('保留折线和曲线现有自定义几何路径', async element => {
    const [kind, options] = await exportLine(element)
    expect(kind).toBe('custGeom')
    expect(options.points.length).toBeGreaterThan(1)
  })
})

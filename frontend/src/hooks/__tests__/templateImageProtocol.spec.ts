import { describe, expect, it } from 'vitest'

import { fillContentImageSlot, getImageExportSizing, getImageObjectFit, getImageReplacementProps, isContentImageSlot, isReplaceableTemplateImage } from '../templateImageProtocol'


describe('template image protocol', () => {
  it('显式协议只允许替换content图片并保护decoration', () => {
    const elements = [
      { type: 'image', id: 'content', imageType: 'content' },
      { type: 'image', id: 'decoration', imageType: 'decoration' },
    ] as any[]

    expect(isReplaceableTemplateImage(elements[0], elements)).toBe(true)
    expect(isReplaceableTemplateImage(elements[1], elements)).toBe(false)
    expect(isContentImageSlot(elements[0])).toBe(true)
    expect(isContentImageSlot(elements[1])).toBe(false)
  })

  it('没有显式协议时保持历史模板图片类型兼容', () => {
    const elements = [
      { type: 'image', id: 'figure', imageType: 'itemFigure' },
      { type: 'image', id: 'background', imageType: 'background' },
    ] as any[]

    expect(isReplaceableTemplateImage(elements[0], elements)).toBe(true)
    expect(isReplaceableTemplateImage(elements[1], elements)).toBe(true)
    expect(isContentImageSlot(elements[0])).toBe(true)
  })

  it('非图片元素和未标注图片都不能进入替换链路', () => {
    const elements = [
      { type: 'text', id: 'title', content: '标题' },
      { type: 'image', id: 'unmarked', src: '/static/original.png' },
    ] as any[]

    expect(isReplaceableTemplateImage(elements[0], elements)).toBe(false)
    expect(isReplaceableTemplateImage(elements[1], elements)).toBe(false)
    expect(isContentImageSlot(elements[0])).toBe(false)
    expect(isContentImageSlot(elements[1])).toBe(false)
  })

  it('图文项替换后使用居中cover适配并清理旧裁剪', () => {
    const slot = {
      type: 'image', id: 'content', imageType: 'content', src: '/old.jpg',
      width: 430, height: 98, clip: { shape: 'rect', range: [[10, 0], [90, 100]] },
    } as any

    expect(fillContentImageSlot(slot, 'https://example.invalid/portrait.jpg')).toMatchObject({
      src: 'https://example.invalid/portrait.jpg',
      width: 430,
      height: 98,
      imageFit: 'cover',
      clip: undefined,
    })
  })

  it.each([
    ['竖图', 'https://example.invalid/portrait.jpg'],
    ['横图', 'https://example.invalid/landscape.jpg'],
  ])('%s内容图在PPTX导出时继续使用cover', (_label, src) => {
    const slot = fillContentImageSlot({
      type: 'image', id: 'content', imageType: 'content', src: '/old.jpg',
      width: 430, height: 98,
    } as any, src)

    expect(getImageExportSizing(slot, 4.3, 0.98)).toEqual({
      type: 'cover',
      w: 4.3,
      h: 0.98,
    })
  })

  it('显式clip优先于imageFit，导出器不会重复应用cover', () => {
    const slot = {
      type: 'image', id: 'content', imageType: 'content', src: '/old.jpg',
      width: 430, height: 98, imageFit: 'cover',
      clip: { shape: 'rect', range: [[10, 0], [90, 100]] },
    } as any

    expect(getImageExportSizing(slot, 4.3, 0.98)).toBeUndefined()
    expect(getImageObjectFit(slot)).toBe('fill')
  })

  it('没有显式clip时编辑器继续应用cover', () => {
    const slot = fillContentImageSlot({
      type: 'image', id: 'content', imageType: 'content', src: '/old.jpg',
      width: 430, height: 98,
    } as any, 'https://example.invalid/content.jpg')

    expect(getImageObjectFit(slot)).toBe('cover')
  })

  it('编辑器替换圆形横图时保留椭圆裁切和原画框', () => {
    const slot = {
      type: 'image', id: 'circle', imageType: 'content', src: '/old.jpg',
      left: 120, top: 150, width: 202, height: 202, fixedRatio: false, rotate: 0,
      clip: { shape: 'ellipse', range: [[0, 0], [100, 100]] },
    } as any

    const props = getImageReplacementProps(slot, 'data:image/jpeg;base64,new', 1920, 1080)

    expect(props).toMatchObject({
      src: 'data:image/jpeg;base64,new',
      left: 120,
      top: 150,
      width: 202,
      height: 202,
      clip: { shape: 'ellipse' },
    })
    expect(props.clip?.range[0][0]).toBeGreaterThan(0)
    expect(props.clip?.range[0][1]).toBe(0)
  })

  it('编辑器替换未裁剪图片时保持历史居中缩放行为', () => {
    const slot = {
      type: 'image', id: 'plain', src: '/old.jpg',
      left: 100, top: 100, width: 200, height: 100, fixedRatio: false, rotate: 0,
    } as any

    expect(getImageReplacementProps(slot, 'data:image/png;base64,new', 1000, 1000)).toEqual({
      src: 'data:image/png;base64,new',
      left: 150,
      top: 100,
      width: 100,
      height: 100,
    })
  })
})

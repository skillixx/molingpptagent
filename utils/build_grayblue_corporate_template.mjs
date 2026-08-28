#!/usr/bin/env node

/**
 * 基于已验证的 template_12 语义骨架构建灰蓝企业宣传模板。
 *
 * 处理内容：
 * 1. 保留目录容量、无损分页、图片隔离和确定性变体协议；
 * 2. 调整为2封面、6目录、2章节、6内容、2结束页；
 * 3. 替换为灰蓝企业专属色板、原创素材、示例文案和唯一ID；
 * 4. 重建第二封面、双图文页和联系方式结束页。
 */

import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const [, , sourceArg, outputArg] = process.argv

if (!sourceArg || !outputArg) {
  console.error('用法: node build_grayblue_corporate_template.mjs <template_12.json> <template_13.json>')
  process.exit(1)
}

const sourcePath = resolve(sourceArg)
const outputPath = resolve(outputArg)
const template = JSON.parse(await readFile(sourcePath, 'utf8'))
const clone = value => JSON.parse(JSON.stringify(value))

const sourceImageSlide = clone(template.slides.find(slide => slide.id === 'content-image-1'))
const sourceEndSlide = clone(template.slides.find(slide => slide.id === 'end-landscape'))

const slideIdMap = new Map([
  ['cover-landscape', 'cover-architectural'],
  ['cover-fan', 'cover-light-image'],
  ['transition-seal', 'transition-facet'],
  ['transition-moon', 'transition-arch'],
  ['content-text-4-alt', 'content-image-2'],
  ['content-metrics-3', 'end-contact'],
  ['end-landscape', 'end-corporate'],
])

const colorMap = new Map([
  ['#223841', '#313A51'],
  ['#5F7F87', '#5C6E9A'],
  ['#B8C9CA', '#D5DCE5'],
  ['#B33A32', '#F0D3A9'],
  ['#B79A63', '#F0D3A9'],
  ['#F4F1EA', '#F4F6F8'],
  ['#5F6F73', '#687386'],
  ['#AEBDB8', '#D5DCE5'],
])

const textMap = new Map([
  ['ORIENTAL INK · QUIET RHYTHM', 'GRAY BLUE · CORPORATE CLARITY'],
  ['ORIENTAL INK', 'CORPORATE CLARITY'],
  ['INK · SPACE · INSIGHT', 'STRUCTURE · EVIDENCE · ACTION'],
  ['INK WASH · LASTING IMPRESSION', 'CLARITY · TRUST · NEXT STEP'],
  ['东方水墨雅韵演示模板', '灰蓝企业宣传演示模板'],
  ['让东方意境承载清晰表达', '让企业价值被清晰看见'],
  ['让水墨留白承载核心观点', '用稳定结构呈现企业价值'],
  ['用克制布局连接观点、证据与行动', '用专业表达连接战略、证据与行动'],
  ['让东方意境留下余韵', '让清晰表达推动下一步行动'],
])

const replaceAll = value => {
  let output = String(value)
  for (const [source, target] of colorMap) output = output.replaceAll(source, target)
  for (const [source, target] of textMap) output = output.replaceAll(source, target)
  output = output.replaceAll('font-family: 宋体', 'font-family: 微软雅黑')
  output = output.replaceAll('font-family: 华文黑体', 'font-family: 微软雅黑')
  output = output.replaceAll('font-family: 方正兰亭黑简体', 'font-family: 微软雅黑')
  return output
}

const renameId = value => {
  if (!value) return value
  return `t13-${String(value)
    .replace(/^t12-/, '')
    .replaceAll('ink-circle', 'facet-ribbon')
    .replaceAll('mountain-band', 'arch-line')
    .replaceAll('brush-accent', 'paper-grain')
    .replaceAll('ink-accent', 'facet-accent')
    .replaceAll('ink', 'corporate')}`
}

const sourceFilename = src => String(src || '').split('/').pop()

const decorationAsset = (slide, source) => {
  if (source.includes('bg_cover')) return 'template_13_asset_bg_cover_v1.jpg'
  if (source.includes('bg_section')) return 'template_13_asset_bg_section_v1.jpg'
  if (source.includes('bg_end')) return 'template_13_asset_bg_end_v1.jpg'
  if (source.includes('mountain_band')) return 'template_13_asset_arch_line_v1.png'
  if (source.includes('brush_accent')) {
    return ['cover', 'transition', 'end'].includes(slide.type)
      ? 'template_13_asset_facet_ribbon_v1.png'
      : 'template_13_asset_paper_grain_v1.png'
  }
  if (source.includes('ink_circle') || source.includes('folding_fan') || source.includes('seal_red')) {
    return 'template_13_asset_facet_ribbon_v1.png'
  }
  return source
}

const setImagePosition = (slide, element, assetName, counters) => {
  if (element.imageType === 'content') {
    element.requireSourceDimensions = true
    return
  }

  element.fixedRatio = true
  if (assetName.includes('_bg_')) {
    Object.assign(element, { left: 0, top: 0, width: 1000, height: 562.5, fixedRatio: false })
    return
  }

  if (assetName.includes('paper_grain')) {
    Object.assign(element, { left: 0, top: 0, width: 1000, height: 562.5, fixedRatio: false })
    return
  }

  if (assetName.includes('arch_line')) {
    const width = slide.type === 'cover' ? 520 : 430
    const height = width * 900 / 1400
    Object.assign(element, { left: 1000 - width, top: 562.5 - height, width, height })
    return
  }

  if (assetName.includes('facet_ribbon')) {
    const index = counters.facet++
    const width = slide.type === 'cover' ? 270 : slide.type === 'transition' ? 235 : 190
    const height = width * 900 / 1400
    Object.assign(element, {
      left: index % 2 === 0 ? 1000 - width - 24 : 28,
      top: index % 2 === 0 ? 26 : 562.5 - height - 24,
      width,
      height,
    })
  }
}

const slotType = element => element.textType || element.text?.type || null

const cloneWith = (element, id, overrides = {}) => ({
  ...clone(element),
  id,
  ...overrides,
})

const buildDoubleImageSlide = () => {
  const slide = clone(sourceImageSlide)
  slide.id = 'content-image-2'
  slide.layoutKind = '2-image-text'
  const keep = slide.elements.filter(element => !element.groupId && element.imageType !== 'content')
  const frame = sourceImageSlide.elements.find(element => element.id.includes('image-frame'))
  const image = sourceImageSlide.elements.find(element => element.imageType === 'content')
  const number = sourceImageSlide.elements.find(element => slotType(element) === 'itemNumber')
  const title = sourceImageSlide.elements.find(element => slotType(element) === 'itemTitle')
  const body = sourceImageSlide.elements.find(element => slotType(element) === 'item')

  for (let index = 0; index < 2; index += 1) {
    const groupId = `t12-content-image-2-item-${index + 1}`
    const left = 66 + index * 462
    keep.push(cloneWith(frame, `t12-double-image-frame-${index + 1}`, {
      groupId,
      left,
      top: 172,
      width: 198,
      height: 172,
    }))
    keep.push(cloneWith(image, `t12-double-content-image-${index + 1}`, {
      groupId: undefined,
      left: left + 10,
      top: 182,
      width: 178,
      height: 152,
      strictImageCount: true,
      requireSourceDimensions: true,
    }))
    keep.push(cloneWith(number, `t12-double-item-number-${index + 1}`, {
      groupId,
      left: left + 218,
      top: 176,
      width: 54,
      height: 38,
    }))
    keep.push(cloneWith(title, `t12-double-item-title-${index + 1}`, {
      groupId,
      left: left + 218,
      top: 218,
      width: 205,
      height: 66,
    }))
    keep.push(cloneWith(body, `t12-double-item-body-${index + 1}`, {
      groupId,
      left: left + 218,
      top: 292,
      width: 205,
      height: 142,
    }))
  }
  slide.elements = keep
  return slide
}

const buildContactEndSlide = () => {
  const slide = clone(sourceEndSlide)
  slide.id = 'end-contact'
  slide.variantMode = 'deterministic'
  const title = slide.elements.find(element => slotType(element) === 'title')
  const content = slide.elements.find(element => slotType(element) === 'content')
  if (title) Object.assign(title, { left: 100, top: 128, width: 800, height: 120 })
  if (content) Object.assign(content, { left: 100, top: 278, width: 800, height: 170 })
  return slide
}

template.slides = template.slides.map(slide => {
  if (slide.id === 'content-text-4-alt') return buildDoubleImageSlide()
  if (slide.id === 'content-metrics-3') return buildContactEndSlide()
  return slide
})

template.id = 'template_13'
template.title = '灰蓝企业宣传'
template.theme = {
  ...(template.theme || {}),
  themeColors: ['#313A51', '#455273', '#5C6E9A', '#F0D3A9', '#D5DCE5'],
  fontColor: '#222B35',
  fontName: '微软雅黑',
  backgroundColor: '#F4F6F8',
}
template.metadata = {
  ...(template.metadata || {}),
  aspectRatio: '16:9',
  sourceReference: '企业宣传(20).pptx',
  imageSlotMarker: 'imageType=content',
  decorativeImageMarker: 'imageType=decoration',
  assetGeneration: 'built-in imagegen; actual model identifier not exposed',
  mvpSlideIds: [
    'cover-architectural',
    'contents-2',
    'contents-3',
    'contents-4',
    'contents-5',
    'contents-6',
    'contents-10',
    'transition-facet',
    'content-text-2',
    'content-text-3',
    'content-text-4',
    'end-corporate',
  ],
}

for (const slide of template.slides) {
  slide.id = slideIdMap.get(slide.id) || slide.id
  if (slide.id === 'end-contact') slide.type = 'end'
  if (['cover-architectural', 'cover-light-image', 'transition-facet', 'transition-arch', 'end-corporate', 'end-contact'].includes(slide.id)) {
    slide.variantMode = 'deterministic'
  }
  slide.remark = [
    '[Sources]',
    '- User-provided visual reference: 企业宣传(20).pptx',
    '- Original project assets generated for template_13 with built-in imagegen; actual model identifier not exposed',
  ].join('\n')

  const counters = { facet: 0 }
  for (const element of slide.elements) {
    // 克隆页面可能复用源元素ID；加入页面前缀保证全局唯一，同时保持组内关系。
    element.id = renameId(`${slide.id}-${element.id}`)
    if (element.groupId) element.groupId = renameId(`${slide.id}-${element.groupId}`)
    if (element.defaultFontName) element.defaultFontName = '微软雅黑'
    if (element.text?.defaultFontName) element.text.defaultFontName = '微软雅黑'
    if (!element.src) continue

    if (element.imageType === 'content') {
      element.src = '/api/data/template_13_asset_bg_section_v1.jpg'
      element.requireSourceDimensions = true
      continue
    }
    const targetAsset = decorationAsset(slide, sourceFilename(element.src))
    element.src = `/api/data/${targetAsset}`
    setImagePosition(slide, element, targetAsset, counters)
  }

  if (slide.id === 'cover-light-image') {
    // 第二封面增加独立内容图槽；没有图片输入时渲染器仍优先使用第一封面。
    slide.elements.push({
      type: 'shape',
      id: 't13-cover-image-frame-0001',
      left: 686,
      top: 112,
      width: 252,
      height: 330,
      viewBox: [200, 200],
      path: 'M 0 0 L 200 0 L 200 200 L 0 200 Z',
      fill: 'rgba(255,255,255,0.72)',
      fixedRatio: false,
      rotate: 0,
      outline: { color: '#D5DCE5', width: 1, style: 'solid' },
      lock: true,
    }, {
      type: 'image',
      id: 't13-cover-content-image-0001',
      left: 698,
      top: 124,
      width: 228,
      height: 306,
      src: '/api/data/template_13_asset_bg_section_v1.jpg',
      imageType: 'content',
      requireSourceDimensions: true,
      fixedRatio: false,
      rotate: 0,
    })
    const title = slide.elements.find(element => slotType(element) === 'title')
    const content = slide.elements.find(element => slotType(element) === 'content')
    if (title) {
      Object.assign(title, { left: 76, top: 190, width: 600, height: 105 })
      title.content = title.content.replace(/font-size:\s*[0-9.]+px/g, 'font-size: 50px')
    }
    if (content) Object.assign(content, { left: 78, top: 330, width: 570, height: 90 })
  }

  if (slide.id === 'cover-architectural') {
    // 深色主封面使用高对比文字，保证投影和缩略图场景都可读。
    for (const element of slide.elements) {
      if (!element.content) continue
      const color = ['title', 'content'].includes(slotType(element)) ? '#FFFFFF' : '#F0D3A9'
      element.content = element.content.replace(/color:\s*#[0-9A-Fa-f]{6}/g, `color: ${color}`)
    }
  }

  if (slide.id === 'transition-facet') {
    const title = slide.elements.find(element => slotType(element) === 'title')
    const content = slide.elements.find(element => slotType(element) === 'content')
    if (title) Object.assign(title, { left: 420, top: 190, width: 500, height: 120 })
    if (content) Object.assign(content, { left: 424, top: 332, width: 460, height: 128 })
  }

  if (slide.type === 'end') {
    // 结束页背景亮度变化较大，增加半透明底板保证标题和正文对比度。
    slide.elements.splice(1, 0, {
      type: 'shape',
      id: `t13-${slide.id}-end-safe-panel`,
      left: 110,
      top: 108,
      width: 780,
      height: 350,
      viewBox: [200, 200],
      path: 'M 0 0 L 200 0 L 200 200 L 0 200 Z',
      fill: 'rgba(244,246,248,0.78)',
      fixedRatio: false,
      rotate: 0,
      outline: { color: 'rgba(244,246,248,0.78)', width: 0, style: 'solid' },
      lock: true,
    })
    const endTitle = slide.elements.find(element => slotType(element) === 'title')
    const endContent = slide.elements.find(element => slotType(element) === 'content')
    if (endTitle) Object.assign(endTitle, { left: 120, top: 184, width: 760, height: 112 })
    if (endContent) Object.assign(endContent, { left: 160, top: 326, width: 680, height: 104 })
  }
}

const serialized = replaceAll(JSON.stringify(template, null, 2))
await writeFile(outputPath, `${serialized}\n`, 'utf8')

#!/usr/bin/env node

/**
 * 基于已验证的 template_11 语义骨架构建东方水墨雅韵模板。
 *
 * 处理内容：
 * 1. 保留 18 页、12 页 MVP、目录容量、分页和图片协议；
 * 2. 替换为 template_12 的原创水墨素材；
 * 3. 统一东方水墨色板、示例文案、来源记录和唯一 ID；
 * 4. 按素材宽高比重新布置背景、山形、笔触、折扇、圆环和印章。
 */

import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const [, , sourceArg, outputArg] = process.argv

if (!sourceArg || !outputArg) {
  console.error('用法: node build_chinese_ink_template.mjs <template_11.json> <template_12.json>')
  process.exit(1)
}

const sourcePath = resolve(sourceArg)
const outputPath = resolve(outputArg)
const template = JSON.parse(await readFile(sourcePath, 'utf8'))

const slideIdMap = new Map([
  ['cover-fluid', 'cover-landscape'],
  ['cover-orbit', 'cover-fan'],
  ['transition-fluid', 'transition-seal'],
  ['transition-number', 'transition-moon'],
  ['content-conclusion-1', 'content-statement-1'],
  ['content-flow-4', 'content-text-4-alt'],
  ['end-fluid', 'end-landscape'],
])

const colorMap = new Map([
  ['#193342', '#223841'],
  ['#28688A', '#5F7F87'],
  ['#86B5C4', '#B8C9CA'],
  ['#A9B9A8', '#AEBDB8'],
  ['#C8C2A4', '#B79A63'],
  ['#F8F8F3', '#F4F1EA'],
  ['#F5F2DF', '#F4F1EA'],
  ['#123B58', '#223841'],
  ['#62747C', '#5F6F73'],
])

const textMap = new Map([
  ['BLUE MARBLE · CREATIVE FLOW', 'ORIENTAL INK · QUIET RHYTHM'],
  ['FLUID CREATIVE', 'ORIENTAL INK'],
  ['BLUE · FLOW · INSIGHT', 'INK · SPACE · INSIGHT'],
  ['KEEP IDEAS FLOWING', 'INK WASH · LASTING IMPRESSION'],
  ['蓝金流体创意演示模板', '东方水墨雅韵演示模板'],
  ['让创意沿着清晰结构自然展开', '让东方意境承载清晰表达'],
  ['让复杂信息形成清晰流向', '让水墨留白承载核心观点'],
  ['用稳定结构连接观点、证据与行动', '用克制布局连接观点、证据与行动'],
  ['让好创意继续流动', '让东方意境留下余韵'],
])

const replaceAll = value => {
  let output = String(value)
  for (const [source, target] of colorMap) output = output.replaceAll(source, target)
  for (const [source, target] of textMap) output = output.replaceAll(source, target)
  output = output.replaceAll('font-family: 方正清刻本悦宋简体', 'font-family: 微软雅黑')
  output = output.replaceAll('font-family: 宋体', 'font-family: 微软雅黑')
  return output
}

const renameId = value => {
  if (!value) return value
  const text = String(value)
    .replace(/^t11-/, '')
    .replaceAll('fluid-corner-ivory', 'ink-circle')
    .replaceAll('fluid-corner-blue', 'mountain-band')
    .replaceAll('fluid-ribbon', 'brush-accent')
    .replaceAll('marble-orb', 'ink-accent')
    .replaceAll('fluid', 'ink')
    .replaceAll('orbit', 'fan')
  return `t12-${text}`
}

const sourceFilename = src => String(src || '').split('/').pop()

const decorationAsset = (slide, source) => {
  if (source.includes('bg_cover')) return 'template_12_asset_bg_cover_v1.jpg'
  if (source.includes('bg_section')) return 'template_12_asset_bg_section_v1.jpg'
  if (source.includes('bg_end')) return 'template_12_asset_bg_end_v1.jpg'
  if (source.includes('corner_ivory')) return 'template_12_asset_ink_circle_v1.png'
  if (source.includes('corner_blue')) return 'template_12_asset_mountain_band_v1.png'
  if (source.includes('fluid_ribbon')) return 'template_12_asset_brush_accent_v1.png'
  if (source.includes('marble_orb')) {
    return slide.id === 'cover-fan'
      ? 'template_12_asset_folding_fan_v1.png'
      : 'template_12_asset_seal_red_v1.png'
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

  if (assetName.includes('mountain_band')) {
    const width = slide.type === 'cover' ? 520 : slide.type === 'contents' ? 420 : 360
    const height = width * 550 / 1800
    Object.assign(element, {
      left: 1000 - width,
      top: 562.5 - height,
      width,
      height,
    })
    return
  }

  if (assetName.includes('ink_circle')) {
    const size = slide.type === 'cover' ? 210 : slide.type === 'transition' ? 205 : 155
    Object.assign(element, {
      left: slide.type === 'transition' ? 50 : 1000 - size - 45,
      top: slide.type === 'transition' ? 105 : 34,
      width: size,
      height: size,
    })
    return
  }

  if (assetName.includes('brush_accent')) {
    const index = counters.brush++
    const width = index % 2 === 0 ? 360 : 310
    const height = width * 420 / 1800
    Object.assign(element, {
      left: index % 2 === 0 ? 590 : 48,
      top: index % 2 === 0 ? 22 : 562.5 - height - 22,
      width,
      height,
    })
    return
  }

  if (assetName.includes('folding_fan')) {
    Object.assign(element, { left: 700, top: 350, width: 265, height: 170 })
    return
  }

  if (assetName.includes('seal_red')) {
    const size = slide.type === 'cover' ? 70 : slide.type === 'end' ? 64 : 58
    Object.assign(element, {
      left: slide.type === 'cover' ? 78 : 1000 - size - 46,
      top: slide.type === 'cover' ? 448 : 562.5 - size - 38,
      width: size,
      height: size,
    })
  }
}

template.id = 'template_12'
template.title = '东方水墨雅韵'
template.theme = {
  ...(template.theme || {}),
  themeColors: ['#223841', '#5F7F87', '#B8C9CA', '#B33A32', '#B79A63'],
  fontColor: '#223841',
  fontName: '微软雅黑',
  backgroundColor: '#F4F1EA',
}
template.metadata = {
  ...(template.metadata || {}),
  aspectRatio: '16:9',
  sourceReference: '中国风格(01).pptx',
  imageSlotMarker: 'imageType=content',
  decorativeImageMarker: 'imageType=decoration',
  assetGeneration: 'built-in imagegen; actual model identifier not exposed',
}

for (const slide of template.slides) {
  slide.id = slideIdMap.get(slide.id) || slide.id
  slide.remark = [
    '[Sources]',
    '- User-provided visual reference: 中国风格(01).pptx',
    '- Original project assets generated for template_12 with built-in imagegen; actual model identifier not exposed',
  ].join('\n')
  const counters = { brush: 0 }
  for (const element of slide.elements) {
    element.id = renameId(element.id)
    if (element.groupId) element.groupId = renameId(element.groupId)
    if (element.defaultFontName) element.defaultFontName = '微软雅黑'
    if (element.text?.defaultFontName) element.text.defaultFontName = '微软雅黑'
    if (element.src) {
      const source = sourceFilename(element.src)
      if (element.imageType === 'content') {
        // 默认内容图也使用本模板资源，生成时再由 Agent 图片替换。
        element.src = '/api/data/template_12_asset_bg_section_v1.jpg'
        element.requireSourceDimensions = true
      }
      else {
        const targetAsset = decorationAsset(slide, source)
        element.src = `/api/data/${targetAsset}`
        setImagePosition(slide, element, targetAsset, counters)
      }
    }
  }

  if (slide.id === 'transition-seal') {
    // 章节背景的深色山体位于左侧，使用半透明宣纸底板保护任意长度的动态文字。
    slide.elements.splice(1, 0, {
      type: 'shape',
      id: 't12-transition-safe-panel-0001',
      left: 410,
      top: 170,
      width: 550,
      height: 320,
      viewBox: [200, 200],
      path: 'M 0 0 L 200 0 L 200 200 L 0 200 Z',
      fill: 'rgba(244,241,234,0.88)',
      fixedRatio: false,
      rotate: 0,
      outline: { color: 'rgba(244,241,234,0.88)', width: 0, style: 'solid' },
      lock: true,
    })
    const title = slide.elements.find(element => element.textType === 'title')
    const content = slide.elements.find(element => element.textType === 'content')
    if (title) Object.assign(title, { left: 455, top: 205, width: 470, height: 118 })
    if (content) Object.assign(content, { left: 460, top: 335, width: 430, height: 130 })
  }
}

template.metadata.mvpSlideIds = template.metadata.mvpSlideIds.map(id => slideIdMap.get(id) || id)

const serialized = replaceAll(JSON.stringify(template, null, 2))
await writeFile(outputPath, `${serialized}\n`, 'utf8')

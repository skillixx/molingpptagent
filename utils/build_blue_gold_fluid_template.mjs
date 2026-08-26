#!/usr/bin/env node

/**
 * 基于已验证的 template_10 语义骨架重建蓝金流体模板。
 *
 * 处理内容：
 * 1. 保留 18 页、12 页 MVP、容量、分页和图片协议；
 * 2. 替换为 template_11 的原创蓝金流体素材；
 * 3. 统一颜色、字体、示例文字和唯一 ID；
 * 4. 修正不同装饰素材的宽高比和安全区位置。
 */

import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const [, , sourceArg, outputArg] = process.argv

if (!sourceArg || !outputArg) {
  console.error('用法: node build_blue_gold_fluid_template.mjs <template_10.json> <template_11.json>')
  process.exit(1)
}

const sourcePath = resolve(sourceArg)
const outputPath = resolve(outputArg)
const template = JSON.parse(await readFile(sourcePath, 'utf8'))

const slideIdMap = new Map([
  ['cover-growth', 'cover-fluid'],
  ['cover-playful', 'cover-orbit'],
  ['transition-path', 'transition-fluid'],
  ['end-growth', 'end-fluid'],
])

const assetMap = new Map([
  ['template_10_asset_bg_cover_v1.jpg', 'template_11_asset_bg_cover_v1.jpg'],
  ['template_10_asset_bg_section_v1.jpg', 'template_11_asset_bg_section_v1.jpg'],
  ['template_10_asset_bg_end_v1.jpg', 'template_11_asset_bg_end_v1.jpg'],
  ['template_10_asset_children_group_v1.png', 'template_11_asset_marble_orb_v1.png'],
  ['template_10_asset_brush_accent_v1.png', 'template_11_asset_fluid_ribbon_v1.png'],
  ['template_10_asset_school_doodles_v1.png', 'template_11_asset_fluid_corner_ivory_v1.png'],
  ['template_10_asset_leaf_canopy_v1.png', 'template_11_asset_fluid_ribbon_v1.png'],
  ['template_10_asset_grass_wave_v1.png', 'template_11_asset_fluid_corner_blue_v1.png'],
  ['template_10_asset_corner_supplies_v1.png', 'template_11_asset_marble_orb_v1.png'],
])

const colorMap = new Map([
  ['#24332A', '#193342'],
  ['#2F9E5B', '#28688A'],
  ['#49B8D6', '#86B5C4'],
  ['#F9FCFA', '#F8F8F3'],
  ['#DDF4E5', '#F5F2DF'],
  ['#617268', '#62747C'],
  ['#F2C14E', '#C8C2A4'],
  ['#1F6F43', '#123B58'],
  ['#8FD36B', '#A9B9A8'],
])

const textMap = new Map([
  ['LEARNING FOR EVERYONE', 'BLUE MARBLE · CREATIVE FLOW'],
  ['FRESH EDUCATION', 'FLUID CREATIVE'],
  ['LEARNING · GROWTH · FUTURE', 'BLUE · FLOW · INSIGHT'],
  ['KEEP LEARNING · KEEP GROWING', 'KEEP IDEAS FLOWING'],
  ['清新校园教育演示模板', '蓝金流体创意演示模板'],
  ['让每一次学习都有清晰路径', '让创意沿着清晰结构自然展开'],
  ['把知识变成可以抵达的成长', '让复杂信息形成清晰流向'],
  ['用清晰结构连接目标、行动与收获', '用稳定结构连接观点、证据与行动'],
  ['从问题出发，找到成长路径', '从核心问题出发，形成清晰路径'],
  ['本章将连接关键问题、核心证据和下一步行动。', '本章将连接核心问题、关键证据和下一步行动。'],
  ['让成长继续发生', '让好创意继续流动'],
  ['感谢聆听，期待一起把下一步变得更清晰。', '感谢聆听，期待一起把下一步变得更清晰。'],
])

const replaceAll = value => {
  let output = String(value)
  for (const [source, target] of colorMap) output = output.replaceAll(source, target)
  for (const [source, target] of textMap) output = output.replaceAll(source, target)
  return output
}

const renameId = value => {
  if (!value) return value
  const text = String(value)
    .replace(/^t10-/, '')
    .replaceAll('growth', 'fluid')
    .replaceAll('playful', 'orbit')
    .replaceAll('children', 'marble-orb')
    .replaceAll('brush', 'fluid-ribbon')
    .replaceAll('doodles', 'fluid-corner-ivory')
    .replaceAll('leaf', 'fluid-ribbon')
    .replaceAll('grass', 'fluid-corner-blue')
    .replaceAll('supplies', 'marble-orb')
    .replaceAll('green', 'blue')
    .replaceAll('school', 'fluid')
  return `t11-${text}`
}

const sourceFilename = src => String(src || '').split('/').pop()

const mapAsset = src => {
  const source = sourceFilename(src)
  const target = assetMap.get(source)
  return target ? `/api/data/${target}` : src
}

const setDecorationPosition = (slide, element, counters) => {
  const filename = sourceFilename(element.src)
  if (element.imageType === 'content') {
    element.requireSourceDimensions = true
    return
  }

  element.fixedRatio = true
  if (filename.includes('_bg_')) {
    Object.assign(element, { left: 0, top: 0, width: 1000, height: 562.5, fixedRatio: false })
    return
  }

  if (filename.includes('corner_blue')) {
    const size = slide.type === 'cover' ? 330 : 285
    Object.assign(element, { left: 1000 - size, top: 562.5 - size, width: size, height: size })
    return
  }

  if (filename.includes('corner_ivory')) {
    const size = slide.type === 'cover' ? 320 : 245
    Object.assign(element, { left: 1000 - size, top: 0, width: size, height: size })
    return
  }

  if (filename.includes('fluid_ribbon')) {
    const index = counters.ribbon++
    if (index % 2 === 0) {
      Object.assign(element, { left: 555, top: 0, width: 420, height: 117 })
    }
    else {
      Object.assign(element, { left: 45, top: 438, width: 360, height: 100 })
    }
    return
  }

  if (filename.includes('marble_orb')) {
    const index = counters.orb++
    const size = slide.type === 'cover' ? 245 : slide.type === 'end' ? 205 : 135
    const top = index % 2 === 0 ? 562.5 - size - 36 : 32
    Object.assign(element, { left: 1000 - size - 55, top, width: size, height: size })
  }
}

template.id = 'template_11'
template.title = '蓝金流体创意'
template.theme = {
  ...(template.theme || {}),
  themeColors: ['#123B58', '#28688A', '#86B5C4', '#A9B9A8', '#C8C2A4'],
  fontColor: '#193342',
  fontName: '微软雅黑',
  backgroundColor: '#F8F8F3',
}
template.metadata = {
  ...(template.metadata || {}),
  aspectRatio: '16:9',
  sourceReference: '创意风格 (56).pptx',
  imageSlotMarker: 'imageType=content',
  decorativeImageMarker: 'imageType=decoration',
  assetGeneration: 'built-in imagegen; actual model identifier not exposed',
}

for (const slide of template.slides) {
  slide.id = slideIdMap.get(slide.id) || slide.id
  slide.remark = [
    '[Sources]',
    '- User-provided visual reference: 创意风格 (56).pptx',
    '- Original project assets generated for template_11 with built-in imagegen; actual model identifier not exposed',
  ].join('\n')
  const counters = { ribbon: 0, orb: 0 }
  for (const element of slide.elements) {
    element.id = renameId(element.id)
    if (element.groupId) element.groupId = renameId(element.groupId)
    if (element.defaultFontName) element.defaultFontName = '微软雅黑'
    if (element.text?.defaultFontName) element.text.defaultFontName = '微软雅黑'
    if (element.src) {
      element.src = mapAsset(element.src)
      setDecorationPosition(slide, element, counters)
    }
  }
}

template.metadata.mvpSlideIds = template.metadata.mvpSlideIds.map(id => slideIdMap.get(id) || id)

const serialized = replaceAll(JSON.stringify(template, null, 2))
await writeFile(outputPath, `${serialized}\n`, 'utf8')

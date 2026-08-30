#!/usr/bin/env node

/**
 * 构建“星脉科技产品发布”生产模板。
 *
 * 支持两个阶段：
 * - mvp：输出规格声明的 20 页 MVP，用于真实生成门禁；
 * - production：输出完整 39 页生产库存。
 */

import { writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const args = process.argv.slice(2)
const stageIndex = args.indexOf('--stage')
const stage = stageIndex >= 0 ? args[stageIndex + 1] : 'production'
const positional = args.filter((value, index) => index !== stageIndex && index !== stageIndex + 1)
const [outputArg] = positional

if (!outputArg || !['mvp', 'production'].includes(stage)) {
  console.error('用法: node build_star_pulse_launch_template.mjs [--stage mvp|production] <template_15.json>')
  process.exit(1)
}

const outputPath = resolve(outputArg)
const COLORS = {
  navy: '#0B1F4D',
  deepNavy: '#050A24',
  cyan: '#25D8FF',
  blue: '#2B6CFF',
  violet: '#8B5CFF',
  signal: '#F34AA9',
  warmWhite: '#08132F',
  white: '#FFFFFF',
  ink: '#F5F8FF',
  slate: '#A9BDD8',
  line: 'rgba(169,189,216,0.30)',
  paleCyan: 'rgba(37,216,255,0.10)',
}

const ASSETS = {
  cover: '/api/data/template_15_asset_bg_cover_v1.jpg',
  section: '/api/data/template_15_asset_bg_section_v1.jpg',
  end: '/api/data/template_15_asset_bg_end_v1.jpg',
  spectrum: '/api/data/template_15_asset_spectrum_footer_v1.png',
  horizon: '/api/data/template_15_asset_horizon_glow_v1.png',
  particles: '/api/data/template_15_asset_particle_field_v1.png',
  stage: '/api/data/template_15_asset_product_stage_v1.png',
}

const rectPath = 'M 0 0 L 200 0 L 200 200 L 0 200 Z'
const circlePath = 'M 100 0 A 100 100 0 1 1 99.9 0 Z'
const diamondPath = 'M 100 0 L 200 100 L 100 200 L 0 100 Z'

const escapeHtml = value => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')

const elementId = (slideId, suffix) => `t15-${slideId}-${suffix}`
const groupId = (slideId, index) => `t15-${slideId}-group-${String(index).padStart(2, '0')}`

const text = ({
  slideId,
  suffix,
  left,
  top,
  width,
  height,
  value,
  fontSize,
  color = COLORS.ink,
  bold = false,
  align = 'left',
  textType,
  group,
  fontFamily = '微软雅黑',
  lineHeight = 1.35,
  minimumFontSize,
  letterSpacing = 0,
  textWidthFactor,
  longTitleLetterSpacing,
  compressionLimits,
}) => ({
  type: 'text',
  id: elementId(slideId, suffix),
  left,
  top,
  width,
  // 语义槽至少容纳一行公共 renderer 的 1.5 行高和 20px 内边距。
  height: textType ? Math.max(height, fontSize * 1.5 + 20) : height,
  rotate: 0,
  defaultFontName: fontFamily,
  defaultColor: color,
  vertical: false,
  textLineHeight: lineHeight,
  content: `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: ${fontFamily};line-height: ${lineHeight};letter-spacing: ${letterSpacing}px;">${bold ? '<strong>' : ''}${escapeHtml(value)}${bold ? '</strong>' : ''}</span></p>`,
  ...(textType ? { textType } : {}),
  ...((minimumFontSize || textType === 'title' || ['content', 'item', 'itemTitle', 'subtitle'].includes(textType))
    ? { minimumFontSize: minimumFontSize || (textType === 'title' ? 36 : 16) }
    : {}),
  ...(textWidthFactor ? { textWidthFactor } : {}),
  ...(longTitleLetterSpacing ? { longTitleLetterSpacing } : {}),
  ...(compressionLimits ? { compressionLimits } : {}),
  ...(group ? { groupId: group } : {}),
})

const shape = ({
  slideId,
  suffix,
  left,
  top,
  width,
  height,
  fill,
  outline = fill,
  outlineWidth = 0,
  path = rectPath,
  group,
  lock = true,
}) => ({
  type: 'shape',
  id: elementId(slideId, suffix),
  left,
  top,
  width,
  height,
  viewBox: [200, 200],
  path,
  fill,
  fixedRatio: false,
  rotate: 0,
  outline: { color: outline, width: outlineWidth, style: 'solid' },
  lock,
  ...(group ? { groupId: group } : {}),
})

const line = ({ slideId, suffix, left, top, width, color = COLORS.cyan, thickness = 2 }) => ({
  type: 'line',
  id: elementId(slideId, suffix),
  left,
  top,
  start: [0, 0],
  end: [width, 0],
  points: ['', ''],
  color,
  style: 'solid',
  width: thickness,
  rotate: 0,
  lock: true,
})

const image = ({
  slideId,
  suffix,
  left,
  top,
  width,
  height,
  src,
  imageType,
  fixedRatio = false,
  strictImageCount = false,
  requireSourceDimensions = false,
  allowExtraItems = false,
}) => ({
  type: 'image',
  id: elementId(slideId, suffix),
  left,
  top,
  width,
  height,
  src,
  fixedRatio,
  rotate: 0,
  imageType,
  ...(imageType === 'decoration' ? { lock: true } : {}),
  ...(strictImageCount ? { strictImageCount: true } : {}),
  ...(requireSourceDimensions ? { requireSourceDimensions: true } : {}),
  ...(allowExtraItems ? { allowExtraItems: true } : {}),
})

const deepBackground = (slideId, src) => [
  image({
    slideId,
    suffix: 'background',
    left: 0,
    top: 0,
    width: 1000,
    height: 562.5,
    src,
    imageType: 'decoration',
  }),
  image({
    slideId,
    suffix: 'particle-overlay',
    left: 0,
    top: 0,
    width: 1000,
    height: 562.5,
    src: ASSETS.particles,
    imageType: 'decoration',
    fixedRatio: true,
  }),
]

const lightDecoration = slideId => [
  image({
    slideId,
    suffix: 'particle-overlay',
    left: 0,
    top: 0,
    width: 1000,
    height: 562.5,
    src: ASSETS.particles,
    imageType: 'decoration',
    fixedRatio: true,
  }),
]

const facetDecoration = slideId => image({
  slideId,
  suffix: 'horizon-overlay',
  left: 0,
  top: 124,
  width: 1000,
  height: 438.5,
  src: ASSETS.horizon,
  imageType: 'decoration',
  fixedRatio: true,
})

const sourceRemark = [
  '[Sources]',
  '- User-provided visual reference: 产品发布 (2).pptx; abstract narrative and visual patterns only; source media excluded',
  '- Original project assets generated for template_15 with built-in image_gen; model identifier not exposed',
].join('\n')

const header = (slideId, titleValue = '用结构把复杂问题讲清楚') => [
  text({
    slideId,
    suffix: 'eyebrow',
    left: 52,
    top: 14,
    width: 300,
    height: 22,
    value: 'PRODUCT · EVIDENCE · MOMENTUM',
    fontSize: 12,
    color: COLORS.cyan,
    bold: true,
    fontFamily: 'Arial',
  }),
  text({
    slideId,
    suffix: 'title',
    left: 52,
    top: 40,
    width: 820,
    height: 108,
    value: titleValue,
    fontSize: 36,
    color: COLORS.white,
    bold: true,
    textType: 'title',
    lineHeight: 1.2,
    letterSpacing: -0.5,
    textWidthFactor: 1.12,
  }),
  line({ slideId, suffix: 'header-line-a', left: 52, top: 154, width: 112, color: COLORS.cyan, thickness: 4 }),
  line({ slideId, suffix: 'header-line-b', left: 164, top: 154, width: 56, color: COLORS.violet, thickness: 4 }),
]

const footer = slideId => text({
  slideId,
  suffix: 'footer',
  left: 780,
  top: 532,
  width: 168,
  height: 18,
  value: 'STAR PULSE · PRODUCT LAUNCH',
  fontSize: 12,
  color: COLORS.slate,
  align: 'right',
  fontFamily: 'Arial',
})

const slide = ({ id, type, elements, layoutKind, variantMode, allowedItemCounts, background = COLORS.warmWhite }) => ({
  id,
  type,
  elements,
  background: { type: 'solid', color: background },
  remark: sourceRemark,
  ...(layoutKind ? { layoutKind } : {}),
  ...(variantMode ? { variantMode } : {}),
  ...(allowedItemCounts ? { allowedItemCounts } : {}),
  ...(['content', 'transition', 'end'].includes(type)
    ? { titleFitLimits: { singleWide: 20, singleAscii: 44, maxWide: 36, maxAscii: 80 } }
    : {}),
})

const makeCover = ({ id, withImage = false }) => {
  const elements = [
    ...deepBackground(id, ASSETS.cover),
    text({
      slideId: id,
      suffix: 'kicker',
      left: 70,
      top: 126,
      width: 450,
      height: 28,
      value: 'STAR PULSE · PRODUCT LAUNCH',
      fontSize: 16,
      color: COLORS.cyan,
      bold: true,
      fontFamily: 'Arial',
    }),
    text({
      slideId: id,
      suffix: 'title',
      left: 70,
      top: 174,
      width: withImage ? 450 : 820,
      height: 150,
      value: '让下一代产品被真正看见',
      fontSize: 50,
      color: COLORS.white,
      bold: true,
      textType: 'title',
      lineHeight: 1.25,
      minimumFontSize: 50,
      textWidthFactor: withImage ? 1.8 : 1.45,
      longTitleLetterSpacing: withImage ? -13 : -8,
      compressionLimits: withImage
        ? { wide: 16, ascii: 32 }
        : { wide: 28, ascii: 56 },
    }),
    text({
      slideId: id,
      suffix: 'content',
      left: 74,
      top: 344,
      width: withImage ? 440 : 760,
      height: 82,
      value: '从核心主张、性能证据到市场定位，形成完整发布叙事。',
      fontSize: 18,
      color: '#DCEAF3',
      textType: 'content',
    }),
    line({ slideId: id, suffix: 'accent', left: 70, top: 452, width: 138, color: COLORS.cyan, thickness: 5 }),
  ]

  if (withImage) {
    elements.push(
      shape({
        slideId: id,
        suffix: 'image-frame',
        left: 590,
        top: 110,
        width: 350,
        height: 390,
        fill: 'rgba(255,255,255,0.06)',
        outline: 'rgba(37,216,255,0.52)',
        outlineWidth: 1,
      }),
      image({
        slideId: id,
        suffix: 'content-image',
        left: 610,
        top: 130,
        width: 310,
        height: 350,
        src: ASSETS.section,
        imageType: 'content',
        strictImageCount: true,
        requireSourceDimensions: true,
      }),
    )
  }
  return {
    ...slide({ id, type: 'cover', elements, variantMode: 'deterministic', background: COLORS.deepNavy }),
    titleFitLimits: withImage
      ? { singleWide: 24, singleAscii: 48, maxWide: 24, maxAscii: 48 }
      : { singleWide: 36, singleAscii: 72, maxWide: 36, maxAscii: 72 },
  }
}

const makeContents = count => {
  const id = `contents-${count}`
  const elements = [
    ...lightDecoration(id),
    ...header(id, '这场发布，沿四条证据线展开'),
    text({
      slideId: id,
      suffix: 'intro',
      left: 642,
      top: 66,
      width: 306,
      height: 48,
      value: '主张 → 性能 → 差异 → 定位',
      fontSize: 16,
      color: COLORS.slate,
      align: 'right',
    }),
  ]

  const columns = count > 6 ? 2 : count <= 3 ? 1 : 2
  const rows = Math.ceil(count / columns)
  const startTop = count <= 3 ? 168 : 148
  const rowGap = count > 6 ? 66 : Math.min(96, 330 / rows)
  const columnWidth = columns === 1 ? 720 : 410
  const columnLeft = columns === 1 ? [140] : [70, 520]
  for (let index = 0; index < count; index += 1) {
    const column = index % columns
    const row = Math.floor(index / columns)
    const top = startTop + row * rowGap
    const left = columnLeft[column]
    const group = groupId(id, index + 1)
    elements.push(
      shape({
        slideId: id,
        suffix: `item-panel-${index + 1}`,
        left,
        top,
        width: columnWidth,
        height: count > 6 ? 52 : 70,
        fill: index % 2 === 0 ? 'rgba(11,31,77,0.82)' : 'rgba(43,108,255,0.16)',
        outline: index % 2 === 0 ? 'rgba(37,216,255,0.36)' : 'rgba(139,92,255,0.42)',
        outlineWidth: 1,
        group,
      }),
      text({
        slideId: id,
        suffix: `item-number-${index + 1}`,
        left: left + 18,
        top: top + (count > 6 ? 12 : 17),
        width: 54,
        height: 30,
        value: String(index + 1).padStart(2, '0'),
        fontSize: 20,
        color: COLORS.blue,
        bold: true,
        textType: 'itemNumber',
        group,
        fontFamily: 'Arial',
      }),
      text({
        slideId: id,
        suffix: `item-${index + 1}`,
        left: left + 80,
        top: top + (count > 6 ? 10 : 15),
        width: columnWidth - 100,
        height: count > 6 ? 34 : 40,
        value: `议题 ${index + 1}：关键结论与行动`,
        fontSize: count > 6 ? 16 : 18,
        color: COLORS.white,
        bold: true,
        textType: 'item',
        group,
      }),
    )
  }
  elements.push(footer(id))
  return slide({ id, type: 'contents', elements })
}

const makeTransition = ({ id, variant = 'horizon' }) => {
  const compact = variant === 'spectrum' || variant === 'stage'
  const elements = [
    ...deepBackground(id, ASSETS.section),
    text({
      slideId: id,
      suffix: 'part-number',
      left: compact ? 92 : 120,
      top: compact ? 138 : 166,
      width: 250,
      height: 142,
      value: '01',
      fontSize: compact ? 72 : 92,
      color: COLORS.cyan,
      bold: true,
      textType: 'partNumber',
      fontFamily: 'Arial',
    }),
    line({
      slideId: id,
      suffix: 'divider',
      left: compact ? 88 : 390,
      top: compact ? 294 : 190,
      width: compact ? 780 : 4,
      color: 'rgba(255,255,255,0.34)',
      thickness: compact ? 2 : 4,
    }),
    text({
      slideId: id,
      suffix: 'title',
      left: compact ? 92 : 424,
      top: compact ? 300 : 182,
      width: compact ? 760 : 490,
      height: compact ? 126 : 132,
      value: '让下一条证据自然成为焦点',
      fontSize: 44,
      color: COLORS.white,
      bold: true,
      textType: 'title',
      lineHeight: 1.2,
      minimumFontSize: 44,
    }),
    text({
      slideId: id,
      suffix: 'content',
      left: compact ? 96 : 428,
      top: compact ? 430 : 322,
      width: compact ? 700 : 430,
      // 横向版式预留三句上限的正文高度；紧凑版式本身宽度更大，维持原高度。
      height: compact ? 70 : 132,
      value: '每个章节只承担一个沟通任务，并为下一步建立必要上下文。',
      fontSize: 18,
      color: '#DCEAF3',
      textType: 'content',
    }),
  ]
  if (variant === 'spectrum') {
    elements.splice(2, 0, image({ slideId: id, suffix: 'spectrum', left: 0, top: 300, width: 1000, height: 262.5, src: ASSETS.spectrum, imageType: 'decoration', fixedRatio: true }))
    elements.splice(3, 0, shape({ slideId: id, suffix: 'text-shield', left: 54, top: 278, width: 892, height: 224, fill: 'rgba(5,10,36,0.72)', outline: 'rgba(37,216,255,0.18)', outlineWidth: 1 }))
  } else if (variant === 'stage') {
    elements.splice(2, 0, image({ slideId: id, suffix: 'stage', left: 240, top: 304, width: 520, height: 258, src: ASSETS.stage, imageType: 'decoration', fixedRatio: true }))
  } else if (variant === 'particle') {
    elements.splice(2, 0, image({ slideId: id, suffix: 'horizon', left: 0, top: 286, width: 1000, height: 276.5, src: ASSETS.horizon, imageType: 'decoration', fixedRatio: true }))
  }
  return {
    ...slide({ id, type: 'transition', elements, variantMode: 'deterministic', background: COLORS.deepNavy }),
    variantKey: variant,
  }
}

const cardPositions = count => {
  if (count === 1) return [{ left: 120, top: 178, width: 760, height: 260 }]
  if (count === 2) return [
    { left: 70, top: 174, width: 410, height: 270 },
    { left: 520, top: 174, width: 410, height: 270 },
  ]
  if (count === 3) return [50, 365, 680].map(left => ({ left, top: 176, width: 270, height: 278 }))
  if (count === 4) return [
    { left: 70, top: 170, width: 405, height: 150 },
    { left: 525, top: 170, width: 405, height: 150 },
    { left: 70, top: 350, width: 405, height: 150 },
    { left: 525, top: 350, width: 405, height: 150 },
  ]
  if (count === 5) return [
    ...[50, 365, 680].map(left => ({ left, top: 170, width: 270, height: 150 })),
    ...[205, 525].map(left => ({ left, top: 350, width: 270, height: 150 })),
  ]
  return [
    ...[50, 365, 680].map(left => ({ left, top: 168, width: 270, height: 154 })),
    ...[50, 365, 680].map(left => ({ left, top: 344, width: 270, height: 154 })),
  ]
}

const makeTextContent = ({ id, count, variant = 'cards', layoutKind = 'text' }) => {
  const elements = [
    ...lightDecoration(id),
    ...(count === 1 ? [facetDecoration(id)] : []),
    ...header(id),
  ]
  const positions = cardPositions(count)

  // 变体只改变装饰和轮廓，语义槽位容量保持相同。
  if (variant === 'split') {
    elements.push(
      shape({ slideId: id, suffix: 'split-left', left: 0, top: 132, width: 500, height: 390, fill: 'rgba(37,216,255,0.08)' }),
      shape({ slideId: id, suffix: 'split-right', left: 500, top: 132, width: 500, height: 390, fill: 'rgba(139,92,255,0.08)' }),
    )
  } else if (variant === 'steps') {
    elements.push(line({ slideId: id, suffix: 'steps-line', left: 155, top: 246, width: 690, color: COLORS.line, thickness: 4 }))
  } else if (variant === 'quadrant') {
    elements.push(shape({ slideId: id, suffix: 'center-diamond', left: 466, top: 276, width: 68, height: 68, fill: COLORS.cyan, path: diamondPath }))
  }

  positions.forEach((position, index) => {
    const group = groupId(id, index + 1)
    const compact = count >= 4
    elements.push(
      shape({
        slideId: id,
        suffix: `panel-${index + 1}`,
        ...position,
        fill: index % 2 === 0 ? 'rgba(11,31,77,0.82)' : COLORS.paleCyan,
        outline: COLORS.line,
        outlineWidth: 1,
        group,
      }),
      shape({
        slideId: id,
        suffix: `number-dot-${index + 1}`,
        left: position.left + 18,
        top: position.top + 18,
        width: 38,
        height: 38,
        fill: index === 0 ? COLORS.cyan : COLORS.deepNavy,
        path: circlePath,
        group,
      }),
      text({
        slideId: id,
        suffix: `item-number-${index + 1}`,
        left: position.left + 18,
        top: position.top + 25,
        width: 38,
        height: 22,
        value: String(index + 1).padStart(2, '0'),
        fontSize: 14,
        color: COLORS.white,
        bold: true,
        align: 'center',
        textType: 'itemNumber',
        group,
        fontFamily: 'Arial',
      }),
      text({
        slideId: id,
        suffix: `item-title-${index + 1}`,
        left: position.left + 70,
        top: position.top + 20,
        width: position.width - 90,
        // 标题框与正文框首尾相接，完整使用卡片头部空间，容纳真实 Agent 的两行标题。
        height: compact ? 68 : 72,
        value: `关键要点 ${index + 1}`,
        fontSize: compact ? 20 : 24,
        color: COLORS.ink,
        bold: true,
        textType: 'itemTitle',
        group,
      }),
      text({
        slideId: id,
        suffix: `item-body-${index + 1}`,
        left: position.left + (compact ? 20 : 70),
        top: position.top + (compact ? 88 : 92),
        width: position.width - (compact ? 40 : 100),
        height: position.height - (compact ? 100 : 114),
        value: '用事实说明影响，并明确下一步动作。',
        fontSize: 16,
        color: COLORS.slate,
        textType: 'item',
        group,
      }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind, allowedItemCounts: [count] })
}

const imagePositions = count => {
  if (count === 1) return [{ left: 76, top: 156, width: 420, height: 324, textLeft: 538, textTop: 196, textWidth: 376, textHeight: 220 }]
  if (count === 2) return [70, 520].map(left => ({ left, top: 154, width: 250, height: 176, textLeft: left + 278, textTop: 174, textWidth: 132, textHeight: 250 }))
  if (count === 3) return [50, 365, 680].map(left => ({ left, top: 158, width: 270, height: 168, textLeft: left, textTop: 344, textWidth: 270, textHeight: 142 }))
  if (count === 4) return [
    { left: 60, top: 150, width: 150, height: 126, textLeft: 226, textTop: 158, textWidth: 230, textHeight: 118 },
    { left: 520, top: 150, width: 150, height: 126, textLeft: 686, textTop: 158, textWidth: 230, textHeight: 118 },
    { left: 60, top: 334, width: 150, height: 126, textLeft: 226, textTop: 342, textWidth: 230, textHeight: 118 },
    { left: 520, top: 334, width: 150, height: 126, textLeft: 686, textTop: 342, textWidth: 230, textHeight: 118 },
  ]
  const columns = count === 5 ? [52, 365, 678] : [52, 365, 678]
  const entries = []
  for (let index = 0; index < count; index += 1) {
    const row = Math.floor(index / 3)
    const column = index % 3
    const left = count === 5 && row === 1 ? [210, 522][column] : columns[column]
    entries.push({
      left,
      top: row === 0 ? 148 : 334,
      width: 100,
      height: 100,
      textLeft: left + 118,
      textTop: row === 0 ? 148 : 334,
      textWidth: 152,
      textHeight: 150,
    })
  }
  return entries
}

const addCompactItem = (elements, { id, index, left, top, width, height = 82 }) => {
  const group = groupId(id, index + 1)
  elements.push(
    shape({ slideId: id, suffix: `item-panel-${index + 1}`, left, top, width, height, fill: index % 2 === 0 ? 'rgba(37,216,255,0.11)' : 'rgba(139,92,255,0.10)', outline: COLORS.line, outlineWidth: 1, group }),
    text({ slideId: id, suffix: `item-title-${index + 1}`, left: left + 16, top: top + 10, width: width - 32, height: 28, value: `核心卖点 ${index + 1}`, fontSize: 18, color: COLORS.white, bold: true, textType: 'itemTitle', group }),
    text({ slideId: id, suffix: `item-body-${index + 1}`, left: left + 16, top: top + 40, width: width - 32, height: height - 46, value: '用可验证证据说明产品价值。', fontSize: 16, color: COLORS.slate, textType: 'item', group }),
  )
}

const makeHeroContent = ({ id, side = 'left' }) => {
  const imageLeft = side === 'left' ? 74 : 616
  const textLeft = side === 'left' ? 548 : 70
  const elements = [
    ...lightDecoration(id),
    ...header(id, '让一个产品主角承载整页记忆点'),
    image({ slideId: id, suffix: 'stage', left: imageLeft - 42, top: 328, width: 400, height: 206, src: ASSETS.stage, imageType: 'decoration', fixedRatio: true }),
    image({ slideId: id, suffix: 'content-image-1', left: imageLeft, top: 150, width: 330, height: 332, src: ASSETS.section, imageType: 'content', strictImageCount: true, requireSourceDimensions: true, allowExtraItems: true }),
  ]
  for (let index = 0; index < 3; index += 1) {
    addCompactItem(elements, { id, index, left: textLeft, top: 162 + index * 112, width: 382, height: 94 })
  }
  elements.push(footer(id))
  return {
    ...slide({ id, type: 'content', elements, layoutKind: 'hero', allowedItemCounts: [1, 2, 3] }),
    variantKey: side,
  }
}

const makeDenseImageContent = () => {
  const id = 'content-image-1-dense'
  const elements = [
    ...lightDecoration(id),
    ...header(id, '一张产品图串起六条关键信息'),
    image({ slideId: id, suffix: 'stage', left: 628, top: 350, width: 330, height: 176, src: ASSETS.stage, imageType: 'decoration', fixedRatio: true }),
    image({ slideId: id, suffix: 'content-image-1', left: 654, top: 164, width: 278, height: 310, src: ASSETS.section, imageType: 'content', strictImageCount: true, requireSourceDimensions: true, allowExtraItems: true }),
  ]
  for (let index = 0; index < 6; index += 1) {
    const column = index % 2
    const row = Math.floor(index / 2)
    addCompactItem(elements, { id, index, left: 52 + column * 286, top: 154 + row * 116, width: 266, height: 98 })
  }
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'image', allowedItemCounts: [4, 5, 6] })
}

const makeDualImageContent = () => {
  const id = 'content-dual-image-2'
  const elements = [...lightDecoration(id), ...header(id, '双视角把产品证据放在同一页')]
  const imageLefts = [58, 518]
  imageLefts.forEach((left, index) => {
    elements.push(image({ slideId: id, suffix: `content-image-${index + 1}`, left, top: 150, width: 424, height: 196, src: ASSETS.section, imageType: 'content', strictImageCount: true, requireSourceDimensions: true, allowExtraItems: true }))
  })
  for (let index = 0; index < 6; index += 1) {
    const column = index % 2
    const row = Math.floor(index / 2)
    const left = 58 + column * 460
    const top = 360 + row * 54
    const group = groupId(id, index + 1)
    elements.push(
      shape({ slideId: id, suffix: `item-panel-${index + 1}`, left, top, width: 424, height: 44, fill: index % 2 === 0 ? 'rgba(37,216,255,0.11)' : 'rgba(139,92,255,0.10)', outline: COLORS.line, outlineWidth: 1, group }),
      text({ slideId: id, suffix: `item-body-${index + 1}`, left: left + 14, top: top + 5, width: 396, height: 30, value: `产品证据 ${index + 1}`, fontSize: 16, color: COLORS.white, textType: 'item', group }),
    )
  }
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'gallery', allowedItemCounts: [2, 3, 4, 5, 6] })
}

const makeImageContent = count => {
  const id = `content-gallery-${count}`
  const elements = [...lightDecoration(id), ...header(id, count >= 3 ? '用图像建立共同现场' : '图像与观点彼此支撑')]
  const positions = imagePositions(count)
  positions.forEach((position, index) => {
    const group = groupId(id, index + 1)
    elements.push(
      shape({
        slideId: id,
        suffix: `frame-${index + 1}`,
        left: position.left - 6,
        top: position.top - 6,
        width: position.width + 12,
        height: position.height + 12,
        fill: 'rgba(11,31,77,0.82)',
        outline: COLORS.line,
        outlineWidth: 1,
        group,
      }),
      image({
        slideId: id,
        suffix: `content-image-${index + 1}`,
        left: position.left,
        top: position.top,
        width: position.width,
        height: position.height,
        src: ASSETS.section,
        imageType: 'content',
        strictImageCount: true,
        requireSourceDimensions: true,
      }),
      text({
        slideId: id,
        suffix: `item-title-${index + 1}`,
        left: position.textLeft,
        top: position.textTop,
        width: position.textWidth,
        height: count >= 5 ? 28 : 42,
        value: `场景 ${index + 1}`,
        fontSize: count >= 5 ? 18 : 22,
        color: COLORS.ink,
        bold: true,
        textType: 'itemTitle',
        group,
      }),
      text({
        slideId: id,
        suffix: `item-body-${index + 1}`,
        left: position.textLeft,
        top: position.textTop + (count >= 5 ? 54 : 60),
        width: position.textWidth,
        height: Math.max(44, position.textHeight - (count >= 5 ? 54 : 60)),
        value: '说明图像与结论之间的关系。',
        fontSize: 16,
        color: COLORS.slate,
        textType: 'item',
        group,
      }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: count >= 3 ? 'gallery' : 'image', allowedItemCounts: [count] })
}

const makeMetrics = count => {
  const id = `content-metrics-${count}`
  const elements = [...lightDecoration(id), ...header(id, '关键指标揭示行动优先级')]
  const positions = count === 3
    ? [80, 365, 650].map(left => ({ left, top: 178, width: 270, height: 270 }))
    : count === 4
      ? [60, 285, 510, 735].map(left => ({ left, top: 188, width: 205, height: 250 }))
      : [40, 230, 420, 610, 800].map(left => ({ left, top: 194, width: 160, height: 236 }))
  positions.forEach((position, index) => {
    const group = groupId(id, index + 1)
    elements.push(
      shape({
        slideId: id,
        suffix: `metric-panel-${index + 1}`,
        ...position,
        fill: index === 0 ? COLORS.deepNavy : 'rgba(11,31,77,0.82)',
        outline: index === 0 ? COLORS.deepNavy : COLORS.line,
        outlineWidth: 1,
        group,
      }),
      shape({
        slideId: id,
        suffix: `metric-marker-${index + 1}`,
        left: position.left + 22,
        top: position.top + 24,
        width: 12,
        height: 52,
        fill: COLORS.cyan,
        group,
      }),
      text({
        slideId: id,
        suffix: `metric-value-${index + 1}`,
        left: position.left + 22,
        top: position.top + 84,
        width: position.width - 44,
        height: 62,
        value: `${72 + index * 6}%`,
        fontSize: count >= 5 ? 30 : 36,
        color: index === 0 ? COLORS.white : COLORS.ink,
        bold: true,
        textType: 'itemTitle',
        group,
        fontFamily: 'Arial',
      }),
      text({
        slideId: id,
        suffix: `metric-label-${index + 1}`,
        left: position.left + 22,
        top: position.top + 154,
        width: position.width - 44,
        height: position.height - 170,
        value: '指标说明与业务含义',
        fontSize: 16,
        color: index === 0 ? '#DCEAF3' : COLORS.slate,
        textType: 'item',
        group,
      }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'metrics', allowedItemCounts: [count] })
}

const makeProcess = count => {
  const id = `content-process-${count}`
  const elements = [
    ...lightDecoration(id),
    ...header(id, '把行动拆成可验证的连续步骤'),
    line({ slideId: id, suffix: 'process-line', left: 105, top: 238, width: 790, color: COLORS.line, thickness: 5 }),
  ]
  const width = count === 3 ? 240 : count === 4 ? 190 : 154
  const gap = count === 3 ? 70 : count === 4 ? 48 : 30
  const start = count === 3 ? 70 : count === 4 ? 84 : 55
  for (let index = 0; index < count; index += 1) {
    const left = start + index * (width + gap)
    const group = groupId(id, index + 1)
    elements.push(
      shape({ slideId: id, suffix: `node-${index + 1}`, left: left + width / 2 - 25, top: 213, width: 50, height: 50, fill: index === 0 ? COLORS.cyan : COLORS.deepNavy, path: circlePath, group }),
      text({ slideId: id, suffix: `item-number-${index + 1}`, left: left + width / 2 - 25, top: 226, width: 50, height: 22, value: String(index + 1).padStart(2, '0'), fontSize: 14, color: COLORS.white, bold: true, align: 'center', textType: 'itemNumber', group, fontFamily: 'Arial' }),
      text({ slideId: id, suffix: `item-title-${index + 1}`, left, top: 286, width, height: 54, value: `步骤 ${index + 1}`, fontSize: 20, color: COLORS.ink, bold: true, align: 'center', textType: 'itemTitle', group }),
      text({ slideId: id, suffix: `item-body-${index + 1}`, left, top: 348, width, height: 106, value: '明确输入、责任与完成标准。', fontSize: 16, color: COLORS.slate, align: 'center', textType: 'item', group }),
    )
  }
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'process', allowedItemCounts: [count] })
}

const makeCompare = count => {
  const id = `content-compare-${count}`
  const elements = [...lightDecoration(id), ...header(id, '用同一口径比较选择')]
  const positions = count === 2
    ? [{ left: 80, top: 164, width: 390, height: 306 }, { left: 530, top: 164, width: 390, height: 306 }]
    : cardPositions(4)
  positions.forEach((position, index) => {
    const group = groupId(id, index + 1)
    const positive = index % 2 === 0
    elements.push(
      shape({ slideId: id, suffix: `compare-panel-${index + 1}`, ...position, fill: positive ? 'rgba(37,216,255,0.12)' : 'rgba(139,92,255,0.10)', outline: positive ? COLORS.cyan : COLORS.violet, outlineWidth: 1, group }),
      shape({ slideId: id, suffix: `compare-band-${index + 1}`, left: position.left, top: position.top, width: 10, height: position.height, fill: positive ? COLORS.cyan : COLORS.signal, group }),
      text({ slideId: id, suffix: `item-title-${index + 1}`, left: position.left + 28, top: position.top + 26, width: position.width - 52, height: 54, value: `方案 ${index + 1}`, fontSize: count === 2 ? 26 : 20, color: COLORS.ink, bold: true, textType: 'itemTitle', group }),
      text({ slideId: id, suffix: `item-body-${index + 1}`, left: position.left + 28, top: position.top + 96, width: position.width - 52, height: position.height - 122, value: '对比价值、代价、风险和适用条件。', fontSize: 16, color: COLORS.slate, textType: 'item', group }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'compare', allowedItemCounts: [count] })
}

const makeHubSpoke = () => {
  const id = 'content-hub-spoke-5'
  const elements = [...lightDecoration(id), ...header(id, '中心主张连接四个支撑分支')]
  // 连接线先于节点创建，确保边线始终位于内容块之后。
  elements.push(
    line({ slideId: id, suffix: 'connector-a', left: 250, top: 286, width: 500, color: COLORS.line, thickness: 2 }),
    line({ slideId: id, suffix: 'connector-b', left: 500, top: 236, width: 0, color: COLORS.line, thickness: 2 }),
  )
  const positions = [
    { left: 350, top: 144, width: 300, height: 106 },
    { left: 70, top: 300, width: 380, height: 92 },
    { left: 550, top: 300, width: 380, height: 92 },
    { left: 70, top: 414, width: 380, height: 92 },
    { left: 550, top: 414, width: 380, height: 92 },
  ]
  positions.forEach((position, index) => {
    const group = groupId(id, index + 1)
    elements.push(
      shape({ slideId: id, suffix: `hub-panel-${index + 1}`, ...position, fill: index === 0 ? COLORS.deepNavy : 'rgba(11,31,77,0.82)', outline: index === 0 ? COLORS.deepNavy : COLORS.line, outlineWidth: 1, group }),
      text({ slideId: id, suffix: `item-title-${index + 1}`, left: position.left + 18, top: position.top + 14, width: position.width - 36, height: 34, value: index === 0 ? '中心主张' : `支撑分支 ${index}`, fontSize: index === 0 ? 22 : 18, color: index === 0 ? COLORS.white : COLORS.ink, bold: true, align: 'center', textType: 'itemTitle', group }),
      text({ slideId: id, suffix: `item-body-${index + 1}`, left: position.left + 18, top: position.top + 50, width: position.width - 36, height: position.height - 60, value: '说明依赖关系和业务作用。', fontSize: 16, color: index === 0 ? '#DCEAF3' : COLORS.slate, align: 'center', textType: 'item', group }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'hub-spoke' })
}

const makeTimeline = count => {
  const id = `content-timeline-${count}`
  const elements = [
    ...lightDecoration(id),
    ...header(id, '四个里程碑形成连续推进'),
    line({ slideId: id, suffix: 'timeline-line', left: 118, top: 238, width: 764, color: COLORS.line, thickness: 5 }),
  ]
  const itemWidth = count === 3 ? 210 : count === 4 ? 156 : 138
  const gap = count === 3 ? 80 : count === 4 ? 74 : 46
  const totalWidth = count * itemWidth + (count - 1) * gap
  const lefts = Array.from({ length: count }, (_, index) => (1000 - totalWidth) / 2 + index * (itemWidth + gap))
  lefts.forEach((left, index) => {
    const group = groupId(id, index + 1)
    elements.push(
      shape({ slideId: id, suffix: `node-${index + 1}`, left: left + 50, top: 210, width: 56, height: 56, fill: index === 0 ? COLORS.cyan : COLORS.deepNavy, path: circlePath, group }),
      text({ slideId: id, suffix: `item-number-${index + 1}`, left: left + 50, top: 226, width: 56, height: 22, value: String(index + 1).padStart(2, '0'), fontSize: 14, color: COLORS.white, bold: true, align: 'center', textType: 'itemNumber', group, fontFamily: 'Arial' }),
      text({ slideId: id, suffix: `item-title-${index + 1}`, left, top: 292, width: itemWidth, height: 48, value: `里程碑 ${index + 1}`, fontSize: 20, color: COLORS.ink, bold: true, align: 'center', textType: 'itemTitle', group }),
      text({ slideId: id, suffix: `item-body-${index + 1}`, left, top: 350, width: itemWidth, height: 104, value: '说明阶段结果、证据和下一步。', fontSize: 16, color: COLORS.slate, align: 'center', textType: 'item', group }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'timeline', allowedItemCounts: [count] })
}

const makePositioning = count => makeTextContent({
  id: `content-positioning-${count}`,
  count,
  variant: count === 3 ? 'steps' : 'quadrant',
  layoutKind: 'positioning',
})

const makeEnd = ({ id, action = false }) => {
  const elements = [
    ...deepBackground(id, ASSETS.end),
    text({ slideId: id, suffix: 'kicker', left: 150, top: 134, width: 700, height: 26, value: action ? 'ALIGN · COMMIT · LAUNCH' : 'VISION · EVIDENCE · MOMENTUM', fontSize: 14, color: COLORS.cyan, bold: true, align: 'center', fontFamily: 'Arial' }),
    text({ slideId: id, suffix: 'title', left: 120, top: 178, width: 760, height: 116, value: action ? '把发布共识转化为下一步行动' : '让下一代产品从这里启程', fontSize: 48, color: COLORS.white, bold: true, align: 'center', textType: 'title' }),
    line({ slideId: id, suffix: 'end-line-a', left: 380, top: 334, width: 150, color: COLORS.cyan, thickness: 4 }),
    line({ slideId: id, suffix: 'end-line-b', left: 530, top: 334, width: 90, color: 'rgba(255,255,255,0.34)', thickness: 4 }),
    text({ slideId: id, suffix: 'content', left: 160, top: 350, width: 680, height: 66, value: action ? '明确负责人、完成标准和复盘时间。' : '感谢聆听，期待一起把产品推向真实世界。', fontSize: 18, color: '#DCEAF3', align: 'center', textType: 'content' }),
  ]
  if (action) {
    for (let index = 0; index < 3; index += 1) {
      const left = 140 + index * 250
      const group = groupId(id, index + 1)
      elements.push(
        shape({ slideId: id, suffix: `action-panel-${index + 1}`, left, top: 430, width: 220, height: 72, fill: 'rgba(11,31,77,0.82)', outline: index === 0 ? COLORS.cyan : COLORS.violet, outlineWidth: 1, group }),
        text({ slideId: id, suffix: `action-item-${index + 1}`, left: left + 14, top: 442, width: 192, height: 44, value: `行动项 ${index + 1}`, fontSize: 16, color: COLORS.white, align: 'center', textType: 'item', group }),
      )
    }
  }
  return slide({ id, type: 'end', elements, variantMode: 'deterministic', background: COLORS.deepNavy })
}

const allSlides = [
  makeCover({ id: 'cover-minimal' }),
  makeCover({ id: 'cover-hero', withImage: true }),
  ...[3, 4, 5, 6].map(makeContents),
  makeTransition({ id: 'transition-horizon', variant: 'horizon' }),
  makeTransition({ id: 'transition-spectrum', variant: 'spectrum' }),
  makeTransition({ id: 'transition-particle', variant: 'particle' }),
  makeTransition({ id: 'transition-stage', variant: 'stage' }),
  makeTextContent({ id: 'content-text-1', count: 1, layoutKind: 'focus' }),
  makeTextContent({ id: 'content-text-2', count: 2 }),
  makeTextContent({ id: 'content-text-3', count: 3 }),
  makeTextContent({ id: 'content-text-4', count: 4 }),
  makeTextContent({ id: 'content-text-5', count: 5 }),
  makeTextContent({ id: 'content-text-6', count: 6 }),
  makeHeroContent({ id: 'content-hero-left', side: 'left' }),
  makeHeroContent({ id: 'content-hero-right', side: 'right' }),
  makeDenseImageContent(),
  makeDualImageContent(),
  ...[3, 4, 5].map(makeMetrics),
  ...[2, 4].map(makeCompare),
  ...[3, 4, 5, 6].map(makeImageContent),
  ...[3, 4, 5].map(makeTimeline),
  ...[3, 4, 5].map(makeProcess),
  ...[3, 4].map(makePositioning),
  makeEnd({ id: 'end-minimal' }),
  makeEnd({ id: 'end-action', action: true }),
]

const mvpSlideIds = [
  'cover-minimal',
  'cover-hero',
  'contents-3',
  'contents-4',
  'contents-5',
  'contents-6',
  'transition-horizon',
  'transition-spectrum',
  'content-text-1',
  'content-text-2',
  'content-text-3',
  'content-text-4',
  'content-text-5',
  'content-text-6',
  'content-hero-left',
  'content-metrics-3',
  'content-metrics-4',
  'content-compare-2',
  'content-gallery-3',
  'end-minimal',
]

const selectedSlides = stage === 'mvp'
  ? allSlides.filter(candidate => mvpSlideIds.includes(candidate.id))
  : allSlides

const template = {
  id: 'template_15',
  title: '星脉科技产品发布',
  width: 1000,
  height: 562.5,
  theme: {
    themeColors: [COLORS.deepNavy, COLORS.navy, COLORS.cyan, COLORS.blue, COLORS.violet, COLORS.signal],
    fontColor: COLORS.ink,
    fontName: '微软雅黑',
    backgroundColor: COLORS.warmWhite,
  },
  slides: selectedSlides,
  metadata: {
    aspectRatio: '16:9',
    sourceReference: '产品发布 (2).pptx（仅抽象叙事与视觉规律，源媒体全部排除）',
    imageSlotMarker: 'imageType=content',
    decorativeImageMarker: 'imageType=decoration',
    assetGeneration: 'built-in image_gen; model identifier not exposed; seven audited project assets',
    buildStage: stage,
    mvpSlideIds,
  },
}

await writeFile(outputPath, `${JSON.stringify(template, null, 2)}\n`, 'utf8')
console.log(JSON.stringify({
  status: 'PASS',
  stage,
  output: outputPath,
  slides: selectedSlides.length,
  pageTypes: Object.fromEntries(['cover', 'contents', 'transition', 'content', 'end'].map(type => [
    type,
    selectedSlides.filter(candidate => candidate.type === type).length,
  ])),
}, null, 2))

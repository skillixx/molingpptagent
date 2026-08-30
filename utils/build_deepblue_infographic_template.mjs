#!/usr/bin/env node

/**
 * 构建“深蓝青棱商务信息图”生产模板。
 *
 * 支持两个阶段：
 * - mvp：输出规格声明的 18 页 MVP，用于真实生成门禁；
 * - production：输出完整 36 页生产库存。
 */

import { writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const args = process.argv.slice(2)
const stageIndex = args.indexOf('--stage')
const stage = stageIndex >= 0 ? args[stageIndex + 1] : 'production'
const positional = args.filter((value, index) => index !== stageIndex && index !== stageIndex + 1)
const [outputArg] = positional

if (!outputArg || !['mvp', 'production'].includes(stage)) {
  console.error('用法: node build_deepblue_infographic_template.mjs [--stage mvp|production] <template_14.json>')
  process.exit(1)
}

const outputPath = resolve(outputArg)
const COLORS = {
  navy: '#354A62',
  deepNavy: '#243447',
  cyan: '#45BEE3',
  blue: '#28A7CF',
  signal: '#FD5B5B',
  warmWhite: '#F6F8FA',
  white: '#FFFFFF',
  ink: '#223041',
  slate: '#6C7B8B',
  line: '#D7E1E9',
  paleCyan: '#E4F7FC',
}

const ASSETS = {
  cover: '/api/data/template_14_asset_bg_cover_v1.jpg',
  section: '/api/data/template_14_asset_bg_section_v1.jpg',
  end: '/api/data/template_14_asset_bg_end_v1.jpg',
  facet: '/api/data/template_14_asset_facet_corner_v1.png',
  line: '/api/data/template_14_asset_line_particle_v1.png',
}

const rectPath = 'M 0 0 L 200 0 L 200 200 L 0 200 Z'
const circlePath = 'M 100 0 A 100 100 0 1 1 99.9 0 Z'
const diamondPath = 'M 100 0 L 200 100 L 100 200 L 0 100 Z'

const escapeHtml = value => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')

const elementId = (slideId, suffix) => `t14-${slideId}-${suffix}`
const groupId = (slideId, index) => `t14-${slideId}-group-${String(index).padStart(2, '0')}`

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
  content: `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: ${fontFamily};line-height: ${lineHeight};">${bold ? '<strong>' : ''}${escapeHtml(value)}${bold ? '</strong>' : ''}</span></p>`,
  ...(textType ? { textType } : {}),
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
    suffix: 'line-overlay',
    left: 0,
    top: -40.2,
    width: 1000,
    height: 642.9,
    src: ASSETS.line,
    imageType: 'decoration',
    fixedRatio: true,
  }),
]

const lightDecoration = slideId => [
  image({
    slideId,
    suffix: 'line-overlay',
    left: 0,
    top: -40.2,
    width: 1000,
    height: 642.9,
    src: ASSETS.line,
    imageType: 'decoration',
    fixedRatio: true,
  }),
]

const facetDecoration = slideId => image({
  slideId,
  suffix: 'facet-overlay',
  left: 0,
  top: -40.2,
  width: 1000,
  height: 642.9,
  src: ASSETS.facet,
  imageType: 'decoration',
  fixedRatio: true,
})

const sourceRemark = [
  '[Sources]',
  '- User-provided visual reference: 扁平风格(38).pptx; abstract layout patterns only',
  '- Original project assets generated for template_14 with built-in image_gen; model identifier not exposed',
].join('\n')

const header = (slideId, titleValue = '用结构把复杂问题讲清楚') => [
  text({
    slideId,
    suffix: 'eyebrow',
    left: 52,
    top: 28,
    width: 300,
    height: 22,
    value: 'STRUCTURE · EVIDENCE · ACTION',
    fontSize: 12,
    color: COLORS.blue,
    bold: true,
    fontFamily: 'Arial',
  }),
  text({
    slideId,
    suffix: 'title',
    left: 52,
    top: 50,
    width: 820,
    height: 80,
    value: titleValue,
    fontSize: 36,
    color: COLORS.ink,
    bold: true,
    textType: 'title',
  }),
  line({ slideId, suffix: 'header-line-a', left: 52, top: 134, width: 112, color: COLORS.cyan, thickness: 4 }),
  line({ slideId, suffix: 'header-line-b', left: 164, top: 134, width: 56, color: COLORS.line, thickness: 4 }),
]

const footer = slideId => text({
  slideId,
  suffix: 'footer',
  left: 780,
  top: 532,
  width: 168,
  height: 18,
  value: 'DEEP BLUE INFOGRAPHIC',
  fontSize: 12,
  color: COLORS.slate,
  align: 'right',
  fontFamily: 'Arial',
})

const slide = ({ id, type, elements, layoutKind, variantMode, background = COLORS.warmWhite }) => ({
  id,
  type,
  elements,
  background: { type: 'solid', color: background },
  remark: sourceRemark,
  ...(layoutKind ? { layoutKind } : {}),
  ...(variantMode ? { variantMode } : {}),
})

const makeCover = ({ id, withImage = false }) => {
  const elements = [
    ...deepBackground(id, ASSETS.cover),
    text({
      slideId: id,
      suffix: 'kicker',
      left: 88,
      top: 160,
      width: 520,
      height: 28,
      value: 'DEEP BLUE · BUSINESS INFOGRAPHIC',
      fontSize: 16,
      color: COLORS.cyan,
      bold: true,
      fontFamily: 'Arial',
    }),
    text({
      slideId: id,
      suffix: 'title',
      left: 88,
      top: 198,
      width: withImage ? 520 : 672,
      height: 128,
      value: '让复杂信息形成清晰行动',
      fontSize: 50,
      color: COLORS.white,
      bold: true,
      textType: 'title',
      lineHeight: 1.25,
    }),
    text({
      slideId: id,
      suffix: 'content',
      left: 92,
      top: 352,
      width: withImage ? 500 : 650,
      height: 82,
      value: '用稳定结构连接观点、证据与下一步。',
      fontSize: 18,
      color: '#DCEAF3',
      textType: 'content',
    }),
    line({ slideId: id, suffix: 'accent', left: 88, top: 452, width: 138, color: COLORS.cyan, thickness: 5 }),
  ]

  if (withImage) {
    elements.push(
      shape({
        slideId: id,
        suffix: 'image-frame',
        left: 650,
        top: 126,
        width: 286,
        height: 318,
        fill: 'rgba(255,255,255,0.12)',
        outline: 'rgba(255,255,255,0.42)',
        outlineWidth: 1,
      }),
      image({
        slideId: id,
        suffix: 'content-image',
        left: 662,
        top: 138,
        width: 262,
        height: 294,
        src: ASSETS.section,
        imageType: 'content',
        strictImageCount: true,
        requireSourceDimensions: true,
      }),
    )
  }
  return slide({ id, type: 'cover', elements, variantMode: 'deterministic', background: COLORS.deepNavy })
}

const makeContents = count => {
  const id = `contents-${count}`
  const elements = [
    ...lightDecoration(id),
    ...header(id, '内容结构'),
    text({
      slideId: id,
      suffix: 'intro',
      left: 642,
      top: 66,
      width: 306,
      height: 48,
      value: '先建立共同视角，再进入证据与行动。',
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
        fill: index % 2 === 0 ? '#FFFFFF' : COLORS.paleCyan,
        outline: COLORS.line,
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
        color: COLORS.ink,
        bold: true,
        textType: 'item',
        group,
      }),
    )
  }
  elements.push(footer(id))
  return slide({ id, type: 'contents', elements })
}

const makeTransition = ({ id, compact = false }) => {
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
      top: compact ? 306 : 190,
      width: compact ? 780 : 4,
      color: 'rgba(255,255,255,0.34)',
      thickness: compact ? 2 : 4,
    }),
    text({
      slideId: id,
      suffix: 'title',
      left: compact ? 92 : 424,
      top: compact ? 326 : 182,
      width: compact ? 760 : 490,
      height: 104,
      value: '先看清问题，再选择行动',
      fontSize: 40,
      color: COLORS.white,
      bold: true,
      textType: 'title',
    }),
    text({
      slideId: id,
      suffix: 'content',
      left: compact ? 96 : 428,
      top: compact ? 430 : 322,
      width: compact ? 700 : 430,
      height: 90,
      value: '本章节将观点、证据与决策标准放在同一结构中。',
      fontSize: 18,
      color: '#DCEAF3',
      textType: 'content',
    }),
  ]
  return slide({ id, type: 'transition', elements, variantMode: 'deterministic', background: COLORS.deepNavy })
}

const cardPositions = count => {
  if (count === 1) return [{ left: 120, top: 178, width: 760, height: 260 }]
  if (count === 2) return [
    { left: 70, top: 174, width: 410, height: 270 },
    { left: 520, top: 174, width: 410, height: 270 },
  ]
  if (count === 3) return [50, 365, 680].map(left => ({ left, top: 176, width: 270, height: 278 }))
  if (count === 4) return [
    { left: 70, top: 150, width: 405, height: 158 },
    { left: 525, top: 150, width: 405, height: 158 },
    { left: 70, top: 338, width: 405, height: 158 },
    { left: 525, top: 338, width: 405, height: 158 },
  ]
  if (count === 5) return [
    ...[50, 365, 680].map(left => ({ left, top: 150, width: 270, height: 158 })),
    ...[205, 525].map(left => ({ left, top: 338, width: 270, height: 158 })),
  ]
  return [
    ...[50, 365, 680].map(left => ({ left, top: 146, width: 270, height: 164 })),
    ...[50, 365, 680].map(left => ({ left, top: 334, width: 270, height: 164 })),
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
      shape({ slideId: id, suffix: 'split-left', left: 0, top: 132, width: 500, height: 390, fill: '#EAF8FC' }),
      shape({ slideId: id, suffix: 'split-right', left: 500, top: 132, width: 500, height: 390, fill: '#FFFFFF' }),
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
        fill: index % 2 === 0 ? '#FFFFFF' : COLORS.paleCyan,
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
        height: compact ? 60 : 58,
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
  return slide({ id, type: 'content', elements, layoutKind })
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

const makeImageContent = count => {
  const id = `content-image-${count}`
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
        fill: '#FFFFFF',
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
  return slide({ id, type: 'content', elements, layoutKind: count >= 3 ? 'gallery' : 'image' })
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
        fill: index === 0 ? COLORS.deepNavy : '#FFFFFF',
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
  return slide({ id, type: 'content', elements, layoutKind: 'metrics' })
}

const makeProcess = count => {
  const id = `content-process-${count}`
  const elements = [
    ...lightDecoration(id),
    ...header(id, '把行动拆成可验证的连续步骤'),
    line({ slideId: id, suffix: 'process-line', left: 105, top: 238, width: 790, color: COLORS.line, thickness: 5 }),
  ]
  const width = count === 4 ? 190 : 154
  const gap = count === 4 ? 48 : 30
  const start = count === 4 ? 84 : 55
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
  return slide({ id, type: 'content', elements, layoutKind: 'process' })
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
      shape({ slideId: id, suffix: `compare-panel-${index + 1}`, ...position, fill: positive ? '#EAF8FC' : '#FFFFFF', outline: positive ? COLORS.cyan : COLORS.line, outlineWidth: 1, group }),
      shape({ slideId: id, suffix: `compare-band-${index + 1}`, left: position.left, top: position.top, width: 10, height: position.height, fill: positive ? COLORS.cyan : COLORS.signal, group }),
      text({ slideId: id, suffix: `item-title-${index + 1}`, left: position.left + 28, top: position.top + 26, width: position.width - 52, height: 54, value: `方案 ${index + 1}`, fontSize: count === 2 ? 26 : 20, color: COLORS.ink, bold: true, textType: 'itemTitle', group }),
      text({ slideId: id, suffix: `item-body-${index + 1}`, left: position.left + 28, top: position.top + 96, width: position.width - 52, height: position.height - 122, value: '对比价值、代价、风险和适用条件。', fontSize: 16, color: COLORS.slate, textType: 'item', group }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'compare' })
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
      shape({ slideId: id, suffix: `hub-panel-${index + 1}`, ...position, fill: index === 0 ? COLORS.deepNavy : '#FFFFFF', outline: index === 0 ? COLORS.deepNavy : COLORS.line, outlineWidth: 1, group }),
      text({ slideId: id, suffix: `item-title-${index + 1}`, left: position.left + 18, top: position.top + 14, width: position.width - 36, height: 34, value: index === 0 ? '中心主张' : `支撑分支 ${index}`, fontSize: index === 0 ? 22 : 18, color: index === 0 ? COLORS.white : COLORS.ink, bold: true, align: 'center', textType: 'itemTitle', group }),
      text({ slideId: id, suffix: `item-body-${index + 1}`, left: position.left + 18, top: position.top + 50, width: position.width - 36, height: position.height - 60, value: '说明依赖关系和业务作用。', fontSize: 16, color: index === 0 ? '#DCEAF3' : COLORS.slate, align: 'center', textType: 'item', group }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'hub-spoke' })
}

const makeTimeline = () => {
  const id = 'content-timeline-4'
  const elements = [
    ...lightDecoration(id),
    ...header(id, '四个里程碑形成连续推进'),
    line({ slideId: id, suffix: 'timeline-line', left: 118, top: 238, width: 764, color: COLORS.line, thickness: 5 }),
  ]
  const lefts = [88, 318, 548, 778]
  lefts.forEach((left, index) => {
    const group = groupId(id, index + 1)
    elements.push(
      shape({ slideId: id, suffix: `node-${index + 1}`, left: left + 50, top: 210, width: 56, height: 56, fill: index === 0 ? COLORS.cyan : COLORS.deepNavy, path: circlePath, group }),
      text({ slideId: id, suffix: `item-number-${index + 1}`, left: left + 50, top: 226, width: 56, height: 22, value: String(index + 1).padStart(2, '0'), fontSize: 14, color: COLORS.white, bold: true, align: 'center', textType: 'itemNumber', group, fontFamily: 'Arial' }),
      text({ slideId: id, suffix: `item-title-${index + 1}`, left, top: 292, width: 156, height: 48, value: `里程碑 ${index + 1}`, fontSize: 20, color: COLORS.ink, bold: true, align: 'center', textType: 'itemTitle', group }),
      text({ slideId: id, suffix: `item-body-${index + 1}`, left, top: 350, width: 156, height: 104, value: '说明阶段结果、证据和下一步。', fontSize: 16, color: COLORS.slate, align: 'center', textType: 'item', group }),
    )
  })
  elements.push(footer(id))
  return slide({ id, type: 'content', elements, layoutKind: 'timeline' })
}

const makeEnd = ({ id, contact = false }) => {
  const elements = [
    ...deepBackground(id, ASSETS.end),
    text({ slideId: id, suffix: 'kicker', left: 150, top: 150, width: 700, height: 26, value: contact ? 'ALIGN · COMMIT · DELIVER' : 'CLARITY · TRUST · NEXT STEP', fontSize: 14, color: COLORS.cyan, bold: true, align: 'center', fontFamily: 'Arial' }),
    text({ slideId: id, suffix: 'title', left: 120, top: 196, width: 760, height: 116, value: contact ? '让共识转化为下一步行动' : '让清晰表达推动下一步', fontSize: 48, color: COLORS.white, bold: true, align: 'center', textType: 'title' }),
    line({ slideId: id, suffix: 'end-line-a', left: 380, top: 334, width: 150, color: COLORS.cyan, thickness: 4 }),
    line({ slideId: id, suffix: 'end-line-b', left: 530, top: 334, width: 90, color: 'rgba(255,255,255,0.34)', thickness: 4 }),
    text({ slideId: id, suffix: 'content', left: 160, top: 356, width: 680, height: 96, value: contact ? '明确负责人、完成标准和复盘时间。' : '感谢聆听，期待一起把下一步变得更清晰。', fontSize: 18, color: '#DCEAF3', align: 'center', textType: 'content' }),
  ]
  return slide({ id, type: 'end', elements, variantMode: 'deterministic', background: COLORS.deepNavy })
}

const allSlides = [
  makeCover({ id: 'cover-minimal' }),
  makeCover({ id: 'cover-with-image', withImage: true }),
  ...[2, 3, 4, 5, 6, 10].map(makeContents),
  makeTransition({ id: 'transition-numbered' }),
  makeTransition({ id: 'transition-compact', compact: true }),
  makeTextContent({ id: 'content-text-1', count: 1, layoutKind: 'focus' }),
  makeTextContent({ id: 'content-text-2', count: 2 }),
  makeTextContent({ id: 'content-text-3', count: 3 }),
  makeTextContent({ id: 'content-text-4', count: 4 }),
  makeTextContent({ id: 'content-text-5', count: 5 }),
  makeTextContent({ id: 'content-text-6', count: 6 }),
  makeTextContent({ id: 'content-text-2-alt', count: 2, variant: 'split' }),
  makeTextContent({ id: 'content-text-3-alt', count: 3, variant: 'steps' }),
  makeTextContent({ id: 'content-text-4-alt', count: 4, variant: 'quadrant' }),
  ...[1, 2, 3, 4, 5, 6].map(makeImageContent),
  ...[3, 4, 5].map(makeMetrics),
  ...[4, 5].map(makeProcess),
  ...[2, 4].map(makeCompare),
  makeHubSpoke(),
  makeTimeline(),
  makeEnd({ id: 'end-action' }),
  makeEnd({ id: 'end-contact', contact: true }),
]

const mvpSlideIds = [
  'cover-minimal',
  'contents-3',
  'contents-4',
  'contents-6',
  'transition-numbered',
  'content-text-1',
  'content-text-2',
  'content-text-3',
  'content-text-4',
  'content-text-5',
  'content-text-6',
  'content-image-1',
  'content-image-2',
  'content-image-4',
  'content-image-6',
  'content-metrics-4',
  'content-process-4',
  'end-action',
]

const selectedSlides = stage === 'mvp'
  ? allSlides.filter(candidate => mvpSlideIds.includes(candidate.id))
  : allSlides

const template = {
  id: 'template_14',
  title: '深蓝青棱商务信息图',
  width: 1000,
  height: 562.5,
  theme: {
    themeColors: [COLORS.deepNavy, COLORS.navy, COLORS.cyan, COLORS.blue, COLORS.signal],
    fontColor: COLORS.ink,
    fontName: '微软雅黑',
    backgroundColor: COLORS.warmWhite,
  },
  slides: selectedSlides,
  metadata: {
    aspectRatio: '16:9',
    sourceReference: '扁平风格(38).pptx（仅抽象布局规律）',
    imageSlotMarker: 'imageType=content',
    decorativeImageMarker: 'imageType=decoration',
    assetGeneration: 'built-in image_gen; model identifier not exposed',
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

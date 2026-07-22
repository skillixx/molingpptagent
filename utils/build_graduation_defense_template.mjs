#!/usr/bin/env node

/**
 * 将前端导出的毕业答辩 PPT JSON 整理为 TrainPPTAgent 可复用模板。
 *
 * 处理内容：
 * 1. 删除素材附录和不适合自动填充的复杂页面；
 * 2. 将固定章节导航收敛为一个可替换的页面标题槽位；
 * 3. 标注页面、文字、图片和图表语义；
 * 4. 抽离 Base64 图片，避免模板 JSON 体积过大。
 */

import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { basename, dirname, extname, join, resolve } from 'node:path'

const [, , inputArg, outputArg, assetDirArg] = process.argv

if (!inputArg || !outputArg || !assetDirArg) {
  console.error('用法: node build_graduation_defense_template.mjs <原始JSON> <模板JSON> <素材目录>')
  process.exit(1)
}

const inputPath = resolve(inputArg)
const outputPath = resolve(outputArg)
const assetDir = resolve(assetDirArg)

// 模板只保留能被当前生成器稳定复用的页面。
const INCLUDED_SLIDES = [
  1, 2, 3,
  4, 5, 6,
  8, 9, 10, 11,
  12, 13, 14, 15,
  19, 20, 21,
  24, 25, 26,
]

const PAGE_TYPES = new Map([
  [1, 'cover'],
  [2, 'cover'],
  [3, 'contents'],
  [4, 'transition'],
  [5, 'content'],
  [6, 'transition'],
  [8, 'content'],
  [9, 'content'],
  [10, 'content'],
  [11, 'transition'],
  [12, 'content'],
  [13, 'content'],
  [14, 'content'],
  [15, 'transition'],
  [19, 'transition'],
  [20, 'content'],
  [21, 'transition'],
  [24, 'content'],
  [25, 'end'],
  [26, 'end'],
])

const CHAPTER_LABELS = new Set([
  '论文绪论',
  '研究背景',
  '研究方法',
  '研究结果',
  '问题讨论',
  '论文总结',
])

const normalizeText = value => String(value || '')
  .replace(/<[^>]+>/g, ' ')
  .replace(/&nbsp;/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()

const getElementText = element => {
  if (element.type === 'text') return normalizeText(element.content)
  if (element.type === 'shape' && element.text) return normalizeText(element.text.content)
  return ''
}

// 商业化视觉系统：统一背景、版心、字体和强调色，避免原模板中的彩色卡通素材互相抢夺注意力。
const COMMERCIAL_TOKENS = {
  contentBackground: '/api/data/template_5_commercial_content_bg_v1.png',
  sectionBackground: '/api/data/template_5_commercial_section_bg_v1.png',
  ivory: '#F7F4EF',
  paper: '#FFFFFF',
  red: '#B42318',
  darkRed: '#7A1712',
  charcoal: '#252525',
  body: '#4A4642',
  muted: '#817A73',
  rule: '#D8D0C8',
}

const escapeHtml = value => String(value || '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')

const makeTextHtml = (text, {
  color = COMMERCIAL_TOKENS.charcoal,
  fontSize = 24,
  fontWeight = 'normal',
  align = 'left',
  letterSpacing = 0,
} = {}) => {
  const weightStyle = fontWeight === 'normal' ? '' : `font-weight: ${fontWeight};`
  const spacingStyle = letterSpacing ? `letter-spacing: ${letterSpacing}px;` : ''
  return `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: 微软雅黑;${weightStyle}${spacingStyle}">${escapeHtml(text)}</span></p>`
}

const styleElementText = (element, options = {}) => {
  const html = makeTextHtml(getElementText(element), options)
  if (element.type === 'text') {
    element.content = html
    element.defaultFontName = '微软雅黑'
    element.defaultColor = options.color || COMMERCIAL_TOKENS.charcoal
    element.fill = ''
    element.outline = { color: '#000000', width: 0, style: 'solid' }
  }
  if (element.type === 'shape' && element.text) {
    element.text.content = html
    element.text.defaultFontName = '微软雅黑'
    element.text.defaultColor = options.color || COMMERCIAL_TOKENS.charcoal
    element.text.align = options.verticalAlign || 'top'
    element.fill = options.fill || ''
    element.outline = options.outline || { color: '#000000', width: 0, style: 'solid' }
  }
}

const createTextElement = ({
  id,
  text,
  left,
  top,
  width,
  height,
  role,
  groupId,
  color,
  fontSize,
  fontWeight,
  align,
  letterSpacing,
}) => ({
  type: 'text',
  id,
  width,
  height,
  left,
  top,
  rotate: 0,
  defaultFontName: '微软雅黑',
  defaultColor: color || COMMERCIAL_TOKENS.charcoal,
  content: makeTextHtml(text, { color, fontSize, fontWeight, align, letterSpacing }),
  lineHeight: 1,
  outline: { color: '#000000', width: 0, style: 'solid' },
  fill: '',
  vertical: false,
  ...(role ? { textType: role } : {}),
  ...(groupId ? { groupId } : {}),
})

const createRectElement = ({ id, left, top, width, height, fill, groupId }) => ({
  type: 'shape',
  id,
  width,
  height,
  left,
  top,
  viewBox: [200, 200],
  path: 'M 0 0 L 200 0 L 200 200 L 0 200 Z',
  fill,
  fixedRatio: false,
  rotate: 0,
  outline: { color: '#000000', width: 0, style: 'solid' },
  text: { content: '', defaultFontName: '微软雅黑', defaultColor: COMMERCIAL_TOKENS.charcoal, align: 'middle' },
  flipH: false,
  flipV: false,
  ...(groupId ? { groupId } : {}),
})

const getBackgroundElement = slide => slide.elements.find(element => (
  element.type === 'image' && element.width > 1100 && element.height > 650
))

const setCommercialBackground = (slide, src) => {
  let background = getBackgroundElement(slide)
  if (!background) {
    background = {
      type: 'image',
      id: `${slide.id}-commercial-background`,
      src,
      left: 0,
      top: 0,
      width: 1280,
      height: 720,
      rotate: 0,
      fixedRatio: false,
      flipH: false,
      flipV: false,
    }
  }
  Object.assign(background, { src, left: 0, top: 0, width: 1280, height: 720, rotate: 0 })
  return background
}

const createContentHeader = (slide, titleElement) => {
  Object.assign(titleElement, { left: 104, top: 36, width: 900, height: 52 })
  styleElementText(titleElement, {
    color: COMMERCIAL_TOKENS.charcoal,
    fontSize: 40,
    fontWeight: 'bold',
    align: 'left',
  })
  return [
    createRectElement({
      id: `${slide.id}-header-accent`, left: 76, top: 43, width: 7, height: 34, fill: COMMERCIAL_TOKENS.red,
    }),
    createRectElement({
      id: `${slide.id}-header-rule`, left: 76, top: 102, width: 1128, height: 2, fill: '#B4231840',
    }),
    titleElement,
  ]
}

const commercializeCover = slide => {
  const background = setCommercialBackground(slide, COMMERCIAL_TOKENS.contentBackground)
  const title = slide.elements.find(element => getTextType(element) === 'title')
  const subtitle = slide.elements.find(element => getTextType(element) === 'content')
  if (!title) return

  Object.assign(title, { left: 122, top: 245, width: 880, height: 118 })
  styleElementText(title, {
    color: COMMERCIAL_TOKENS.charcoal,
    fontSize: 64,
    fontWeight: 'bold',
    align: 'left',
    letterSpacing: 1,
  })
  if (subtitle) {
    Object.assign(subtitle, { left: 124, top: 382, width: 720, height: 52 })
    styleElementText(subtitle, { color: COMMERCIAL_TOKENS.muted, fontSize: 24, align: 'left' })
  }

  slide.elements = [
    background,
    createTextElement({
      id: `${slide.id}-cover-kicker`, text: 'GRADUATION DEFENSE', left: 124, top: 190,
      width: 360, height: 30, color: COMMERCIAL_TOKENS.red, fontSize: 19, fontWeight: 'bold',
      align: 'left', letterSpacing: 2,
    }),
    createRectElement({
      id: `${slide.id}-cover-rule`, left: 124, top: 225, width: 92, height: 5, fill: COMMERCIAL_TOKENS.red,
    }),
    title,
    ...(subtitle ? [subtitle] : []),
  ]
}

const commercializeContents = slide => {
  const background = setCommercialBackground(slide, COMMERCIAL_TOKENS.contentBackground)
  const items = sortByPosition(slide.elements.filter(element => getTextType(element) === 'item')).slice(0, 6)
  const fixedTexts = slide.elements.filter(element => element.type === 'text' && !getTextType(element))
  const englishTitle = fixedTexts.find(element => /CONTENTS/i.test(getElementText(element)))
  const chineseTitle = fixedTexts.find(element => /目\s*录/.test(getElementText(element)))

  if (englishTitle) {
    Object.assign(englishTitle, { left: 78, top: 58, width: 260, height: 30 })
    styleElementText(englishTitle, {
      color: COMMERCIAL_TOKENS.red, fontSize: 18, fontWeight: 'bold', align: 'left', letterSpacing: 2,
    })
  }
  if (chineseTitle) {
    Object.assign(chineseTitle, { left: 76, top: 88, width: 260, height: 72 })
    styleElementText(chineseTitle, {
      color: COMMERCIAL_TOKENS.charcoal, fontSize: 50, fontWeight: 'bold', align: 'left',
    })
  }

  const contentElements = []
  items.forEach((item, index) => {
    const column = index % 2
    const row = Math.floor(index / 2)
    const groupId = `${slide.id}-contents-group-${index + 1}`
    const left = column === 0 ? 92 : 666
    const top = 206 + row * 142
    Object.assign(item, { left: left + 72, top, width: 430, height: 48, groupId })
    styleElementText(item, {
      color: COMMERCIAL_TOKENS.charcoal, fontSize: 29, fontWeight: 'bold', align: 'left',
    })
    contentElements.push(
      createTextElement({
        id: `${groupId}-number`, text: String(index + 1).padStart(2, '0'), left, top: top + 1,
        width: 58, height: 44, role: 'itemNumber', groupId,
        color: COMMERCIAL_TOKENS.red, fontSize: 25, fontWeight: 'bold', align: 'left',
      }),
      item,
      createRectElement({
        id: `${groupId}-rule`, left, top: top + 62, width: 500, height: 2, fill: COMMERCIAL_TOKENS.rule, groupId,
      }),
    )
  })

  slide.elements = [
    background,
    ...(englishTitle ? [englishTitle] : []),
    ...(chineseTitle ? [chineseTitle] : []),
    createRectElement({
      id: `${slide.id}-contents-divider`, left: 628, top: 190, width: 2, height: 420, fill: '#B4231826',
    }),
    ...contentElements,
  ]
}

const commercializeTransition = slide => {
  const background = setCommercialBackground(slide, COMMERCIAL_TOKENS.sectionBackground)
  const title = slide.elements.find(element => getTextType(element) === 'title')
  if (!title) return
  Object.assign(title, { left: 190, top: 286, width: 800, height: 92 })
  styleElementText(title, {
    color: COMMERCIAL_TOKENS.charcoal, fontSize: 58, fontWeight: 'bold', align: 'left',
  })

  slide.elements = [
    background,
    createTextElement({
      id: `${slide.id}-part-number`, text: '01', left: 190, top: 194, width: 100, height: 56,
      role: 'partNumber', color: COMMERCIAL_TOKENS.red, fontSize: 34, fontWeight: 'bold', align: 'left',
    }),
    createTextElement({
      id: `${slide.id}-section-label`, text: 'SECTION', left: 286, top: 207, width: 180, height: 30,
      color: COMMERCIAL_TOKENS.muted, fontSize: 17, fontWeight: 'bold', align: 'left', letterSpacing: 2,
    }),
    createRectElement({
      id: `${slide.id}-transition-rule`, left: 190, top: 264, width: 96, height: 5, fill: COMMERCIAL_TOKENS.red,
    }),
    title,
    createTextElement({
      id: `${slide.id}-transition-summary`, text: '章节核心观点与关键结论', left: 192, top: 398,
      width: 720, height: 70, role: 'content', color: COMMERCIAL_TOKENS.body,
      fontSize: 24, align: 'left',
    }),
  ]
}

const createItemTitle = (slide, index, left, top, width, groupId) => createTextElement({
  id: `${slide.id}-item-title-${index + 1}`,
  text: '要点标题',
  left,
  top,
  width,
  height: 44,
  role: 'itemTitle',
  groupId,
  color: COMMERCIAL_TOKENS.charcoal,
  fontSize: 28,
  fontWeight: 'bold',
  align: 'left',
})

const createItemNumber = (slide, index, left, top, groupId) => createTextElement({
  id: `${slide.id}-item-number-${index + 1}`,
  text: String(index + 1).padStart(2, '0'),
  left,
  top,
  width: 54,
  height: 40,
  role: 'itemNumber',
  groupId,
  color: COMMERCIAL_TOKENS.red,
  fontSize: 22,
  fontWeight: 'bold',
  align: 'left',
})

const commercializeTextContent = (slide, background, header, bodies, singleContent) => {
  const elements = [background, ...header]

  if (!bodies.length && singleContent) {
    Object.assign(singleContent, { left: 170, top: 214, width: 940, height: 270 })
    styleElementText(singleContent, {
      color: COMMERCIAL_TOKENS.body, fontSize: 28, align: 'center', verticalAlign: 'middle',
    })
    if (singleContent.type === 'shape') {
      singleContent.fill = '#FFFFFFB8'
      singleContent.outline = { color: COMMERCIAL_TOKENS.rule, width: 1, style: 'solid' }
    }
    elements.push(
      createRectElement({
        id: `${slide.id}-single-accent`, left: 612, top: 178, width: 56, height: 5, fill: COMMERCIAL_TOKENS.red,
      }),
      singleContent,
    )
    slide.elements = elements
    return
  }

  const count = bodies.length
  bodies.forEach((body, index) => {
    const groupId = `${slide.id}-text-item-${index + 1}`
    let left = 96
    let top = 160
    let width = 1088
    let bodyTop = top + 50
    let bodyHeight = 82
    let titleLeft = left + 64
    let titleWidth = width - 64

    if (count === 2) {
      left = index === 0 ? 96 : 668
      top = 184
      width = 516
      bodyTop = 258
      bodyHeight = 250
      titleLeft = left + 64
      titleWidth = width - 64
    }
    else if (count === 3) {
      top = 154 + index * 169
      bodyTop = top + 48
      bodyHeight = 92
    }
    else if (count >= 4) {
      const column = index % 2
      const row = Math.floor(index / 2)
      left = column === 0 ? 96 : 668
      // 拉开两行的纵向距离，使前端按“从左到右、从上到下”稳定映射 01→04。
      top = 150 + row * 290
      width = 516
      bodyTop = top + 54
      bodyHeight = 120
      titleLeft = left + 64
      titleWidth = width - 64
    }

    Object.assign(body, { left: titleLeft, top: bodyTop, width: titleWidth, height: bodyHeight, groupId })
    styleElementText(body, {
      color: COMMERCIAL_TOKENS.body,
      fontSize: count === 2 ? 24 : 23,
      align: 'left',
      verticalAlign: 'top',
      fill: '',
      outline: { color: '#000000', width: 0, style: 'solid' },
    })

    elements.push(
      createItemNumber(slide, index, left, top + 2, groupId),
      createItemTitle(slide, index, titleLeft, top, titleWidth, groupId),
      body,
      createRectElement({
        id: `${groupId}-rule`, left, top: bodyTop + bodyHeight + 16,
        width, height: 2, fill: index === 0 ? '#B4231866' : COMMERCIAL_TOKENS.rule, groupId,
      }),
    )
  })

  slide.elements = elements
}

const commercializeImageContent = (slide, background, header, images, bodies, subtitles, contents) => {
  const elements = [background, ...header]
  if (images.length === 1) {
    const image = images[0]
    const subtitle = subtitles[0]
    const body = contents[0] || bodies[0]
    Object.assign(image, { left: 76, top: 150, width: 540, height: 390 })
    elements.push(image)
    if (subtitle) {
      Object.assign(subtitle, { left: 670, top: 178, width: 500, height: 58 })
      styleElementText(subtitle, {
        color: COMMERCIAL_TOKENS.charcoal, fontSize: 32, fontWeight: 'bold', align: 'left',
      })
      elements.push(subtitle)
    }
    if (body) {
      setTextType(body, 'content')
      Object.assign(body, { left: 670, top: 260, width: 500, height: 220 })
      styleElementText(body, { color: COMMERCIAL_TOKENS.body, fontSize: 24, align: 'left' })
      elements.push(body)
    }
    elements.push(createRectElement({
      id: `${slide.id}-image-accent`, left: 670, top: 240, width: 76, height: 4, fill: COMMERCIAL_TOKENS.red,
    }))
    slide.elements = elements
    return
  }

  const count = Math.min(images.length, 3)
  for (let index = 0; index < count; index += 1) {
    const left = 76 + index * 382
    const image = images[index]
    const title = subtitles[index] || createItemTitle(slide, index, left, 392, 340, `${slide.id}-image-${index + 1}`)
    const body = bodies[index] || contents[index]
    Object.assign(image, { left, top: 154, width: 340, height: 218 })
    // 图片型内容由前端按 subtitle/content 替换，不能沿用纯文本页的 itemTitle/item。
    setTextType(title, 'subtitle')
    Object.assign(title, { left, top: 396, width: 340, height: 46 })
    styleElementText(title, {
      color: COMMERCIAL_TOKENS.charcoal, fontSize: 27, fontWeight: 'bold', align: 'left',
    })
    elements.push(image, title)
    if (body) {
      setTextType(body, 'content')
      Object.assign(body, { left, top: 456, width: 340, height: 142 })
      styleElementText(body, { color: COMMERCIAL_TOKENS.body, fontSize: 21, align: 'left' })
      elements.push(body)
    }
    elements.push(createRectElement({
      id: `${slide.id}-image-rule-${index + 1}`, left, top: 442, width: 58, height: 4, fill: COMMERCIAL_TOKENS.red,
    }))
  }
  slide.elements = elements
}

const commercializeContent = slide => {
  const background = setCommercialBackground(slide, COMMERCIAL_TOKENS.contentBackground)
  const title = slide.elements.find(element => getTextType(element) === 'title')
  if (!title) return
  const header = createContentHeader(slide, title)
  const charts = slide.elements.filter(element => element.type === 'chart')
  const images = sortByPosition(slide.elements.filter(element => element.imageType === 'itemFigure'))
  const bodies = sortByPosition(slide.elements.filter(element => getTextType(element) === 'item'))
  const subtitles = sortByPosition(slide.elements.filter(element => ['itemTitle', 'subtitle'].includes(getTextType(element))))
  const contents = sortByPosition(slide.elements.filter(element => getTextType(element) === 'content'))

  if (charts.length) {
    const chart = charts[0]
    Object.assign(chart, {
      left: 120, top: 148, width: 1040, height: 390,
      themeColors: [COMMERCIAL_TOKENS.red, COMMERCIAL_TOKENS.charcoal, '#A8786E', '#D0A099', '#8B827B'],
      textColor: COMMERCIAL_TOKENS.body,
    })
    const insight = contents[0]
    if (insight) {
      Object.assign(insight, { left: 170, top: 565, width: 940, height: 66 })
      styleElementText(insight, { color: COMMERCIAL_TOKENS.body, fontSize: 22, align: 'center' })
    }
    slide.elements = [background, ...header, chart, ...(insight ? [insight] : [])]
    return
  }

  if (images.length) {
    commercializeImageContent(slide, background, header, images, bodies, subtitles, contents)
    return
  }

  commercializeTextContent(slide, background, header, bodies, contents[0])
}

const commercializeEnd = slide => {
  const background = setCommercialBackground(slide, COMMERCIAL_TOKENS.contentBackground)
  const mainText = slide.elements.find(element => getElementText(element))
  if (!mainText) return
  Object.assign(mainText, { left: 122, top: 276, width: 820, height: 100 })
  styleElementText(mainText, {
    color: COMMERCIAL_TOKENS.charcoal, fontSize: 58, fontWeight: 'bold', align: 'left',
  })
  slide.elements = [
    background,
    createTextElement({
      id: `${slide.id}-end-kicker`, text: 'THANK YOU', left: 124, top: 220,
      width: 260, height: 32, color: COMMERCIAL_TOKENS.red,
      fontSize: 19, fontWeight: 'bold', align: 'left', letterSpacing: 2,
    }),
    createRectElement({
      id: `${slide.id}-end-rule`, left: 124, top: 258, width: 92, height: 5, fill: COMMERCIAL_TOKENS.red,
    }),
    mainText,
  ]
}

const applyCommercialDesign = slide => {
  if (slide.type === 'cover') commercializeCover(slide)
  else if (slide.type === 'contents') commercializeContents(slide)
  else if (slide.type === 'transition') commercializeTransition(slide)
  else if (slide.type === 'content') commercializeContent(slide)
  else if (slide.type === 'end') commercializeEnd(slide)
}

const setTextType = (element, textType) => {
  if (element.type === 'text') element.textType = textType
  if (element.type === 'shape' && element.text) element.text.type = textType
}

const getTextType = element => {
  if (element.type === 'text') return element.textType
  if (element.type === 'shape' && element.text) return element.text.type
  return undefined
}

const setElementHtml = (element, html) => {
  if (element.type === 'text') element.content = html
  if (element.type === 'shape' && element.text) element.text.content = html
}

const collapseSemanticText = element => {
  const role = getTextType(element)
  if (!role) return

  const original = element.type === 'text' ? element.content : element.text?.content
  if (typeof original !== 'string') return

  // 生成器只替换第一个文本节点，因此先把复杂的多段富文本压成单一文本节点，避免旧句子残留。
  const paragraphOpen = original.match(/<p\b[^>]*>/i)?.[0] || '<p>'
  const spanOpen = original.match(/<span\b[^>]*>/i)?.[0]
  const placeholders = {
    title: '页面标题',
    content: '正文内容',
    item: '内容要点',
    itemTitle: '要点标题',
    itemNumber: '01',
    partNumber: '01',
  }
  const placeholder = placeholders[role] || '文本内容'
  const minimumFontSizes = {
    title: 32,
    content: 24,
    item: 24,
    itemTitle: 26,
    subtitle: 28,
    itemNumber: 32,
    partNumber: 32,
  }
  const minimumFontSize = minimumFontSizes[role] || 22
  let html = spanOpen
    ? `${paragraphOpen}${spanOpen}${placeholder}</span></p>`
    : `${paragraphOpen}${placeholder}</p>`

  // 保留原稿较大的字号，只抬高过小的正文，避免投影场景下内容难以阅读。
  if (/font-size:\s*[0-9.]+px/i.test(html)) {
    html = html.replace(/font-size:\s*([0-9.]+)px/gi, (_, value) => (
      `font-size: ${Math.max(Number(value), minimumFontSize)}px`
    ))
  }
  else {
    html = html.replace(/<p\b/i, `<p style="font-size: ${minimumFontSize}px;"`)
  }
  setElementHtml(element, html)
}

const bringSemanticSlotsToFront = slide => {
  // 可替换内容最后渲染，防止原稿的装饰图形盖住标题、正文、图片或图表。
  const semantic = slide.elements.filter(element => (
    Boolean(getTextType(element))
    || element.imageType === 'itemFigure'
    || element.type === 'chart'
  ))
  const semanticIds = new Set(semantic.map(element => element.id))
  slide.elements = [
    ...slide.elements.filter(element => !semanticIds.has(element.id)),
    ...semantic,
  ]
}

const replaceElementText = (element, searchValue, replacement) => {
  if (element.type === 'text' && typeof element.content === 'string') {
    element.content = element.content.replace(searchValue, replacement)
  }
  if (element.type === 'shape' && element.text && typeof element.text.content === 'string') {
    element.text.content = element.text.content.replace(searchValue, replacement)
  }
}

const overlapsHorizontally = (first, second) => {
  const firstRight = first.left + first.width
  const secondRight = second.left + second.width
  return Math.min(firstRight, secondRight) - Math.max(first.left, second.left) > 20
}

const stripCoverMetadata = slide => {
  // 封面只保留主标题和一行副标题，避免生成结果残留“答辩人/指导老师/xxxxx”。
  slide.elements = slide.elements.filter(element => {
    if (element.top < 450 || element.left >= 700) return true
    return false
  })

  for (const element of slide.elements) {
    const text = getElementText(element)
    if (text.includes('毕业答辩模板')) setTextType(element, 'title')
    else if (text.includes('学院') || text.includes('班')) setTextType(element, 'content')
  }
}

const simplifyContentsSlide = slide => {
  // 原目录页的校园插画被解析成 800 多个小形状，删除这些形状可避免卡顿和 SVG Infinity 错误。
  slide.elements = slide.elements.filter(element => element.type === 'image' || element.type === 'text')

  for (const element of slide.elements) {
    const text = getElementText(element)
    if (text === 'CONTANTS') {
      replaceElementText(element, /CONTANTS/g, 'CONTENTS')
      // 原稿英文目录标题向左越界，向内收回后仍保留左侧构图。
      Object.assign(element, { left: 32, width: 305 })
    }
    if (/^[一二三四五六七八九十]+、/.test(text)) setTextType(element, 'item')
  }
}

const simplifyContentHeader = slide => {
  const activePill = slide.elements.find(element => (
    element.type === 'shape'
    && element.top >= 0
    && element.top <= 30
    && element.width >= 130
    && element.width <= 200
    && element.height >= 35
    && element.height <= 60
  ))

  const titleElement = activePill
    ? slide.elements.find(element => (
      element.type === 'text'
      && element.top < 70
      && CHAPTER_LABELS.has(getElementText(element))
      && overlapsHorizontally(element, activePill)
    ))
    : undefined

  slide.elements = slide.elements.filter(element => {
    if (element.top >= 83) return true
    if (element.type === 'image') return true
    if (element.type === 'shape' && element.width > 1000) return true
    return element === activePill || element === titleElement
  })

  if (activePill) {
    activePill.left = 32
    activePill.top = 8
    activePill.width = 620
    activePill.height = 48
  }

  if (titleElement) {
    titleElement.left = 50
    titleElement.top = 8
    titleElement.width = 580
    titleElement.height = 48
    setTextType(titleElement, 'title')
  }
}

const tagContentSlots = slide => {
  const textElements = slide.elements.filter(element => getElementText(element) && element.top >= 100)
  const bodyElements = textElements.filter(element => getElementText(element).length >= 18)

  // 单段正文使用 content；多项内容使用 item，匹配现有生成器的模板选择规则。
  for (const element of bodyElements) {
    setTextType(element, bodyElements.length === 1 ? 'content' : 'item')
  }

  const bodySet = new Set(bodyElements)
  const shortTextElements = textElements.filter(element => {
    if (bodySet.has(element)) return false
    const text = getElementText(element)
    return text.length >= 2 && text.length <= 12
  })

  const pureNumberElements = shortTextElements.filter(element => /^\d{1,2}$/.test(getElementText(element)))
  if (bodyElements.length > 1 && pureNumberElements.length === bodyElements.length) {
    for (const element of pureNumberElements) setTextType(element, 'itemNumber')
  }

  const titleElements = shortTextElements.filter(element => {
    const text = getElementText(element)
    return !/^\d/.test(text) && !/PENCIL|DEMO|book like/i.test(text)
  })
  if (bodyElements.length > 1 && titleElements.length === bodyElements.length) {
    for (const element of titleElements) setTextType(element, 'itemTitle')
  }

  // 与内容项对应的多图页面使用 itemFigure；整页背景不参与图片替换。
  const contentImages = slide.elements.filter(element => (
    element.type === 'image'
    && element.top >= 100
    && element.width < 1100
    && element.height < 650
  ))
  if (contentImages.length && contentImages.length === bodyElements.length) {
    for (const image of contentImages) image.imageType = 'itemFigure'
  }

  // 清除明显的示例占位词，防止生成后的页面残留英文样例。
  slide.elements = slide.elements.filter(element => !/PENCIL|DEMO|name is that book like/i.test(getElementText(element)))

  // 内容区未标注语义的固定文案无法被 AI 替换，删除后可避免出现原模板的旧标题或说明。
  slide.elements = slide.elements.filter(element => {
    if (element.top < 100 || !getElementText(element)) return true
    return Boolean(getTextType(element))
  })
}

const polishStackedTextLayout = slide => {
  const bodies = sortByPosition(slide.elements.filter(element => (
    getTextType(element) === 'item'
    && element.type === 'shape'
    && element.width > 800
  )))
  if (bodies.length !== 3) return

  // 复用原稿的三块正文形状，改成轻量信息带，增强层次但不压缩可用文字区域。
  const fills = ['#FFF4F1', '#FFFFFF', '#FFF4F1']
  bodies.forEach((body, index) => {
    Object.assign(body, {
      left: 150,
      top: 145 + index * 165,
      width: 1000,
      height: 125,
      fill: fills[index],
      outline: { color: '#F1B4AD', width: 1, style: 'solid' },
      shadow: { h: 0, v: 3, blur: 8, color: '#7D2B221F' },
    })
  })
  // 原稿底部的短线在信息带版式里会形成无意义噪声。
  slide.elements = slide.elements.filter(element => element.type !== 'line')
}

const polishFourItemLayout = slide => {
  const bodies = slide.elements.filter(element => (
    getTextType(element) === 'item'
    && element.type === 'shape'
  ))
  if (bodies.length !== 4) return

  // 四要点页把文字锁定在左右安全栏，中间 500px 专门留给原稿图形，杜绝装饰侵入阅读区。
  const leftBodies = bodies.filter(body => body.left < 640).sort((first, second) => first.top - second.top)
  const rightBodies = bodies.filter(body => body.left >= 640).sort((first, second) => first.top - second.top)
  leftBodies.forEach((body, index) => Object.assign(body, {
    left: 45,
    top: 175 + index * 300,
    width: 330,
    height: 145,
  }))
  rightBodies.forEach((body, index) => Object.assign(body, {
    left: 905,
    top: 175 + index * 300,
    width: 330,
    height: 145,
  }))
}

const removeOverflowingDecorations = slide => {
  // 仅删除正文区域越过画布底边的非语义装饰；背景和可替换内容保持不变。
  slide.elements = slide.elements.filter(element => {
    if (getTextType(element) || element.imageType === 'itemFigure' || element.type === 'chart') return true
    if (element.type !== 'shape' || element.top < 80) return true
    return element.top + element.height <= 720
  })
}

const createChartElement = () => ({
  type: 'chart',
  id: 'graduationChartSlot',
  chartType: 'bar',
  left: 145,
  top: 145,
  width: 990,
  height: 360,
  rotate: 0,
  themeColors: ['#E74E3E', '#FFC000', '#56B4C3', '#8E5AA7', '#91CC75'],
  textColor: '#666666',
  data: {
    labels: ['第一项', '第二项', '第三项', '第四项'],
    legends: ['数据'],
    series: [[220, 440, 350, 160]],
  },
  chartMark: 'item',
})

const rebuildChartSlide = slide => {
  const background = slide.elements.filter(element => element.type === 'image' && element.width > 1100)
  const header = slide.elements.filter(element => element.top < 83 && element.type !== 'image')
  const content = slide.elements.filter(element => (
    element.top >= 500
    && getElementText(element).length >= 18
  ))
  slide.elements = [...background, ...header, createChartElement(), ...content]
  for (const element of content) setTextType(element, 'content')
}

const stripEndMetadata = slide => {
  // 结束页保留主致谢语，删除学校、学院、班级等演示占位信息。
  slide.elements = slide.elements.filter(element => !/学院|班|学校|答辩人|指导老师|x{2,}/i.test(getElementText(element)))
  // 与底部元信息配套的小标签在文字删除后会变成空框，也一并清理。
  slide.elements = slide.elements.filter(element => !(
    element.type === 'shape'
    && !getElementText(element)
    && element.top > 430
    && element.width < 300
  ))
}

const sortByPosition = elements => [...elements].sort((first, second) => (
  (first.top * 2 + first.left) - (second.top * 2 + second.left)
))

const assignVariantIds = (slide, suffix) => {
  slide.id = `${slide.id || 'graduation-layout'}-${suffix}`
  for (const element of slide.elements) element.id = `${element.id}-${suffix}`
  return slide
}

const createTextVariant = (sourceSlide, count) => {
  const slide = assignVariantIds(structuredClone(sourceSlide), `text-${count}`)
  const itemIds = new Set(sortByPosition(slide.elements.filter(element => getTextType(element) === 'item'))
    .slice(0, count)
    .map(element => element.id))
  const titleIds = new Set(sortByPosition(slide.elements.filter(element => getTextType(element) === 'itemTitle'))
    .slice(0, count)
    .map(element => element.id))
  const numberIds = new Set(sortByPosition(slide.elements.filter(element => getTextType(element) === 'itemNumber'))
    .slice(0, count)
    .map(element => element.id))

  slide.elements = slide.elements.filter(element => {
    const role = getTextType(element)
    if (role === 'item') return itemIds.has(element.id)
    if (role === 'itemTitle') return titleIds.has(element.id)
    if (role === 'itemNumber') return numberIds.has(element.id)
    return true
  })

  if (count === 1) {
    // 单段文字直接沿用原稿槽位，仅修改语义，避免破坏装饰与文字的原始关系。
    const body = slide.elements.find(element => itemIds.has(element.id))
    if (body) {
      setTextType(body, 'content')
    }
    slide.elements = slide.elements.filter(element => !['itemTitle', 'itemNumber'].includes(getTextType(element)))
  }
  else if (count === 2) {
    // 双要点保留原稿的对称槽位，不再统一移动或改造成通用卡片。
  }
  return slide
}

const createSingleImageVariant = sourceSlide => {
  const slide = assignVariantIds(structuredClone(sourceSlide), 'image-1')
  const image = sortByPosition(slide.elements.filter(element => element.imageType === 'itemFigure'))[0]
  const body = sortByPosition(slide.elements.filter(element => getTextType(element) === 'item'))[0]
  const subtitle = sortByPosition(slide.elements.filter(element => getTextType(element) === 'itemTitle'))[0]

  slide.elements = slide.elements.filter(element => {
    if (element.imageType === 'itemFigure') return element === image
    const role = getTextType(element)
    if (role === 'item') return element === body
    if (role === 'itemTitle') return element === subtitle
    return true
  })

  if (image) Object.assign(image, { left: 90, top: 165, width: 520, height: 360 })
  if (subtitle) {
    setTextType(subtitle, 'subtitle')
    Object.assign(subtitle, { left: 660, top: 180, width: 500, height: 70 })
  }
  if (body) {
    setTextType(body, 'content')
    Object.assign(body, { left: 660, top: 270, width: 500, height: 240 })
  }
  // 原三图页面右侧的小图标会侵入长标题区域，单图版式中移除这些装饰，保证文字区完整。
  slide.elements = slide.elements.filter(element => !(
    !getTextType(element)
    && element.type === 'shape'
    && element.left > 840
    && element.top > 130
    && element.top < 560
    && element.width < 220
    && element.height < 220
  ))
  return slide
}

const mimeToExtension = mime => {
  if (mime === 'image/jpeg') return '.jpg'
  if (mime === 'image/svg+xml') return '.svg'
  if (mime === 'image/gif') return '.gif'
  return '.png'
}

const externalizeImages = async slides => {
  await mkdir(assetDir, { recursive: true })
  const savedImages = new Map()

  for (const slide of slides) {
    const unsupportedImageIds = new Set()
    for (const element of slide.elements) {
      if (element.type !== 'image' || typeof element.src !== 'string') continue
      const match = element.src.match(/^data:([^;]+);base64,(.+)$/s)
      if (!match) continue

      const [, mime, base64] = match
      const imageBuffer = Buffer.from(base64, 'base64')
      const isPng = imageBuffer.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))
      const isJpeg = imageBuffer[0] === 0xff && imageBuffer[1] === 0xd8
      const isGif = imageBuffer.subarray(0, 3).toString('ascii') === 'GIF'
      const isSvg = imageBuffer.subarray(0, 512).toString('utf8').includes('<svg')

      // pptxtojson 可能把 EMF/WMF 标成 image/png；浏览器无法解码这类数据，直接移除装饰图避免破图。
      if (!isPng && !isJpeg && !isGif && !isSvg) {
        unsupportedImageIds.add(element.id)
        continue
      }

      const digest = createHash('sha1').update(base64).digest('hex').slice(0, 12)
      const extension = mimeToExtension(mime)
      const filename = `template_5_asset_${digest}${extension}`
      const filePath = join(assetDir, filename)

      if (!savedImages.has(filename)) {
        await writeFile(filePath, imageBuffer)
        savedImages.set(filename, filePath)
      }

      element.src = `/api/data/${filename}`
    }
    slide.elements = slide.elements.filter(element => !unsupportedImageIds.has(element.id))
  }

  return [...savedImages.keys()]
}

const main = async () => {
  const source = JSON.parse(await readFile(inputPath, 'utf8'))
  const slides = INCLUDED_SLIDES.map(slideNumber => {
    const slide = structuredClone(source.slides[slideNumber - 1])
    // 临时保留原始页码，便于派生版式精确复用指定构图；写出模板前会删除。
    slide.sourceSlideNumber = slideNumber
    slide.type = PAGE_TYPES.get(slideNumber)

    if (slide.type === 'cover') stripCoverMetadata(slide)
    if (slide.type === 'contents') simplifyContentsSlide(slide)
    if (slide.type === 'transition') {
      for (const element of slide.elements) {
        if (getElementText(element)) setTextType(element, 'title')
      }
    }
    if (slide.type === 'content') {
      simplifyContentHeader(slide)
      tagContentSlots(slide)
      if (slideNumber === 10) rebuildChartSlide(slide)
      // 保留原稿的线条、图标和装饰构图；只做语义标注与必要的图表槽位转换。
      removeOverflowingDecorations(slide)
    }
    if (slide.type === 'end') stripEndMetadata(slide)

    // 所有可替换槽位统一为单文本节点，确保运行时覆盖而不是在旧文案前追加。
    for (const element of slide.elements) collapseSemanticText(element)
    bringSemanticSlotsToFront(slide)

    return slide
  })

  // 补齐原稿缺少的常用数量版式，避免内容较少时残留未替换的样例文字或图片。
  const threeItemSlides = slides.filter(slide => (
    slide.type === 'content'
    && slide.elements.filter(element => getTextType(element) === 'item').length === 3
    && !slide.elements.some(element => element.imageType === 'itemFigure')
  ))
  const fourItemSlides = slides.filter(slide => (
    slide.type === 'content'
    && slide.elements.filter(element => getTextType(element) === 'item').length === 4
    && !slide.elements.some(element => element.imageType === 'itemFigure')
  )).sort((first, second) => first.elements.length - second.elements.length)
  if (threeItemSlides.length && fourItemSlides.length) {
    // 单项使用灯泡构图，双项使用环形构图，避免连续复用同一个问号装饰。
    const singleSource = fourItemSlides.find(slide => slide.sourceSlideNumber === 14) || fourItemSlides[0]
    const doubleSource = fourItemSlides.find(slide => slide.sourceSlideNumber === 24) || fourItemSlides[1] || fourItemSlides[0]
    slides.push(createTextVariant(singleSource, 1))
    slides.push(createTextVariant(doubleSource, 2))
  }

  const imageSlide = slides.find(slide => (
    slide.type === 'content'
    && slide.elements.filter(element => element.imageType === 'itemFigure').length >= 3
  ))
  if (imageSlide) slides.push(createSingleImageVariant(imageSlide))

  // 在所有基础页与派生页生成完成后统一应用商业化设计，保证随机选版时视觉仍然一致。
  for (const slide of slides) applyCommercialDesign(slide)

  // 原始页码只服务于构建阶段，不进入前端模板数据。
  for (const slide of slides) delete slide.sourceSlideNumber

  const assets = await externalizeImages(slides)
  const template = {
    title: '毕业答辩',
    width: source.width,
    height: source.height,
    theme: {
      ...source.theme,
      themeColors: ['#B42318', '#7A1712', '#252525', '#A8786E', '#D0A099', '#8B827B'],
      fontColor: COMMERCIAL_TOKENS.charcoal,
      fontName: '微软雅黑',
      backgroundColor: COMMERCIAL_TOKENS.ivory,
      shadow: { h: 0, v: 3, blur: 8, color: '#2525251F' },
      outline: { width: 1, color: COMMERCIAL_TOKENS.rule, style: 'solid' },
    },
    slides,
  }

  await mkdir(dirname(outputPath), { recursive: true })
  await writeFile(outputPath, `${JSON.stringify(template, null, 2)}\n`, 'utf8')

  console.log(JSON.stringify({
    input: basename(inputPath),
    output: outputPath,
    slides: slides.length,
    assets: assets.length,
    sizeMB: Number(((await readFile(outputPath)).length / 1024 / 1024).toFixed(2)),
  }, null, 2))
}

main().catch(error => {
  console.error(error)
  process.exit(1)
})

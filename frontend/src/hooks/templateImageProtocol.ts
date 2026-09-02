import type { PPTElement, PPTImageElement } from '@/types/slides'


const explicitImageTypes = new Set(['content', 'decoration'])

/** 判断一页是否采用 content/decoration 显式图片协议。 */
export const hasExplicitImageProtocol = (elements: PPTElement[]) => elements.some(element => (
  element.type === 'image'
  && explicitImageTypes.has(String((element as PPTImageElement).imageType || ''))
))

/** 识别可承载正文图片的显式或历史图片槽。 */
export const isContentImageSlot = (element: PPTElement) => (
  element.type === 'image'
  && ['content', 'itemFigure'].includes(String((element as PPTImageElement).imageType || ''))
)

/** 显式协议只替换 content；没有显式协议时保持历史模板兼容行为。 */
export const isReplaceableTemplateImage = (element: PPTElement, elements: PPTElement[]) => {
  if (element.type !== 'image') return false
  const imageType = String((element as PPTImageElement).imageType || '')
  if (hasExplicitImageProtocol(elements)) return imageType === 'content'
  return Boolean(imageType)
}

/** 将 AI 图文项放入内容槽，并用 cover 居中裁剪避免任意宽高比被拉伸。 */
export const fillContentImageSlot = (element: PPTImageElement, src: string): PPTImageElement => ({
  ...element,
  src,
  clip: undefined,
  imageFit: 'cover',
})

/** 把浏览器图片适配语义转换为 PPTXGenJS 可识别的导出 sizing。 */
export const getImageExportSizing = (
  element: PPTImageElement,
  width: number,
  height: number,
) => {
  if (element.clip || !element.imageFit || element.imageFit === 'fill') return undefined
  return { type: element.imageFit, w: width, h: height } as const
}

/** 显式裁剪优先；编辑器、缩略图和放映不得再叠加 object-fit 二次裁剪。 */
export const getImageObjectFit = (element: PPTImageElement) => (
  element.clip ? 'fill' : (element.imageFit || 'fill')
)

/**
 * 计算编辑器“替换图片”的更新属性。
 * 已裁剪图片保持原画框和裁剪形状，只根据新图比例重算居中裁切范围；未裁剪图片保持历史居中缩放行为。
 */
export const getImageReplacementProps = (
  element: PPTImageElement,
  src: string,
  sourceWidth: number,
  sourceHeight: number,
): Partial<PPTImageElement> => {
  if (element.clip) {
    const frameRatio = element.width / element.height
    const sourceRatio = sourceWidth / sourceHeight
    let range: [[number, number], [number, number]]

    if (sourceRatio > frameRatio) {
      const visibleWidth = frameRatio / sourceRatio * 100
      const distance = (100 - visibleWidth) / 2
      range = [[distance, 0], [100 - distance, 100]]
    }
    else {
      const visibleHeight = sourceRatio / frameRatio * 100
      const distance = (100 - visibleHeight) / 2
      range = [[0, distance], [100, 100 - distance]]
    }

    return {
      src,
      left: element.left,
      top: element.top,
      width: element.width,
      height: element.height,
      clip: { ...element.clip, range },
    }
  }

  const height = element.height
  const width = sourceWidth * (height / sourceHeight)
  const centerX = element.left + element.width / 2
  const centerY = element.top + element.height / 2
  return {
    src,
    width,
    height,
    left: centerX - width / 2,
    top: centerY - height / 2,
  }
}

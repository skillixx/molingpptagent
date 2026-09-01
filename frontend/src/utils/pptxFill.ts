/** PPTX 填充值可能是字符串或二维码样式对象；纯色背景只接受非空字符串。 */
export const normalizePptxSolidFill = (value: unknown): string => {
  return typeof value === 'string' && value ? value : '#fff'
}

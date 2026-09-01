import { describe, expect, it } from 'vitest'

import { normalizePptxSolidFill } from '@/utils/pptxFill'


describe('PPTX 纯色背景填充值', () => {
  it('保留合法字符串颜色', () => {
    expect(normalizePptxSolidFill('#123456')).toBe('#123456')
  })

  it.each([null, undefined, '', { type: 'qr', foregroundColor: '#000' }])(
    '对象、空值和空字符串安全回退为白色：%j',
    value => {
      expect(normalizePptxSolidFill(value)).toBe('#fff')
    },
  )
})

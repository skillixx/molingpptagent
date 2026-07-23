import { describe, expect, it } from 'vitest'

import { shouldUseMobileEditor } from '@/views/Editor/editorViewport'


describe('shouldUseMobileEditor', () => {
  it('桌面浏览器缩到390px也必须进入移动布局', () => {
    expect(shouldUseMobileEditor('Mozilla/5.0 Windows', 390)).toBe(true)
    expect(shouldUseMobileEditor('Mozilla/5.0 Windows', 768)).toBe(false)
  })

  it('移动设备UA在宽视口下仍保留触屏布局', () => {
    expect(shouldUseMobileEditor('Mozilla/5.0 iPad', 1024)).toBe(true)
  })
})

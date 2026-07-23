import { createPinia, setActivePinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import { useSlidesStore } from '@/store'
import ExportPPTX from '../ExportPPTX.vue'

describe('ExportPPTX 文件位置', () => {
  it('明确展示文件名和浏览器下载位置', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    useSlidesStore().setTitle('Linux 入门')

    const wrapper = shallowMount(ExportPPTX, {
      global: {
        plugins: [pinia],
        directives: { tooltip: () => undefined },
        stubs: { IconDownload: true },
      },
    })

    const location = wrapper.get('[data-testid="export-file-location"]')
    expect(location.text()).toContain('Linux 入门.pptx')
    expect(location.text()).toContain('浏览器默认下载目录')
    expect(location.text()).toContain('临时作品')
  })
})

import { createPinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Outline from '@/views/Outline/index.vue'
import message from '@/utils/message'


const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/utils/message', () => ({
  default: { error: vi.fn() },
}))

describe('PPTAgent 主流程导航', () => {
  beforeEach(() => vi.clearAllMocks())

  it('生成首页提供可用的作品库入口', async () => {
    const wrapper = shallowMount(Outline, {
      global: { plugins: [createPinia()] },
    })

    await wrapper.get('[data-testid="open-works"]').trigger('click')

    expect(push).toHaveBeenCalledWith({ name: 'Works' })
    wrapper.unmount()
  })

  it('缺少一级标题时阻止创建PPT并给出明确反馈', async () => {
    const wrapper = shallowMount(Outline, {
      global: { plugins: [createPinia()] },
    })
    const state = wrapper.vm as unknown as { step: string; outline: string }
    state.step = 'outline'
    state.outline = '生成说明\n## 第一章\n### 目标\n- 行动项'
    await nextTick()

    await wrapper.get('.act-btn.primary').trigger('click')

    expect(push).not.toHaveBeenCalled()
    expect(message.error).toHaveBeenCalledWith('大纲需包含一级标题和章节内容，请完善后再创建PPT')
    wrapper.unmount()
  })
})

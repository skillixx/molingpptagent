import { createPinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Outline from '@/views/Outline/index.vue'


const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

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
})

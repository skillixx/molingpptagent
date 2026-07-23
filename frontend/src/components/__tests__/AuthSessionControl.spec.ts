import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AuthSessionControl from '@/components/AuthSessionControl.vue'


const replace = vi.fn()
const authStore = {
  isAuthenticated: true,
  user: { userId: 9, appId: 15, productId: 73 },
  logout: vi.fn(),
}

vi.mock('vue-router', () => ({
  useRouter: () => ({ replace }),
}))

vi.mock('@/store/auth', () => ({
  useAuthStore: () => authStore,
}))

beforeEach(() => {
  authStore.isAuthenticated = true
  authStore.logout.mockReset()
  replace.mockReset()
})

describe('AuthSessionControl', () => {
  it('退出成功后进入已退出提示页', async () => {
    authStore.logout.mockResolvedValue(undefined)
    const wrapper = mount(AuthSessionControl)

    await wrapper.get('button').trigger('click')

    expect(authStore.logout).toHaveBeenCalledOnce()
    expect(replace).toHaveBeenCalledWith({ name: 'AuthFailure', query: { reason: 'logged_out' } })
  })

  it('退出失败时显示明确反馈并允许再次操作', async () => {
    authStore.logout.mockRejectedValue(new Error('sensitive detail'))
    const wrapper = mount(AuthSessionControl)

    await wrapper.get('button').trigger('click')

    expect(wrapper.get('[role="status"]').text()).toBe('退出失败，请稍后重试。')
    expect(wrapper.get('button').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).not.toContain('sensitive detail')
  })
})

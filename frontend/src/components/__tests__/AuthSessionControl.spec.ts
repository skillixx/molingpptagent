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
  it('以紧凑且可访问的账号操作区展示退出按钮', () => {
    const wrapper = mount(AuthSessionControl)

    expect(wrapper.get('.identity-label').text()).toBe('墨灵用户')
    expect(wrapper.get('.identity-value').text()).toBe('9')
    expect(wrapper.get('.logout-button').attributes('aria-label')).toBe('退出当前账号')
    expect(wrapper.get('.logout-button-icon').attributes('aria-hidden')).toBe('true')
  })

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

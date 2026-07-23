import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AuthFailure from '@/views/AuthFailure/index.vue'


const replace = vi.fn()
const authStore = {
  isAuthenticated: false,
  failureReason: 'expired',
  initialize: vi.fn(),
}
const route = {
  query: {
    reason: 'expired',
    redirect: '/works?page=2',
  },
}

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ replace }),
}))

vi.mock('@/store/auth', () => ({
  useAuthStore: () => authStore,
}))

vi.mock('@/services/authConfig', () => ({
  authFrontendConfig: {
    ssoEnabled: true,
    molingPortalUrl: '',
  },
}))

beforeEach(() => {
  authStore.isAuthenticated = false
  authStore.failureReason = 'expired'
  authStore.initialize.mockReset()
  replace.mockReset()
  route.query.reason = 'expired'
  route.query.redirect = '/works?page=2'
})

describe('AuthFailure', () => {
  it('重新检查成功后回到原站内路径', async () => {
    authStore.initialize.mockImplementation(async () => {
      authStore.isAuthenticated = true
    })
    const wrapper = mount(AuthFailure)

    await wrapper.get('.primary-action').trigger('click')

    expect(authStore.initialize).toHaveBeenCalledWith(true)
    expect(replace).toHaveBeenCalledWith('/works?page=2')
  })

  it('拒绝协议相对外部跳转并回退到 PPTAgent 生成入口', async () => {
    route.query.redirect = '//evil.example/steal'
    authStore.initialize.mockImplementation(async () => {
      authStore.isAuthenticated = true
    })
    const wrapper = mount(AuthFailure)

    await wrapper.get('.primary-action').trigger('click')

    expect(replace).toHaveBeenCalledWith('/')
  })

  it('未配置墨灵地址时返回按钮展示明确反馈而不是无响应', async () => {
    const wrapper = mount(AuthFailure)

    await wrapper.get('.secondary-action').trigger('click')

    expect(wrapper.get('[role="status"]').text()).toContain('未配置墨灵返回地址')
  })
})

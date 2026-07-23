import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthApiError, authApi } from '@/services/auth'
import { AUTH_SYNC_KEY, useAuthStore } from '@/store/auth'


vi.mock('@/services/auth', async importOriginal => {
  const original = await importOriginal<typeof import('@/services/auth')>()
  return {
    ...original,
    authApi: {
      getCurrentUser: vi.fn(),
      logout: vi.fn(),
    },
  }
})

const mockedApi = vi.mocked(authApi)

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
})

describe('useAuthStore', () => {
  it('首次加载与强制刷新均以服务端Session为准', async () => {
    mockedApi.getCurrentUser.mockResolvedValue({ userId: 9, appId: 15, productId: 73 })
    const store = useAuthStore()

    await store.initialize()
    await store.initialize()
    await store.initialize(true)

    expect(mockedApi.getCurrentUser).toHaveBeenCalledTimes(2)
    expect(store.status).toBe('authenticated')
    expect(store.user?.userId).toBe(9)
  })

  it('401后进入匿名过期态而不是平台故障态', async () => {
    mockedApi.getCurrentUser.mockRejectedValue(new AuthApiError('expired', 401))
    const store = useAuthStore()

    await store.initialize()

    expect(store.status).toBe('anonymous')
    expect(store.failureReason).toBe('expired')
  })

  it('退出后清空身份并广播给其他标签页', async () => {
    mockedApi.logout.mockResolvedValue(undefined)
    const store = useAuthStore()
    store.markAuthenticated({ userId: 9, appId: 15, productId: 73 })

    await store.logout()

    expect(store.status).toBe('anonymous')
    expect(store.user).toBeNull()
    expect(localStorage.getItem(AUTH_SYNC_KEY)).toContain('logout:')
  })

  it('退出失败时保留当前身份供界面展示反馈和重试', async () => {
    mockedApi.logout.mockRejectedValue(new AuthApiError('platform', 503))
    const store = useAuthStore()
    store.markAuthenticated({ userId: 9, appId: 15, productId: 73 })

    await expect(store.logout()).rejects.toBeInstanceOf(AuthApiError)

    expect(store.status).toBe('error')
    expect(store.user?.userId).toBe(9)
    expect(store.failureReason).toBe('platform')
  })

  it('收到其他标签退出事件后立即使当前标签失效', () => {
    const store = useAuthStore()
    store.markAuthenticated({ userId: 9, appId: 15, productId: 73 })
    const onInvalidated = vi.fn()
    const cleanup = store.startCrossTabSync(onInvalidated)

    window.dispatchEvent(new StorageEvent('storage', {
      key: AUTH_SYNC_KEY,
      newValue: 'logout:other-tab',
    }))

    expect(store.status).toBe('anonymous')
    expect(store.failureReason).toBe('expired')
    expect(onInvalidated).toHaveBeenCalledOnce()
    cleanup()
  })

  it('退出或跨标签失效后忽略更晚返回的旧me成功响应', async () => {
    let resolveRequest: ((user: { userId: number; appId: number; productId: number }) => void) | undefined
    mockedApi.getCurrentUser.mockReturnValue(new Promise(resolve => {
      resolveRequest = resolve
    }))
    const store = useAuthStore()

    const pending = store.initialize(true)
    store.markAnonymous('expired')
    resolveRequest?.({ userId: 9, appId: 15, productId: 73 })
    await pending

    expect(store.status).toBe('anonymous')
    expect(store.user).toBeNull()
  })
})

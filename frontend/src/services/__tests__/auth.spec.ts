import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuthApiError, authApi } from '@/services/auth'


afterEach(() => {
  vi.unstubAllGlobals()
})

describe('authApi', () => {
  it('从服务端Cookie会话读取当前用户且禁止缓存', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      user_id: 9,
      app_id: 15,
      product_id: 73,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(authApi.getCurrentUser()).resolves.toEqual({ userId: 9, appId: 15, productId: 73 })
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/me', expect.objectContaining({
      credentials: 'include',
      cache: 'no-store',
    }))
  })

  it('将401稳定分类为会话过期', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })))

    await expect(authApi.getCurrentUser()).rejects.toEqual(
      expect.objectContaining<AuthApiError>({ reason: 'expired', status: 401 }),
    )
  })

  it('将网络失败分类为平台不可用且不暴露原始异常', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('sensitive network detail')))

    await expect(authApi.getCurrentUser()).rejects.toMatchObject({ reason: 'platform', status: 0 })
  })

  it('退出使用同源POST并携带Cookie', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(authApi.logout()).resolves.toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/logout', expect.objectContaining({
      method: 'POST',
      credentials: 'include',
      cache: 'no-store',
    }))
  })
})

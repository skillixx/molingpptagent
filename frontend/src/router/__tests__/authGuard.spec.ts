import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/store/auth'
import { resolveAuthNavigation } from '@/router/authGuard'


beforeEach(() => {
  setActivePinia(createPinia())
})

describe('resolveAuthNavigation', () => {
  it('SSO关闭时保持旧功能可用且不查询Session', async () => {
    const store = useAuthStore()
    const initialize = vi.spyOn(store, 'initialize')

    await expect(resolveAuthNavigation(store, false, true, '/editor')).resolves.toBe(true)
    expect(initialize).not.toHaveBeenCalled()
  })

  it('匿名用户被送到认证失败页并保留安全的站内返回路径', async () => {
    const store = useAuthStore()
    vi.spyOn(store, 'initialize').mockImplementation(async () => {
      store.markAnonymous('expired')
    })

    await expect(resolveAuthNavigation(store, true, true, '/works?page=2')).resolves.toEqual({
      name: 'AuthFailure',
      query: { reason: 'expired', redirect: '/works?page=2' },
    })
  })

  it('已登录用户可以进入受保护页面', async () => {
    const store = useAuthStore()
    vi.spyOn(store, 'initialize').mockImplementation(async () => {
      store.markAuthenticated({ userId: 9, appId: 15, productId: 73 })
    })

    await expect(resolveAuthNavigation(store, true, true, '/works')).resolves.toBe(true)
    expect(store.initialize).toHaveBeenCalledWith(true)
  })
})

describe('works route contract', () => {
  it('作品入口不再复用大纲页占位组件', async () => {
    const { routes } = await import('@/router')
    const route = routes.find(item => item.name === 'Works')
    expect(route?.path).toBe('/works')
    expect(String(route?.component)).toContain('Works')
  })
})

describe('history editor route contract', () => {
  it('新路由携带作品ID且旧路由仍可兼容', async () => {
    const { routes, resolveLegacyEditorNavigation } = await import('@/router')
    expect(routes.find(item => item.name === 'PresentationEditor')?.path).toBe('/editor/:presentationId')
    expect(routes.find(item => item.name === 'Editor')?.path).toBe('/editor')
    expect(resolveLegacyEditorNavigation({ presentationId: 'presentation-1' })).toEqual({
      name: 'PresentationEditor',
      params: { presentationId: 'presentation-1' },
    })
    expect(resolveLegacyEditorNavigation({ presentationId: ['bad'] })).toBe(true)
  })
})

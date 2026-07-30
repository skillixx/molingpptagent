import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PresentationApiError, presentationApi } from '@/services/presentations'
import type * as PresentationServiceModule from '@/services/presentations'
import PresentationLoader from '@/views/Editor/PresentationLoader.vue'


vi.mock('@/services/presentations', async importOriginal => {
  const original = await importOriginal<typeof PresentationServiceModule>()
  return { ...original, presentationApi: { ...original.presentationApi, get: vi.fn() } }
})
const api = vi.mocked(presentationApi)
const detail = {
  id: 'presentation-1', title: '恢复作品', status: 'ready' as const, currentVersion: 3, slideCount: 1,
  templateId: null, thumbnailFileId: null,
  createdAt: '2026-07-23T01:00:00Z', updatedAt: '2026-07-23T02:00:00Z',
  document: { schemaVersion: 1 as const, slides: [{ id: 'slide-1', elements: [] }], theme: {}, viewportSize: 1000, viewportRatio: 0.5625 },
}

function testRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/works', name: 'Works', component: { template: '<div />' } },
      { path: '/editor', name: 'Editor', component: { template: '<div />' } },
      { path: '/editor/:presentationId', name: 'PresentationEditor', component: { template: '<div />' } },
    ],
  })
}

beforeEach(() => vi.clearAllMocks())
afterEach(() => vi.useRealTimers())

describe('PresentationLoader', () => {
  it('直接URL加载成功后才挂载编辑器', async () => {
    let resolveDetail: ((value: typeof detail) => void) | undefined
    api.get.mockReturnValue(new Promise(resolve => {
      resolveDetail = resolve
    }))
    const router = testRouter()
    await router.push('/editor/presentation-1')
    await router.isReady()
    const wrapper = mount(PresentationLoader, {
      slots: { default: '<div data-testid="editor-slot">编辑器</div>' },
      global: { plugins: [createPinia(), router] },
    })

    expect(wrapper.get('[data-testid="history-loading"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="editor-slot"]').exists()).toBe(false)
    resolveDetail?.(detail)
    await flushPromises()
    expect(wrapper.get('[data-testid="editor-slot"]').text()).toBe('编辑器')
  })

  it('404提示不泄露归属并可返回作品库', async () => {
    api.get.mockRejectedValue(new PresentationApiError(404, 'PRESENTATION_NOT_FOUND'))
    const router = testRouter()
    await router.push('/editor/missing')
    await router.isReady()
    const wrapper = mount(PresentationLoader, { global: { plugins: [createPinia(), router] } })
    await flushPromises()

    expect(wrapper.get('[data-testid="history-not-found"]').text()).toContain('可能已删除、不存在，或不属于当前账号')
    await wrapper.get('[data-testid="back-to-works"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('Works')
  })

  it('旧/editor入口不请求服务端并继续显示内存稿', async () => {
    const router = testRouter()
    await router.push('/editor')
    await router.isReady()
    const wrapper = mount(PresentationLoader, {
      slots: { default: '<div data-testid="editor-slot">旧编辑器</div>' },
      global: { plugins: [createPinia(), router] },
    })
    await flushPromises()

    expect(wrapper.get('[data-testid="editor-slot"]').text()).toBe('旧编辑器')
    expect(api.get).not.toHaveBeenCalled()
  })

  it('暂时失败后重试按钮可恢复编辑器', async () => {
    api.get
      .mockRejectedValueOnce(new PresentationApiError(0))
      .mockResolvedValueOnce(detail)
    const router = testRouter()
    await router.push('/editor/presentation-1')
    await router.isReady()
    const wrapper = mount(PresentationLoader, {
      slots: { default: '<div data-testid="editor-slot">已恢复</div>' },
      global: { plugins: [createPinia(), router] },
    })
    await flushPromises()

    expect(wrapper.get('[data-testid="history-error"]').exists()).toBe(true)
    await wrapper.get('[data-testid="retry-history"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="editor-slot"]').text()).toBe('已恢复')
    expect(api.get).toHaveBeenCalledTimes(2)
  })

  it('生成中作品自动轮询并在就绪后挂载编辑器', async () => {
    vi.useFakeTimers()
    api.get
      .mockResolvedValueOnce({ ...detail, status: 'generating' })
      .mockResolvedValueOnce(detail)
    const router = testRouter()
    await router.push('/editor/presentation-1')
    await router.isReady()
    const wrapper = mount(PresentationLoader, {
      slots: { default: '<div data-testid="editor-slot">生成完成</div>' },
      global: { plugins: [createPinia(), router] },
    })
    await flushPromises()

    expect(wrapper.get('[data-testid="history-unavailable"]').text()).toContain('作品正在生成')
    await vi.advanceTimersByTimeAsync(4000)
    await flushPromises()
    expect(wrapper.get('[data-testid="editor-slot"]').text()).toBe('生成完成')
    expect(api.get).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })
})

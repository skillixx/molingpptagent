import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { presentationApi } from '@/services/presentations'
import Works from '@/views/Works/index.vue'


const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/services/presentations', async importOriginal => {
  const original = await importOriginal<typeof import('@/services/presentations')>()
  return {
    ...original,
    presentationApi: {
      list: vi.fn(), create: vi.fn(), duplicate: vi.fn(), remove: vi.fn(),
    },
  }
})

const api = vi.mocked(presentationApi)
const item = {
  id: 'p-1', title: '经营复盘', status: 'ready' as const, currentVersion: 1, slideCount: 12,
  templateId: null, thumbnailFileId: null,
  createdAt: '2026-07-23T01:00:00Z', updatedAt: '2026-07-23T02:00:00Z',
}

function mountWorks() {
  return mount(Works, {
    global: {
      plugins: [createPinia()],
      stubs: { teleport: true },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  api.list.mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0, hasMore: false })
})

describe('Works', () => {
  it('空态、新建按钮和错误重试都不会成为无响应控件', async () => {
    const wrapper = mountWorks()
    await flushPromises()
    expect(wrapper.get('[data-testid="works-empty"]').text()).toContain('还没有演示文稿')

    await wrapper.get('[data-testid="new-presentation"]').trigger('click')
    expect(push).toHaveBeenLastCalledWith({ name: 'Outline' })

    await wrapper.get('[data-testid="new-presentation-empty"]').trigger('click')
    expect(push).toHaveBeenLastCalledWith({ name: 'Outline' })
    expect(api.create).not.toHaveBeenCalled()

    api.list.mockRejectedValueOnce(new Error('network'))
    await wrapper.get('[data-testid="refresh-works"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="works-error"]').text()).toContain('作品加载失败')
    await wrapper.get('[data-testid="retry-load"]').trigger('click')
    expect(api.list).toHaveBeenCalledTimes(3)
  })

  it('搜索会防抖加载，手机筛选按钮可打开和关闭抽屉', async () => {
    vi.useFakeTimers()
    const wrapper = mountWorks()
    await flushPromises()

    await wrapper.get('[data-testid="works-search"]').setValue('季度')
    await vi.advanceTimersByTimeAsync(320)
    expect(api.list).toHaveBeenLastCalledWith(expect.objectContaining({ search: '季度' }))

    await wrapper.get('[data-testid="mobile-filter"]').trigger('click')
    expect(wrapper.get('[data-testid="filter-drawer"]').attributes('aria-hidden')).toBe('false')
    await wrapper.get('[data-testid="close-filter"]').trigger('click')
    expect(wrapper.get('[data-testid="filter-drawer"]').attributes('aria-hidden')).toBe('true')
    vi.useRealTimers()
  })

  it('卡片可打开、复制并经过确认后删除', async () => {
    api.list.mockResolvedValue({ items: [item], page: 1, pageSize: 20, total: 1, hasMore: false })
    api.duplicate.mockResolvedValue({ ...item, id: 'p-2', title: '经营复盘 副本' })
    api.remove.mockResolvedValue(undefined)
    const wrapper = mountWorks()
    await flushPromises()

    await wrapper.get('[data-testid="open-p-1"]').trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'PresentationEditor', params: { presentationId: 'p-1' } })
    await wrapper.get('[data-testid="duplicate-p-1"]').trigger('click')
    await flushPromises()
    expect(api.duplicate).toHaveBeenCalledWith('p-1')

    await wrapper.get('[data-testid="delete-p-1"]').trigger('click')
    expect(wrapper.get('[role="alertdialog"]').text()).toContain('删除“经营复盘”')
    await wrapper.get('[data-testid="confirm-delete"]').trigger('click')
    await flushPromises()
    expect(api.remove).toHaveBeenCalledWith('p-1')
  })
})

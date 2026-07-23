import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { presentationApi } from '@/services/presentations'
import { usePresentationsStore } from '@/store/presentations'


vi.mock('@/services/presentations', async importOriginal => {
  const original = await importOriginal<typeof import('@/services/presentations')>()
  return {
    ...original,
    presentationApi: {
      list: vi.fn(),
      create: vi.fn(),
      duplicate: vi.fn(),
      remove: vi.fn(),
    },
  }
})

const api = vi.mocked(presentationApi)
const baseItem = {
  id: 'p-1', title: '作品一', status: 'ready' as const, currentVersion: 1, slideCount: 8,
  templateId: null, thumbnailFileId: null,
  createdAt: '2026-07-23T01:00:00Z', updatedAt: '2026-07-23T02:00:00Z',
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('usePresentationsStore', () => {
  it('加载成功、筛选和失败重试均有明确状态', async () => {
    api.list.mockResolvedValue({ items: [baseItem], page: 1, pageSize: 20, total: 1, hasMore: false })
    const store = usePresentationsStore()
    store.search = '作品'
    store.statusFilter = 'ready'

    await store.load()
    expect(store.status).toBe('ready')
    expect(store.items).toHaveLength(1)
    expect(api.list).toHaveBeenCalledWith(expect.objectContaining({ search: '作品', status: 'ready' }))

    api.list.mockRejectedValue(new Error('secret'))
    await store.load()
    expect(store.status).toBe('error')
    expect(store.errorMessage).toBe('作品加载失败，请稍后重试。')
    expect(store.errorMessage).not.toContain('secret')
  })

  it('较晚发起的搜索结果不会被旧请求覆盖', async () => {
    let resolveOld: ((value: any) => void) | undefined
    api.list
      .mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce({ items: [{ ...baseItem, id: 'new', title: '新结果' }], page: 1, pageSize: 20, total: 1, hasMore: false })
    const store = usePresentationsStore()

    const oldRequest = store.load()
    store.search = '新'
    await store.load()
    resolveOld?.({ items: [{ ...baseItem, id: 'old', title: '旧结果' }], page: 1, pageSize: 20, total: 1, hasMore: false })
    await oldRequest

    expect(store.items[0].id).toBe('new')
  })

  it('创建、复制和删除立即更新可见列表', async () => {
    const store = usePresentationsStore()
    api.create.mockResolvedValue({ presentation: baseItem, taskId: 'task-1', reused: false })
    api.duplicate.mockResolvedValue({ ...baseItem, id: 'p-2', title: '作品一 副本' })
    api.remove.mockResolvedValue(undefined)

    await store.create({ title: '作品一', content: '生成内容' })
    await store.duplicate('p-1')
    await store.remove('p-1')

    expect(store.items.map(item => item.id)).toEqual(['p-2'])
    expect(store.feedback).toBe('作品已移入回收状态。')
  })

  it('当新作品不匹配当前筛选时不虚增可见总数', async () => {
    api.list.mockResolvedValue({ items: [], page: 1, pageSize: 20, total: 0, hasMore: false })
    api.create.mockResolvedValue({ presentation: baseItem, taskId: 'task-1', reused: false })
    api.duplicate.mockResolvedValue({ ...baseItem, id: 'p-2', title: '作品一 副本' })
    const store = usePresentationsStore()
    store.statusFilter = 'failed'
    await store.load()

    await store.create({ title: '作品一', content: '生成内容' })
    await store.duplicate('p-1')

    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
  })
})

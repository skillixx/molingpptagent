import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { presentationApi } from '@/services/presentations'
import type {
  CreatePresentationInput,
  PresentationSort,
  PresentationStatus,
  PresentationSummary,
} from '@/services/presentations'


export type WorksLoadStatus = 'idle' | 'loading' | 'ready' | 'error'
export type WorksStatusFilter = 'all' | PresentationStatus

function idempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return `works-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export const usePresentationsStore = defineStore('presentations', () => {
  const items = ref<PresentationSummary[]>([])
  const status = ref<WorksLoadStatus>('idle')
  const errorMessage = ref('')
  const feedback = ref('')
  const page = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const hasMore = ref(false)
  const search = ref('')
  const statusFilter = ref<WorksStatusFilter>('all')
  const sort = ref<PresentationSort>('updated_desc')
  let loadEpoch = 0

  const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  async function load(): Promise<void> {
    const epoch = ++loadEpoch
    status.value = 'loading'
    errorMessage.value = ''
    try {
      const result = await presentationApi.list({
        page: page.value,
        pageSize: pageSize.value,
        search: search.value.trim() || undefined,
        status: statusFilter.value === 'all' ? undefined : statusFilter.value,
        sort: sort.value,
      })
      if (epoch !== loadEpoch) return
      items.value = result.items
      total.value = result.total
      hasMore.value = result.hasMore
      status.value = 'ready'
    }
    catch {
      if (epoch !== loadEpoch) return
      items.value = []
      status.value = 'error'
      errorMessage.value = '作品加载失败，请稍后重试。'
    }
  }

  async function create(input: CreatePresentationInput): Promise<PresentationSummary> {
    const result = await presentationApi.create(input, idempotencyKey())
    const visibleInCurrentView = matchesCurrentView(result.presentation)
    if (visibleInCurrentView) {
      items.value = [result.presentation, ...items.value.filter(item => item.id !== result.presentation.id)]
    }
    // total 表示当前筛选条件下的结果数，不可把不可见作品或幂等重用请求计入。
    if (visibleInCurrentView && !result.reused) total.value += 1
    status.value = 'ready'
    feedback.value = result.reused ? '已恢复之前的创建请求。' : '作品已创建，生成任务正在排队。'
    return result.presentation
  }

  async function duplicate(presentationId: string): Promise<PresentationSummary> {
    const copied = await presentationApi.duplicate(presentationId)
    const visibleInCurrentView = matchesCurrentView(copied)
    if (visibleInCurrentView) {
      items.value = [copied, ...items.value]
      total.value += 1
    }
    feedback.value = '副本已创建。'
    return copied
  }

  async function remove(presentationId: string): Promise<void> {
    await presentationApi.remove(presentationId)
    const existed = items.value.some(item => item.id === presentationId)
    items.value = items.value.filter(item => item.id !== presentationId)
    if (existed) total.value = Math.max(0, total.value - 1)
    feedback.value = '作品已移入回收状态。'
    if (items.value.length === 0 && page.value > 1) {
      page.value -= 1
      await load()
    }
  }

  async function applyFilters(): Promise<void> {
    page.value = 1
    await load()
  }

  async function goToPage(nextPage: number): Promise<void> {
    page.value = Math.min(Math.max(1, nextPage), pageCount.value)
    await load()
  }

  function matchesCurrentView(item: PresentationSummary): boolean {
    const statusMatches = statusFilter.value === 'all' || statusFilter.value === item.status
    const searchMatches = !search.value.trim() || item.title.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase())
    return statusMatches && searchMatches
  }

  return {
    items,
    status,
    errorMessage,
    feedback,
    page,
    pageSize,
    total,
    hasMore,
    pageCount,
    search,
    statusFilter,
    sort,
    load,
    create,
    duplicate,
    remove,
    applyFilters,
    goToPage,
  }
})

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PresentationApiError, presentationApi } from '@/services/presentations'
import { usePresentationEditorStore } from '@/store/presentationEditor'
import { useSlidesStore } from '@/store/slides'


vi.mock('@/services/presentations', async importOriginal => {
  const original = await importOriginal<typeof import('@/services/presentations')>()
  return { ...original, presentationApi: { ...original.presentationApi, get: vi.fn() } }
})

const api = vi.mocked(presentationApi)
const detail = {
  id: 'presentation-1', title: '服务端作品', status: 'ready' as const, currentVersion: 7, slideCount: 1,
  templateId: null, thumbnailFileId: null,
  createdAt: '2026-07-23T01:00:00Z', updatedAt: '2026-07-23T02:00:00Z',
  document: {
    schemaVersion: 1 as const,
    slides: [{ id: 'server-slide', elements: [] }],
    theme: { themeColors: ['#123456'] },
    viewportSize: 1200,
    viewportRatio: 0.75,
  },
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('usePresentationEditorStore', () => {
  it('按ID一次性恢复作品与版本上下文', async () => {
    api.get.mockResolvedValue(detail)
    const editor = usePresentationEditorStore()
    const slides = useSlidesStore()

    await editor.load('presentation-1')

    expect(editor.loadStatus).toBe('ready')
    expect(slides.$state).toMatchObject({
      presentationId: 'presentation-1',
      presentationVersion: 7,
      title: '服务端作品',
      slideIndex: 0,
      viewportSize: 1200,
      viewportRatio: 0.75,
      slides: [{ id: 'server-slide', elements: [] }],
    })
  })

  it('404和损坏响应不覆盖已有编辑内容', async () => {
    const slides = useSlidesStore()
    slides.setTitle('本地未保存标题')
    const editor = usePresentationEditorStore()
    api.get.mockRejectedValueOnce(new PresentationApiError(404, 'PRESENTATION_NOT_FOUND'))

    await editor.load('missing')
    expect(editor.loadStatus).toBe('not_found')
    expect(slides.title).toBe('本地未保存标题')

    api.get.mockRejectedValueOnce(new PresentationApiError(502))
    await editor.load('broken')
    expect(editor.loadStatus).toBe('error')
    expect(slides.title).toBe('本地未保存标题')
  })

  it('路由快速切换时旧请求不得覆盖新作品', async () => {
    let resolveOld: ((value: typeof detail) => void) | undefined
    api.get
      .mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce({ ...detail, id: 'presentation-2', title: '新作品' })
    const editor = usePresentationEditorStore()

    const oldLoad = editor.load('presentation-1')
    await editor.load('presentation-2')
    resolveOld?.(detail)
    await oldLoad

    expect(useSlidesStore().presentationId).toBe('presentation-2')
    expect(useSlidesStore().title).toBe('新作品')
  })

  it('生成中和待结算的直达URL不开放编辑', async () => {
    api.get.mockResolvedValueOnce({ ...detail, status: 'generating' })
    const editor = usePresentationEditorStore()
    await editor.load('presentation-1')
    expect(editor.loadStatus).toBe('unavailable')
    expect(editor.unavailableStatus).toBe('generating')
    expect(useSlidesStore().presentationId).toBeNull()
  })
})

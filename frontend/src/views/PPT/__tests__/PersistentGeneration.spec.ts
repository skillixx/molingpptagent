import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import PPT from '@/views/PPT/index.vue'
import api from '@/services'
import { presentationApi } from '@/services/presentations'
import type * as PresentationServiceModule from '@/services/presentations'


vi.mock('@/services/authConfig', () => ({ authFrontendConfig: { ssoEnabled: true } }))
vi.mock('@/services', () => ({
  default: {
    getTemplates: vi.fn(),
    AIPPT_Content: vi.fn(),
    getMockData: vi.fn(),
    getFileData: vi.fn(),
  },
}))
vi.mock('@/services/presentations', async importOriginal => {
  const original = await importOriginal<typeof PresentationServiceModule>()
  return { ...original, presentationApi: { ...original.presentationApi, create: vi.fn() } }
})
vi.mock('@/hooks/useAIPPT', () => ({
  default: () => ({ AIPPTGenerator: vi.fn(), presetImgPool: vi.fn() }),
}))
vi.mock('@/hooks/useAddSlidesOrElements', () => ({
  default: () => ({ addSlidesFromDataToEnd: vi.fn() }),
}))
vi.mock('@/hooks/useSlideHandler', () => ({
  default: () => ({ isEmptySlide: ref(true) }),
}))
vi.mock('@/utils/message', () => ({
  default: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

const mockedApi = vi.mocked(api)
const mockedPresentationApi = vi.mocked(presentationApi)

function testRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ppt', name: 'PPT', component: PPT },
      { path: '/editor/:presentationId', name: 'PresentationEditor', component: { template: '<div />' } },
    ],
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  mockedApi.getTemplates.mockResolvedValue({
    data: [{ id: 'template_1', name: '通用模板', cover: '/cover.jpg' }],
  })
  mockedPresentationApi.create.mockResolvedValue({
    presentation: {
      id: 'presentation-uat-1',
      title: '积分闭环',
      status: 'billing_pending',
      currentVersion: 1,
      slideCount: 0,
      templateId: 'template_1',
      thumbnailFileId: null,
      createdAt: '2026-07-30T08:00:00Z',
      updatedAt: '2026-07-30T08:00:00Z',
    },
    taskId: 'task-uat-1',
    reused: false,
  })
})

describe('PPT persistent generation', () => {
  it('SSO 模式创建持久任务并进入作品状态页', async () => {
    const router = testRouter()
    await router.push({
      name: 'PPT',
      query: {
        outline: '# 积分闭环\n## 预占与结算',
        language: 'chinese',
        model: 'deepseek-chat',
      },
    })
    await router.isReady()
    const wrapper = mount(PPT, { global: { plugins: [createPinia(), router] } })
    await flushPromises()

    await wrapper.get('.btn-primary').trigger('click')
    await flushPromises()

    expect(mockedPresentationApi.create).toHaveBeenCalledTimes(1)
    expect(mockedPresentationApi.create.mock.calls[0][0]).toMatchObject({
      title: '积分闭环',
      content: '# 积分闭环\n## 预占与结算',
      templateId: 'template_1',
      generateFromUploadedFile: false,
      generateFromWebSearch: false,
    })
    expect(mockedApi.AIPPT_Content).not.toHaveBeenCalled()
    expect(router.currentRoute.value).toMatchObject({
      name: 'PresentationEditor',
      params: { presentationId: 'presentation-uat-1' },
    })
  })

  it('网络重试复用同一幂等键且不重复调用旧流接口', async () => {
    mockedPresentationApi.create
      .mockRejectedValueOnce(new TypeError('network'))
      .mockResolvedValueOnce({
        presentation: {
          id: 'presentation-uat-1', title: '积分闭环', status: 'generating',
          currentVersion: 1, slideCount: 0, templateId: 'template_1', thumbnailFileId: null,
          createdAt: '2026-07-30T08:00:00Z', updatedAt: '2026-07-30T08:00:00Z',
        },
        taskId: 'task-uat-1',
        reused: true,
      })
    const router = testRouter()
    await router.push({
      name: 'PPT',
      query: { outline: '# 积分闭环', language: 'chinese', model: 'deepseek-chat' },
    })
    await router.isReady()
    const wrapper = mount(PPT, { global: { plugins: [createPinia(), router] } })
    await flushPromises()

    await wrapper.get('.btn-primary').trigger('click')
    await flushPromises()
    await wrapper.get('.btn-primary').trigger('click')
    await flushPromises()

    expect(mockedPresentationApi.create).toHaveBeenCalledTimes(2)
    expect(mockedPresentationApi.create.mock.calls[0][1]).toBe(
      mockedPresentationApi.create.mock.calls[1][1],
    )
    expect(mockedApi.AIPPT_Content).not.toHaveBeenCalled()
  })
})

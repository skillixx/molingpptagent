import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import PPT from '@/views/PPT/index.vue'
import api from '@/services'
import { PresentationApiError, presentationApi } from '@/services/presentations'
import type * as PresentationServiceModule from '@/services/presentations'
import message from '@/utils/message'


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
const mockedMessage = vi.mocked(message)

function testRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ppt', name: 'PPT', component: PPT },
      { path: '/editor/:presentationId', name: 'PresentationEditor', component: { template: '<div />' } },
      { path: '/works', name: 'Works', component: { template: '<div />' } },
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

afterEach(() => {
  vi.useRealTimers()
})

describe('PPT persistent generation', () => {
  it('等待任务创建时持续展示阶段、耗时和长等待说明', async () => {
    let resolveCreate: ((value: Awaited<ReturnType<typeof presentationApi.create>>) => void) | undefined
    mockedPresentationApi.create.mockImplementationOnce(() => new Promise(resolve => {
      resolveCreate = resolve
    }))
    const router = testRouter()
    await router.push({
      name: 'PPT',
      query: { outline: '# 长任务反馈', language: 'chinese', model: 'deepseek-chat' },
    })
    await router.isReady()
    const wrapper = mount(PPT, { global: { plugins: [createPinia(), router] } })
    await flushPromises()
    vi.useFakeTimers()

    await wrapper.get('.btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="generation-status"]').text()).toContain('正在创建云端任务')
    expect(wrapper.get('[data-testid="generation-elapsed"]').text()).toContain('0 秒')
    expect(wrapper.get('[data-testid="generation-steps"]').text()).toContain('模板已确认')

    await vi.advanceTimersByTimeAsync(12_000)

    expect(wrapper.get('[data-testid="generation-elapsed"]').text()).toContain('12 秒')
    expect(wrapper.get('[data-testid="generation-hint"]').text()).toContain('请求已经发出')

    await vi.advanceTimersByTimeAsync(18_000)

    expect(wrapper.get('[data-testid="generation-hint"]').text()).toContain('尚未收到服务端确认')

    resolveCreate?.({
      presentation: {
        id: 'presentation-delayed', title: '长任务反馈', status: 'generating',
        currentVersion: 1, slideCount: 0, templateId: 'template_1', thumbnailFileId: null,
        createdAt: '2026-08-18T00:00:00Z', updatedAt: '2026-08-18T00:00:00Z',
      },
      taskId: 'task-delayed',
      reused: false,
    })
    await flushPromises()
    vi.useRealTimers()
  })

  it('允许用户选择任务创建后前往作品库且不会突然进入编辑器', async () => {
    let resolveCreate: ((value: Awaited<ReturnType<typeof presentationApi.create>>) => void) | undefined
    mockedPresentationApi.create.mockImplementationOnce(() => new Promise(resolve => {
      resolveCreate = resolve
    }))
    const router = testRouter()
    await router.push({
      name: 'PPT',
      query: { outline: '# 后台生成', language: 'chinese', model: 'deepseek-chat' },
    })
    await router.isReady()
    const wrapper = mount(PPT, { global: { plugins: [createPinia(), router] } })
    await flushPromises()

    await wrapper.get('.btn-primary').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="generation-destination"]').trigger('click')

    expect(wrapper.get('[data-testid="generation-destination"]').text()).toContain('改为创建后打开编辑器')

    resolveCreate?.({
      presentation: {
        id: 'presentation-background', title: '后台生成', status: 'generating',
        currentVersion: 1, slideCount: 0, templateId: 'template_1', thumbnailFileId: null,
        createdAt: '2026-08-18T00:00:00Z', updatedAt: '2026-08-18T00:00:00Z',
      },
      taskId: 'task-background',
      reused: false,
    })
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('Works')
  })

  it('任务已创建但自动跳转失败时保留成功状态和手动入口', async () => {
    const router = testRouter()
    await router.push({
      name: 'PPT',
      query: { outline: '# 跳转兜底', language: 'chinese', model: 'deepseek-chat' },
    })
    await router.isReady()
    const wrapper = mount(PPT, { global: { plugins: [createPinia(), router] } })
    await flushPromises()
    const pushSpy = vi.spyOn(router, 'push').mockRejectedValueOnce(new Error('navigation failed'))

    await wrapper.get('.btn-primary').trigger('click')
    await flushPromises()

    expect(mockedMessage.success).toHaveBeenCalledWith('生成任务已创建')
    expect(mockedMessage.error).not.toHaveBeenCalled()
    expect(mockedMessage.warning).toHaveBeenCalledWith(
      '生成任务已创建，但页面自动跳转失败，请手动选择下一步',
    )
    expect(wrapper.get('[data-testid="generation-navigation-fallback"]').text()).toContain('自动跳转未完成')

    await wrapper.get('[data-testid="generation-navigation-fallback"] .destination-button').trigger('click')
    await flushPromises()

    expect(pushSpy).toHaveBeenLastCalledWith({
      name: 'PresentationEditor',
      params: { presentationId: 'presentation-uat-1' },
    })
    expect(router.currentRoute.value.name).toBe('PresentationEditor')
  })

  it('用户等待期间离开页面后，任务完成也不会强制跳回', async () => {
    let resolveCreate: ((value: Awaited<ReturnType<typeof presentationApi.create>>) => void) | undefined
    mockedPresentationApi.create.mockImplementationOnce(() => new Promise(resolve => {
      resolveCreate = resolve
    }))
    const router = testRouter()
    await router.push({
      name: 'PPT',
      query: { outline: '# 离开页面', language: 'chinese', model: 'deepseek-chat' },
    })
    await router.isReady()
    const wrapper = mount(PPT, { global: { plugins: [createPinia(), router] } })
    await flushPromises()

    await wrapper.get('.btn-primary').trigger('click')
    await flushPromises()
    wrapper.unmount()
    await router.push({ name: 'Works' })

    resolveCreate?.({
      presentation: {
        id: 'presentation-after-leave', title: '离开页面', status: 'generating',
        currentVersion: 1, slideCount: 0, templateId: 'template_1', thumbnailFileId: null,
        createdAt: '2026-08-18T00:00:00Z', updatedAt: '2026-08-18T00:00:00Z',
      },
      taskId: 'task-after-leave',
      reused: false,
    })
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('Works')
  })

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

  it('可信来源配置错误时提示管理员检查应用地址', async () => {
    mockedPresentationApi.create.mockRejectedValueOnce(
      new PresentationApiError(403, 'AUTH_ORIGIN_REJECTED'),
    )
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

    expect(mockedMessage.error).toHaveBeenCalledWith(
      '当前访问地址未获服务端信任，请联系管理员检查应用地址配置',
    )
    expect(router.currentRoute.value.name).toBe('PPT')
  })
})

import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useMainStore, useSlidesStore } from '@/store'
import { presentationApi, type PresentationDetail } from '@/services/presentations'
import EditorHeader from '../index.vue'

async function mountHeader(persistent = true) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/editor', name: 'Editor', component: { template: '<div />' } },
      { path: '/editor/:presentationId', name: 'PresentationEditor', component: { template: '<div />' } },
      { path: '/works', name: 'Works', component: { template: '<div />' } },
    ],
  })
  await router.push(persistent ? '/editor/presentation-1' : '/editor')
  await router.isReady()

  const slidesStore = useSlidesStore()
  slidesStore.presentationId = persistent ? 'presentation-1' : null
  slidesStore.setTitle('Linux 入门')

  const wrapper = shallowMount(EditorHeader, {
    global: {
      plugins: [pinia, router],
      directives: { tooltip: () => undefined },
      stubs: {
        IconClick: true,
        IconFilePdf: true,
        IconFileJpg: true,
        IconNotes: true,
        IconDownload: true,
        IconRefresh: true,
        IconMark: true,
        IconCommand: true,
        IconHamburgerButton: true,
        IconSlideTwo: true,
        IconPpt: true,
        IconDown: true,
        IconCheck: true,
      },
    },
  })
  return { wrapper, router }
}

describe('EditorHeader 工作台与文件入口', () => {
  afterEach(() => vi.restoreAllMocks())

  it('在编辑器顶栏直接展示稳定作品路径，并可返回用户工作台', async () => {
    const { wrapper, router } = await mountHeader()

    const workspace = wrapper.get('[data-testid="editor-workspace-link"]')
    expect(wrapper.get('[data-testid="editor-file-path"]').text()).toContain('Linux 入门')

    await workspace.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('Works')
  })

  it('提供带文字的导出入口并打开生成文件面板', async () => {
    const { wrapper } = await mountHeader()

    await wrapper.get('[data-testid="editor-export-file"]').trigger('click')
    expect(useMainStore().dialogForExport).toBe('pptx')
  })

  it('临时作品可以保存到个人工作台并切换为稳定作品路径', async () => {
    const { wrapper, router } = await mountHeader(false)
    const slidesStore = useSlidesStore()
    const detail = {
      id: 'saved-presentation-1',
      title: 'Linux 入门',
      status: 'draft',
      currentVersion: 1,
      slideCount: slidesStore.slides.length,
      templateId: null,
      thumbnailFileId: null,
      createdAt: '2026-07-23T08:00:00Z',
      updatedAt: '2026-07-23T08:00:00Z',
      document: {
        schemaVersion: 1,
        slides: slidesStore.slides,
        theme: slidesStore.theme,
        viewportSize: slidesStore.viewportSize,
        viewportRatio: slidesStore.viewportRatio,
      },
    } satisfies PresentationDetail
    const saveDraft = vi.spyOn(presentationApi, 'saveDraft').mockResolvedValue({
      presentation: detail,
      reused: false,
    })

    await wrapper.get('[data-testid="editor-save-work"]').trigger('click')
    await flushPromises()

    expect(saveDraft).toHaveBeenCalledOnce()
    expect(slidesStore.presentationId).toBe('saved-presentation-1')
    expect(router.currentRoute.value).toMatchObject({
      name: 'PresentationEditor',
      params: { presentationId: 'saved-presentation-1' },
    })
  })
})

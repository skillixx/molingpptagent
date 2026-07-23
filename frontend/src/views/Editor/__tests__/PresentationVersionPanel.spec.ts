import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { presentationApi } from '@/services/presentations'
import { useSlidesStore } from '@/store'
import PresentationVersionPanel from '../PresentationVersionPanel.vue'


const version = {
  id: 'version-2',
  version: 2,
  reason: 'manual' as const,
  createdAt: '2026-07-23T05:00:00Z',
  contentSha256: 'a'.repeat(64),
  uncompressedBytes: 256,
}

describe('PresentationVersionPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const slidesStore = useSlidesStore()
    slidesStore.presentationId = 'presentation-1'
    slidesStore.presentationVersion = 2
    vi.restoreAllMocks()
  })

  it('打开面板加载摘要，手动检查点先保存再创建', async () => {
    vi.spyOn(presentationApi, 'listVersions').mockResolvedValue({ items: [version], total: 1 })
    vi.spyOn(presentationApi, 'createCheckpoint').mockResolvedValue(version)
    const engine = { status: 'dirty', saveNow: vi.fn(async () => { engine.status = 'saved' }) }
    const wrapper = mount(PresentationVersionPanel, {
      props: { engine, applyRestored: vi.fn() },
    })

    await wrapper.get('[data-testid="toggle-version-panel"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('版本 v2'))
    await wrapper.get('[data-testid="create-manual-checkpoint"]').trigger('click')

    expect(engine.saveNow).toHaveBeenCalledTimes(1)
    expect(presentationApi.createCheckpoint).toHaveBeenCalledWith('presentation-1', 2, 'manual')
    expect(wrapper.text()).toContain('检查点已保存')
  })

  it('恢复必须确认并以当前版本为基线，成功后重新加载编辑器', async () => {
    vi.spyOn(presentationApi, 'listVersions').mockResolvedValue({ items: [version], total: 1 })
    vi.spyOn(presentationApi, 'restoreVersion').mockResolvedValue({} as never)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const applyRestored = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(PresentationVersionPanel, {
      props: { engine: { status: 'saved', saveNow: vi.fn() }, applyRestored },
    })

    await wrapper.get('[data-testid="toggle-version-panel"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="restore-version-2"]').exists()).toBe(true))
    await wrapper.get('[data-testid="restore-version-2"]').trigger('click')

    expect(window.confirm).toHaveBeenCalled()
    expect(presentationApi.restoreVersion).toHaveBeenCalledWith('presentation-1', 2, 2)
    expect(applyRestored).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('已恢复为新版本')
  })

  it('未保存或离线状态阻止恢复且所有按钮都有反馈', async () => {
    vi.spyOn(presentationApi, 'listVersions').mockResolvedValue({ items: [version], total: 1 })
    const restore = vi.spyOn(presentationApi, 'restoreVersion')
    const wrapper = mount(PresentationVersionPanel, {
      props: { engine: { status: 'offline', saveNow: vi.fn() }, applyRestored: vi.fn() },
    })

    await wrapper.get('[data-testid="toggle-version-panel"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="restore-version-2"]').exists()).toBe(true))
    await wrapper.get('[data-testid="restore-version-2"]').trigger('click')

    expect(restore).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请先联网并保存当前修改')
  })
})

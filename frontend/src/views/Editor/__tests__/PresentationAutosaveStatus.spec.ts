import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import PresentationAutosaveStatus from '@/views/Editor/PresentationAutosaveStatus.vue'


function engine(overrides: Record<string, unknown> = {}) {
  return {
    status: 'dirty',
    errorCode: null,
    needsRetryConfirmation: false,
    recoveryDraft: null,
    localDraftAvailable: true,
    conflict: null,
    acceptRecovery: vi.fn(),
    discardRecovery: vi.fn(),
    confirmRetry: vi.fn(),
    saveNow: vi.fn(),
    loadLatest: vi.fn(),
    saveAsCopy: vi.fn(),
    ...overrides,
  }
}

describe('PresentationAutosaveStatus', () => {
  it('脏稿可手动保存且按钮有真实回调', async () => {
    const controller = engine()
    const wrapper = mount(PresentationAutosaveStatus, { props: { engine: controller as never } })
    expect(wrapper.text()).toContain('有未保存修改')
    await wrapper.get('[data-testid="manual-save"]').trigger('click')
    expect(controller.saveNow).toHaveBeenCalledTimes(1)
  })

  it('本地草稿提供恢复和忽略两个可操作选择', async () => {
    const controller = engine({ recoveryDraft: { title: '本地稿' } })
    const wrapper = mount(PresentationAutosaveStatus, { props: { engine: controller as never, mobile: true } })
    await wrapper.get('[data-testid="recover-local-draft"]').trigger('click')
    await wrapper.get('[data-testid="discard-local-draft"]').trigger('click')
    expect(controller.acceptRecovery).toHaveBeenCalledTimes(1)
    expect(controller.discardRecovery).toHaveBeenCalledTimes(1)
  })

  it('联网恢复后只有用户确认才调用重试', async () => {
    const controller = engine({ status: 'error', needsRetryConfirmation: true })
    const wrapper = mount(PresentationAutosaveStatus, { props: { engine: controller as never } })
    expect(controller.confirmRetry).not.toHaveBeenCalled()
    await wrapper.get('[data-testid="confirm-save-retry"]').trigger('click')
    expect(controller.confirmRetry).toHaveBeenCalledTimes(1)
  })

  it('离线按钮明确禁用而不是伪装可保存', () => {
    const wrapper = mount(PresentationAutosaveStatus, {
      props: { engine: engine({ status: 'offline' }) as never },
    })
    const button = wrapper.get('[data-testid="manual-save"]')
    expect(button.text()).toBe('等待联网')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('版本冲突提供加载最新和另存副本两个真实动作', async () => {
    const controller = engine({
      status: 'conflict',
      conflict: { title: '最新稿', currentVersion: 4, updatedAt: '2026-07-23T05:00:00Z' },
    })
    const wrapper = mount(PresentationAutosaveStatus, { props: { engine: controller as never } })
    expect(wrapper.text()).toContain('最新为 v4')
    await wrapper.get('[data-testid="load-latest-version"]').trigger('click')
    await wrapper.get('[data-testid="save-conflict-copy"]').trigger('click')
    expect(controller.loadLatest).toHaveBeenCalledTimes(1)
    expect(controller.saveAsCopy).toHaveBeenCalledTimes(1)
  })
})

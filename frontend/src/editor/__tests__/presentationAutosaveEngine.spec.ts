import { beforeEach, describe, expect, it, vi } from 'vitest'
import { shallowReactive } from 'vue'

import {
  PresentationAutosaveEngine,
  type EditablePresentationSnapshot,
  type LocalPresentationDraft,
} from '@/editor/presentationAutosaveEngine'


function snapshot(title: string, version = 1): EditablePresentationSnapshot {
  return {
    presentationId: 'presentation-1',
    version,
    title,
    document: {
      schemaVersion: 1,
      slides: [{ id: 'slide-1', elements: [], remark: title }],
      theme: {},
      viewportSize: 1000,
      viewportRatio: 0.5625,
    },
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((ok, fail) => { resolve = ok; reject = fail })
  return { promise, resolve, reject }
}

describe('PresentationAutosaveEngine', () => {
  beforeEach(() => vi.useFakeTimers())

  it('连续输入只在2秒静默后保存最新稿', async () => {
    const save = vi.fn().mockResolvedValue({ currentVersion: 2 })
    const writeDraft = vi.fn().mockResolvedValue(undefined)
    const engine = new PresentationAutosaveEngine({
      save,
      readDraft: vi.fn().mockResolvedValue(null),
      writeDraft,
      deleteDraft: vi.fn().mockResolvedValue(undefined),
      isOnline: () => true,
    })
    await engine.activate('user-1', snapshot('初始'))

    await engine.markChanged(snapshot('第一次'))
    await vi.advanceTimersByTimeAsync(1500)
    await engine.markChanged(snapshot('最终内容'))
    await vi.advanceTimersByTimeAsync(1999)
    expect(save).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)

    expect(save).toHaveBeenCalledTimes(1)
    expect(save.mock.calls[0][0].title).toBe('最终内容')
    expect(writeDraft).toHaveBeenLastCalledWith('user-1', expect.objectContaining({ title: '最终内容' }))
  })

  it('慢请求期间只允许一个请求在途，完成后立即保存排队的最新稿', async () => {
    const first = deferred<{ currentVersion: number }>()
    const save = vi.fn()
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ currentVersion: 3 })
    const engine = new PresentationAutosaveEngine({
      save,
      readDraft: vi.fn().mockResolvedValue(null),
      writeDraft: vi.fn().mockResolvedValue(undefined),
      deleteDraft: vi.fn().mockResolvedValue(undefined),
      isOnline: () => true,
    })
    await engine.activate('user-1', snapshot('初始'))
    await engine.markChanged(snapshot('请求一'))
    await vi.advanceTimersByTimeAsync(2000)
    expect(save).toHaveBeenCalledTimes(1)

    await engine.markChanged(snapshot('请求二'))
    await vi.advanceTimersByTimeAsync(2000)
    expect(save).toHaveBeenCalledTimes(1)
    first.resolve({ currentVersion: 2 })
    await vi.runAllTimersAsync()
    await Promise.resolve()
    expect(save).toHaveBeenCalledTimes(2)
    expect(save.mock.calls[1][0].title).toBe('请求二')
    expect(engine.status).toBe('saved')
  })

  it('断网保留草稿，恢复网络后必须用户确认才重试', async () => {
    let online = false
    const save = vi.fn().mockResolvedValue({ currentVersion: 2 })
    const engine = new PresentationAutosaveEngine({
      save,
      readDraft: vi.fn().mockResolvedValue(null),
      writeDraft: vi.fn().mockResolvedValue(undefined),
      deleteDraft: vi.fn().mockResolvedValue(undefined),
      isOnline: () => online,
    })
    await engine.activate('user-1', snapshot('初始'))
    await engine.markChanged(snapshot('离线草稿'))
    await vi.advanceTimersByTimeAsync(2000)
    expect(save).not.toHaveBeenCalled()
    expect(engine.status).toBe('offline')

    online = true
    engine.handleOnline()
    expect(engine.needsRetryConfirmation).toBe(true)
    expect(save).not.toHaveBeenCalled()
    await engine.confirmRetry()
    expect(save).toHaveBeenCalledTimes(1)
    expect(engine.needsRetryConfirmation).toBe(false)
  })

  it('关闭再打开时只提示恢复同身份同作品且同服务端版本的本地稿', async () => {
    const localDraft: LocalPresentationDraft = {
      ...snapshot('本地未保存内容'),
      scope: 'user-1',
      updatedAt: 100,
    }
    const applyRecovered = vi.fn()
    const deleteDraft = vi.fn().mockResolvedValue(undefined)
    const engine = new PresentationAutosaveEngine({
      save: vi.fn().mockResolvedValue({ currentVersion: 2 }),
      readDraft: vi.fn().mockResolvedValue(localDraft),
      writeDraft: vi.fn().mockResolvedValue(undefined),
      deleteDraft,
      isOnline: () => true,
      applyRecovered,
    })

    await engine.activate('user-1', snapshot('服务端内容'))
    expect(engine.recoveryDraft?.title).toBe('本地未保存内容')
    await engine.acceptRecovery()
    expect(applyRecovered).toHaveBeenCalledWith(expect.objectContaining({ title: '本地未保存内容' }))
    expect(engine.status).toBe('dirty')
    expect(engine.shouldBlockLeave()).toBe(true)

    const stale = new PresentationAutosaveEngine({
      save: vi.fn(),
      readDraft: vi.fn().mockResolvedValue({ ...localDraft, version: 1 }),
      writeDraft: vi.fn(),
      deleteDraft,
      isOnline: () => true,
    })
    await stale.activate('user-1', snapshot('服务端已更新', 2))
    expect(stale.recoveryDraft).toBeNull()
    expect(deleteDraft).toHaveBeenCalled()
  })

  it('保存失败不丢草稿且保存中或脏稿触发离开保护', async () => {
    const pending = deferred<{ currentVersion: number }>()
    const engine = new PresentationAutosaveEngine({
      save: vi.fn().mockReturnValue(pending.promise),
      readDraft: vi.fn().mockResolvedValue(null),
      writeDraft: vi.fn().mockResolvedValue(undefined),
      deleteDraft: vi.fn().mockResolvedValue(undefined),
      isOnline: () => true,
    })
    await engine.activate('user-1', snapshot('初始'))
    await engine.markChanged(snapshot('待保存'))
    expect(engine.shouldBlockLeave()).toBe(true)
    const saving = engine.saveNow()
    expect(engine.status).toBe('saving')
    expect(engine.shouldBlockLeave()).toBe(true)
    pending.reject(new Error('raw network failure'))
    await saving
    expect(engine.status).toBe('error')
    expect(engine.errorCode).toBe('PRESENTATION_SAVE_FAILED')
    expect(engine.shouldBlockLeave()).toBe(true)
  })

  it('Vue集成只做浅层响应式，写入草稿仍是可结构化克隆的纯对象', async () => {
    const writeDraft = vi.fn(async (_scope, value) => { structuredClone(value) })
    const engine = shallowReactive(new PresentationAutosaveEngine({
      save: vi.fn().mockResolvedValue({ currentVersion: 2 }),
      readDraft: vi.fn().mockResolvedValue(null),
      writeDraft,
      deleteDraft: vi.fn().mockResolvedValue(undefined),
      isOnline: () => true,
    }))
    await engine.activate('user-1', snapshot('初始'))
    await expect(engine.markChanged(snapshot('可克隆稿'))).resolves.toBeUndefined()
    expect(writeDraft).toHaveBeenCalledTimes(1)
  })

  it('IndexedDB不可用时仍执行云端保存并暴露本地兜底告警', async () => {
    const save = vi.fn().mockResolvedValue({ currentVersion: 2 })
    const engine = new PresentationAutosaveEngine({
      save,
      readDraft: vi.fn().mockRejectedValue(new Error('indexeddb denied')),
      writeDraft: vi.fn().mockRejectedValue(new Error('quota exceeded')),
      deleteDraft: vi.fn().mockRejectedValue(new Error('delete denied')),
      isOnline: () => true,
    })
    await expect(engine.activate('user-1', snapshot('初始'))).resolves.toBeUndefined()
    expect(engine.localDraftAvailable).toBe(false)
    await expect(engine.markChanged(snapshot('仍需云端保存'))).resolves.toBeUndefined()
    await vi.advanceTimersByTimeAsync(2000)
    expect(save).toHaveBeenCalledTimes(1)
    expect(engine.status).toBe('saved')
    expect(engine.localDraftAvailable).toBe(false)
  })

  it('同一作品重新加载时旧草稿读取结果不能覆盖新一轮激活', async () => {
    const oldRead = deferred<LocalPresentationDraft | null>()
    const readDraft = vi.fn()
      .mockReturnValueOnce(oldRead.promise)
      .mockResolvedValueOnce(null)
    const deleteDraft = vi.fn().mockResolvedValue(undefined)
    const engine = new PresentationAutosaveEngine({
      save: vi.fn(),
      readDraft,
      writeDraft: vi.fn(),
      deleteDraft,
      isOnline: () => true,
    })
    const firstActivation = engine.activate('user-1', snapshot('第一轮', 1))
    await engine.activate('user-1', snapshot('第二轮', 2))
    oldRead.resolve({ ...snapshot('旧本地稿', 1), scope: 'user-1', updatedAt: 1 })
    await firstActivation
    expect(engine.recoveryDraft).toBeNull()
    expect(deleteDraft).not.toHaveBeenCalled()
  })

  it('409进入冲突态并保留后续本地编辑，不再自动重复覆盖', async () => {
    const save = vi.fn().mockRejectedValue({
      code: 'PRESENTATION_VERSION_CONFLICT',
      latest: { title: '标签A版本', currentVersion: 2, updatedAt: '2026-07-23T05:00:00Z' },
    })
    const deleteDraft = vi.fn()
    const engine = new PresentationAutosaveEngine({
      save,
      readDraft: vi.fn().mockResolvedValue(null),
      writeDraft: vi.fn().mockResolvedValue(undefined),
      deleteDraft,
      isOnline: () => true,
    })
    await engine.activate('user-1', snapshot('标签B初始'))
    await engine.markChanged(snapshot('标签B冲突稿'))
    await engine.saveNow()
    expect(engine.status).toBe('conflict')
    expect(engine.conflict).toEqual({
      title: '标签A版本', currentVersion: 2, updatedAt: '2026-07-23T05:00:00Z',
    })
    expect(deleteDraft).not.toHaveBeenCalled()

    await engine.markChanged(snapshot('冲突后继续编辑'))
    await vi.advanceTimersByTimeAsync(5000)
    expect(save).toHaveBeenCalledTimes(1)
    expect(engine.status).toBe('conflict')
    expect(engine.shouldBlockLeave()).toBe(true)
  })

  it('冲突后可加载最新或把本地稿另存为版本1副本', async () => {
    const conflict = {
      code: 'PRESENTATION_VERSION_CONFLICT',
      latest: { title: '最新稿', currentVersion: 2, updatedAt: '2026-07-23T05:00:00Z' },
    }
    const reloadLatest = vi.fn().mockResolvedValue(undefined)
    const saveAsCopy = vi.fn().mockResolvedValue({ id: 'copy-1', currentVersion: 1 })
    const onCopyCreated = vi.fn()
    const deleteDraft = vi.fn().mockResolvedValue(undefined)
    const dependencies = {
      save: vi.fn().mockRejectedValue(conflict),
      readDraft: vi.fn().mockResolvedValue(null),
      writeDraft: vi.fn().mockResolvedValue(undefined),
      deleteDraft,
      isOnline: () => true,
      reloadLatest,
      saveAsCopy,
      onCopyCreated,
    }
    const latestEngine = new PresentationAutosaveEngine(dependencies)
    await latestEngine.activate('user-1', snapshot('本地稿'))
    await latestEngine.markChanged(snapshot('本地冲突稿'))
    await latestEngine.saveNow()
    await latestEngine.loadLatest()
    expect(deleteDraft).toHaveBeenCalledWith('user-1', 'presentation-1')
    expect(reloadLatest).toHaveBeenCalledWith('presentation-1')

    const copyEngine = new PresentationAutosaveEngine(dependencies)
    await copyEngine.activate('user-1', snapshot('本地稿'))
    await copyEngine.markChanged(snapshot('需要另存的本地稿'))
    await copyEngine.saveNow()
    await copyEngine.saveAsCopy()
    expect(saveAsCopy).toHaveBeenCalledWith(expect.objectContaining({ title: '需要另存的本地稿' }))
    expect(onCopyCreated).toHaveBeenCalledWith('copy-1')
  })

  it('加载最新失败时不删除本地冲突稿，仍可选择另存副本', async () => {
    const deleteDraft = vi.fn()
    const engine = new PresentationAutosaveEngine({
      save: vi.fn().mockRejectedValue({
        code: 'PRESENTATION_VERSION_CONFLICT',
        latest: { title: '最新稿', currentVersion: 2, updatedAt: '2026-07-23T05:00:00Z' },
      }),
      readDraft: vi.fn().mockResolvedValue(null),
      writeDraft: vi.fn().mockResolvedValue(undefined),
      deleteDraft,
      isOnline: () => true,
      reloadLatest: vi.fn().mockRejectedValue(new Error('network failed')),
    })
    await engine.activate('user-1', snapshot('本地稿'))
    await engine.markChanged(snapshot('本地冲突稿'))
    await engine.saveNow()
    await engine.loadLatest()
    expect(engine.status).toBe('conflict')
    expect(engine.conflict).not.toBeNull()
    expect(deleteDraft).not.toHaveBeenCalled()
  })
})

import type { PresentationConflictSummary, PresentationDocument } from '@/services/presentations'


export type PresentationSaveStatus = 'idle' | 'saved' | 'dirty' | 'saving' | 'offline' | 'error' | 'conflict'

export interface EditablePresentationSnapshot {
  presentationId: string
  version: number
  title: string
  document: PresentationDocument
}

export interface LocalPresentationDraft extends EditablePresentationSnapshot {
  scope: string
  updatedAt: number
}

interface SaveResult { currentVersion: number }

export interface PresentationAutosaveDependencies {
  save: (snapshot: EditablePresentationSnapshot) => Promise<SaveResult>
  readDraft: (scope: string, presentationId: string) => Promise<LocalPresentationDraft | null>
  writeDraft: (scope: string, draft: EditablePresentationSnapshot) => Promise<void>
  deleteDraft: (scope: string, presentationId: string) => Promise<void>
  isOnline: () => boolean
  applyRecovered?: (snapshot: EditablePresentationSnapshot) => void
  onSavedVersion?: (version: number) => void
  reloadLatest?: (presentationId: string) => Promise<void>
  saveAsCopy?: (snapshot: EditablePresentationSnapshot) => Promise<{ id: string; currentVersion: number }>
  onCopyCreated?: (presentationId: string) => void
  delayMs?: number
}

export class PresentationAutosaveEngine {
  status: PresentationSaveStatus = 'idle'
  errorCode: string | null = null
  needsRetryConfirmation = false
  recoveryDraft: LocalPresentationDraft | null = null
  lastSavedAt: number | null = null
  localDraftAvailable = true
  conflict: PresentationConflictSummary | null = null

  private scope = ''
  private current: EditablePresentationSnapshot | null = null
  private timer: ReturnType<typeof setTimeout> | null = null
  private inFlight: Promise<void> | null = null
  private changedDuringSave = false
  private active = false
  private activationEpoch = 0

  constructor(private readonly dependencies: PresentationAutosaveDependencies) {}

  async activate(scope: string, server: EditablePresentationSnapshot): Promise<void> {
    const epoch = ++this.activationEpoch
    this.cancelTimer()
    this.scope = scope
    this.current = structuredClone(server)
    this.active = true
    this.status = 'saved'
    this.errorCode = null
    this.needsRetryConfirmation = false
    this.recoveryDraft = null
    this.conflict = null
    this.localDraftAvailable = true
    let draft: LocalPresentationDraft | null
    try {
      draft = await this.dependencies.readDraft(scope, server.presentationId)
    }
    catch {
      // 浏览器禁用IndexedDB时仍允许云端保存，但必须向用户暴露本地兜底不可用。
      if (epoch === this.activationEpoch) {
        this.localDraftAvailable = false
        this.errorCode = 'LOCAL_DRAFT_UNAVAILABLE'
      }
      return
    }
    if (epoch !== this.activationEpoch || !this.active || this.current?.presentationId !== server.presentationId) return
    if (!draft) return
    // 旧服务端版本的草稿不能直接覆盖新稿；T13会提供冲突另存流程。
    if (draft.version !== server.version) {
      await this.tryDeleteDraft(scope, server.presentationId)
      return
    }
    if (this.signature(draft) === this.signature(server)) {
      await this.tryDeleteDraft(scope, server.presentationId)
      return
    }
    this.recoveryDraft = draft
  }

  deactivate(): void {
    this.activationEpoch += 1
    this.active = false
    this.cancelTimer()
  }

  async markChanged(snapshot: EditablePresentationSnapshot): Promise<void> {
    if (!this.active || snapshot.presentationId !== this.current?.presentationId) return
    this.current = structuredClone(snapshot)
    this.status = this.conflict ? 'conflict' : 'dirty'
    this.errorCode = null
    if (this.inFlight) this.changedDuringSave = true
    if (!this.conflict) this.schedule()
    try {
      await this.dependencies.writeDraft(this.scope, this.current)
      this.localDraftAvailable = true
    }
    catch {
      // 本地写失败不能阻断已排定的云端保存；离线时UI会明确提示没有本地兜底。
      this.localDraftAvailable = false
      this.errorCode = 'LOCAL_DRAFT_UNAVAILABLE'
    }
  }

  async saveNow(): Promise<void> {
    this.cancelTimer()
    if (!this.current || !this.active) return
    if (this.conflict) return
    if (this.inFlight) {
      this.changedDuringSave = true
      return this.inFlight
    }
    if (!this.dependencies.isOnline()) {
      this.status = 'offline'
      this.needsRetryConfirmation = false
      return
    }
    const saving = structuredClone(this.current)
    this.changedDuringSave = false
    this.status = 'saving'
    this.errorCode = null
    this.inFlight = this.performSave(saving)
    await this.inFlight
  }

  handleOnline(): void {
    if (!this.active || !this.current) return
    if (this.status === 'offline' || this.status === 'error' || this.status === 'dirty') {
      // 网络恢复只提示，不自动重放可能产生业务冲突的写请求。
      this.needsRetryConfirmation = true
    }
  }

  async confirmRetry(): Promise<void> {
    this.needsRetryConfirmation = false
    await this.saveNow()
  }

  async acceptRecovery(): Promise<void> {
    if (!this.recoveryDraft) return
    const recovered = structuredClone(this.recoveryDraft)
    this.recoveryDraft = null
    this.current = recovered
    this.dependencies.applyRecovered?.(recovered)
    this.status = 'dirty'
    this.schedule()
    try {
      await this.dependencies.writeDraft(this.scope, recovered)
      this.localDraftAvailable = true
    }
    catch {
      this.localDraftAvailable = false
      this.errorCode = 'LOCAL_DRAFT_UNAVAILABLE'
    }
  }

  async discardRecovery(): Promise<void> {
    if (!this.current) return
    this.recoveryDraft = null
    await this.tryDeleteDraft(this.scope, this.current.presentationId)
  }

  async loadLatest(): Promise<void> {
    if (!this.current || !this.conflict || !this.dependencies.reloadLatest) return
    const presentationId = this.current.presentationId
    this.cancelTimer()
    this.status = 'saving'
    try {
      // 先确认最新稿成功加载，再删除用户明确放弃的冲突草稿；网络失败时仍可另存副本。
      await this.dependencies.reloadLatest(presentationId)
      await this.tryDeleteDraft(this.scope, presentationId)
      this.conflict = null
      this.status = 'saved'
    }
    catch {
      this.status = 'conflict'
      this.errorCode = 'PRESENTATION_LOAD_LATEST_FAILED'
    }
  }

  async saveAsCopy(): Promise<void> {
    if (!this.current || !this.conflict || !this.dependencies.saveAsCopy) return
    const local = structuredClone(this.current)
    this.cancelTimer()
    this.status = 'saving'
    try {
      const copied = await this.dependencies.saveAsCopy(local)
      await this.tryDeleteDraft(this.scope, local.presentationId)
      this.conflict = null
      this.status = 'saved'
      this.dependencies.onCopyCreated?.(copied.id)
    }
    catch (error) {
      this.status = this.dependencies.isOnline() ? 'error' : 'offline'
      const code = typeof error === 'object' && error && 'code' in error ? String(error.code) : ''
      this.errorCode = /^[A-Z0-9_]{1,64}$/.test(code) ? code : 'PRESENTATION_COPY_FAILED'
    }
  }

  shouldBlockLeave(): boolean {
    return ['dirty', 'saving', 'offline', 'error', 'conflict'].includes(this.status)
  }

  private async performSave(saving: EditablePresentationSnapshot): Promise<void> {
    try {
      const result = await this.dependencies.save(saving)
      if (!this.active || this.current?.presentationId !== saving.presentationId) return
      this.current.version = result.currentVersion
      this.dependencies.onSavedVersion?.(result.currentVersion)
      const hasNewerChanges = this.changedDuringSave || this.signature(this.current) !== this.signature(saving)
      if (hasNewerChanges) {
        this.status = 'dirty'
      }
      else {
        await this.tryDeleteDraft(this.scope, saving.presentationId)
        this.status = 'saved'
        this.lastSavedAt = Date.now()
      }
    }
    catch (error) {
      if (!this.active) return
      const conflict = this.parseConflict(error)
      if (conflict) {
        this.conflict = conflict
        this.status = 'conflict'
        this.errorCode = 'PRESENTATION_VERSION_CONFLICT'
        return
      }
      this.status = this.dependencies.isOnline() ? 'error' : 'offline'
      const code = typeof error === 'object' && error && 'code' in error ? String(error.code) : ''
      this.errorCode = /^[A-Z0-9_]{1,64}$/.test(code) ? code : 'PRESENTATION_SAVE_FAILED'
    }
    finally {
      this.inFlight = null
      if (this.active && this.changedDuringSave && this.status === 'dirty') {
        this.changedDuringSave = false
        // 慢请求期间积累的修改已经等满防抖窗口，释放在途锁后立即保存最新稿。
        void this.saveNow()
      }
    }
  }

  private schedule(): void {
    this.cancelTimer()
    this.timer = setTimeout(() => void this.saveNow(), this.dependencies.delayMs ?? 2000)
  }

  private cancelTimer(): void {
    if (this.timer !== null) clearTimeout(this.timer)
    this.timer = null
  }

  private signature(snapshot: EditablePresentationSnapshot): string {
    return JSON.stringify({ title: snapshot.title, document: snapshot.document })
  }

  private async tryDeleteDraft(scope: string, presentationId: string): Promise<void> {
    try {
      await this.dependencies.deleteDraft(scope, presentationId)
    }
    catch {
      // 服务端保存已成功时，清理本地辅助数据失败不能伪装成云端保存失败或触发重复PATCH。
      this.localDraftAvailable = false
      this.errorCode = 'LOCAL_DRAFT_UNAVAILABLE'
    }
  }

  private parseConflict(error: unknown): PresentationConflictSummary | null {
    if (!error || typeof error !== 'object' || !('code' in error) || !('latest' in error)) return null
    if (String(error.code) !== 'PRESENTATION_VERSION_CONFLICT') return null
    const latest = error.latest
    if (!latest || typeof latest !== 'object') return null
    const value = latest as Record<string, unknown>
    if (
      typeof value.title !== 'string' || !value.title ||
      !Number.isInteger(value.currentVersion) || Number(value.currentVersion) < 1 ||
      typeof value.updatedAt !== 'string' || Number.isNaN(Date.parse(value.updatedAt))
    ) return null
    return {
      title: value.title,
      currentVersion: Number(value.currentVersion),
      updatedAt: value.updatedAt,
    }
  }
}

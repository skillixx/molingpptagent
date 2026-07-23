import Dexie, { type EntityTable } from 'dexie'

import type { EditablePresentationSnapshot, LocalPresentationDraft } from '@/editor/presentationAutosaveEngine'


interface DraftRecord extends LocalPresentationDraft {
  key: string
}

const draftDatabase = new Dexie('trainppt_moling_drafts_v1') as Dexie & {
  drafts: EntityTable<DraftRecord, 'key'>
}

// 草稿库名称稳定，关闭页面后仍可恢复；key同时绑定身份与作品，避免同浏览器串稿。
draftDatabase.version(1).stores({ drafts: 'key,scope,presentationId,updatedAt' })

function key(scope: string, presentationId: string): string {
  return `${scope}:${presentationId}`
}

export const presentationDrafts = {
  async read(scope: string, presentationId: string): Promise<LocalPresentationDraft | null> {
    const record = await draftDatabase.drafts.get(key(scope, presentationId))
    if (!record || record.scope !== scope || record.presentationId !== presentationId) return null
    const { key: _key, ...draft } = record
    return structuredClone(draft)
  },

  async write(scope: string, snapshot: EditablePresentationSnapshot): Promise<void> {
    // JSON稿件本身就是跨端契约；在存储边界再转一次纯对象，防止调用方误传Vue Proxy。
    const plainSnapshot = JSON.parse(JSON.stringify(snapshot)) as EditablePresentationSnapshot
    await draftDatabase.drafts.put({
      ...plainSnapshot,
      key: key(scope, snapshot.presentationId),
      scope,
      updatedAt: Date.now(),
    })
  },

  async remove(scope: string, presentationId: string): Promise<void> {
    await draftDatabase.drafts.delete(key(scope, presentationId))
  },
}

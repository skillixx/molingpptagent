<template>
  <section class="version-shell" :class="{ mobile }">
    <button
      type="button"
      class="toggle-button"
      data-testid="toggle-version-panel"
      :aria-expanded="open"
      @click="togglePanel"
    >历史版本</button>
    <div v-if="open" class="version-panel" aria-label="历史版本面板">
      <header>
        <div>
          <strong>检查点版本</strong>
          <p>恢复会生成新版本，不覆盖历史</p>
        </div>
        <button type="button" class="close-button" aria-label="关闭历史版本" @click="open = false">×</button>
      </header>

      <button
        type="button"
        class="primary-button"
        data-testid="create-manual-checkpoint"
        :disabled="!!busy"
        @click="createManualCheckpoint"
      >{{ busy === 'create' ? '正在保存…' : '保存当前检查点' }}</button>

      <p v-if="feedback" class="feedback" role="status">{{ feedback }}</p>
      <p v-if="loading" class="empty">正在加载版本…</p>
      <p v-else-if="!versions.length" class="empty">暂无检查点，可先保存当前版本</p>
      <ul v-else>
        <li v-for="item in versions" :key="item.id">
          <div class="version-copy">
            <strong>版本 v{{ item.version }}</strong>
            <span>{{ reasonLabel[item.reason] }} · {{ formatDate(item.createdAt) }}</span>
            <span>{{ formatBytes(item.uncompressedBytes) }} · {{ item.contentSha256.slice(0, 10) }}</span>
          </div>
          <button
            type="button"
            class="restore-button"
            :data-testid="`restore-version-${item.version}`"
            :disabled="!!busy"
            @click="restore(item.version)"
          >{{ busy === `restore-${item.version}` ? '恢复中…' : '恢复' }}</button>
        </li>
      </ul>
    </div>
  </section>
</template>

<script lang="ts" setup>
import { ref } from 'vue'

import type { PresentationSaveStatus } from '@/editor/presentationAutosaveEngine'
import { presentationApi, type PresentationDetail, type PresentationVersionSummary, type StoredCheckpointReason } from '@/services/presentations'
import { useSlidesStore } from '@/store'


type VersionPanelEngine = {
  status: PresentationSaveStatus
  saveNow: () => Promise<void>
}

const props = defineProps<{
  mobile?: boolean
  engine: VersionPanelEngine
  applyRestored: (detail: PresentationDetail) => Promise<void>
}>()
const slidesStore = useSlidesStore()
const open = ref(false)
const loading = ref(false)
const busy = ref<string>('')
const feedback = ref('')
const versions = ref<PresentationVersionSummary[]>([])

const reasonLabel: Record<StoredCheckpointReason, string> = {
  manual: '手动保存',
  ai: 'AI 操作',
  export: '导出',
  periodic: '周期节点',
  restore: '历史恢复',
}

async function togglePanel() {
  open.value = !open.value
  if (open.value) await loadVersions()
}

async function loadVersions() {
  const presentationId = slidesStore.presentationId
  if (!presentationId) return
  loading.value = true
  try {
    const result = await presentationApi.listVersions(presentationId)
    versions.value = result.items
  }
  catch {
    feedback.value = '版本加载失败，请重试'
  }
  finally {
    loading.value = false
  }
}

async function createManualCheckpoint() {
  const presentationId = slidesStore.presentationId
  if (!presentationId || slidesStore.presentationVersion === null) return
  if (props.engine.status === 'offline') {
    feedback.value = '请先联网并保存当前修改'
    return
  }
  busy.value = 'create'
  feedback.value = ''
  try {
    if (props.engine.status !== 'saved') await props.engine.saveNow()
    if (props.engine.status !== 'saved' || slidesStore.presentationVersion === null) {
      feedback.value = '当前修改尚未保存，不能创建检查点'
      return
    }
    await presentationApi.createCheckpoint(
      presentationId,
      slidesStore.presentationVersion,
      'manual',
    )
    feedback.value = '检查点已保存'
    await loadVersions()
  }
  catch {
    feedback.value = '检查点保存失败，当前作品未受影响'
  }
  finally {
    busy.value = ''
  }
}

async function restore(version: number) {
  const presentationId = slidesStore.presentationId
  const baseVersion = slidesStore.presentationVersion
  if (!presentationId || baseVersion === null) return
  if (props.engine.status !== 'saved') {
    feedback.value = '请先联网并保存当前修改'
    return
  }
  if (!window.confirm(`确认恢复版本 v${version}？当前历史不会被覆盖。`)) {
    feedback.value = '已取消恢复'
    return
  }
  busy.value = `restore-${version}`
  feedback.value = ''
  try {
    const restored = await presentationApi.restoreVersion(presentationId, version, baseVersion)
    await props.applyRestored(restored)
    feedback.value = '已恢复为新版本'
    await loadVersions()
  }
  catch {
    feedback.value = '恢复失败，请刷新版本后重试'
  }
  finally {
    busy.value = ''
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

function formatBytes(value: number): string {
  return value < 1024 ? `${value} B` : `${(value / 1024).toFixed(1)} KiB`
}
</script>

<style lang="scss" scoped>
.version-shell { position: fixed; top: 5px; right: 14px; z-index: 80; }
.toggle-button,.primary-button,.restore-button,.close-button { border: 0; font: inherit; cursor: pointer; }
.toggle-button { min-height: 30px; padding: 0 11px; color: #4338ca; border: 1px solid #c7d2fe; border-radius: 8px; background: #eef2ff; font-size: 12px; font-weight: 700; }
.version-panel { position: absolute; top: 38px; right: 0; width: min(360px, calc(100vw - 28px)); max-height: min(620px, calc(100vh - 56px)); overflow: auto; padding: 16px; border: 1px solid #e5e7eb; border-radius: 12px; background: #fff; box-shadow: 0 18px 50px rgba(15,23,42,.18); }
header { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
header strong { color: #111827; font-size: 15px; }
header p { margin: 4px 0 0; color: #6b7280; font-size: 12px; }
.close-button { width: 30px; height: 30px; color: #6b7280; border-radius: 7px; background: #f3f4f6; font-size: 20px; }
.primary-button { width: 100%; min-height: 38px; color: #fff; border-radius: 8px; background: #4f46e5; font-weight: 700; }
button:disabled { cursor: default; opacity: .55; }
.feedback,.empty { margin: 10px 0 0; color: #4b5563; font-size: 12px; }
ul { margin: 12px 0 0; padding: 0; list-style: none; }
li { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 11px 0; border-top: 1px solid #f0f1f3; }
.version-copy { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.version-copy strong { color: #1f2937; font-size: 13px; }
.version-copy span { overflow: hidden; color: #6b7280; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.restore-button { flex: 0 0 auto; min-height: 30px; padding: 0 10px; color: #4338ca; border-radius: 7px; background: #eef2ff; font-weight: 700; }
button:focus-visible { outline: 3px solid rgba(79,70,229,.25); outline-offset: 2px; }
.mobile { position: static; padding: 6px 12px; background: #fff; border-bottom: 1px solid #e5e7eb; }
.mobile .toggle-button { width: 100%; min-height: 36px; }
.mobile .version-panel { position: static; width: auto; max-height: 46vh; margin-top: 8px; box-shadow: none; }
@media (max-width: 390px) { .mobile { padding: 6px 10px; }.mobile .version-panel { padding: 12px; } }
</style>

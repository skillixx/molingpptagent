<template>
  <aside class="save-status" :class="[`status-${engine.status}`, { mobile }]" aria-live="polite">
    <div class="status-copy">
      <span class="status-dot" aria-hidden="true"></span>
      <span>{{ statusText }}</span>
    </div>
    <div class="actions">
      <template v-if="engine.recoveryDraft">
        <button
          type="button"
          data-testid="recover-local-draft"
          @click="engine.acceptRecovery()"
        >恢复本地稿</button>
        <button
          type="button"
          class="muted"
          data-testid="discard-local-draft"
          @click="engine.discardRecovery()"
        >忽略</button>
      </template>
      <template v-else-if="engine.conflict">
        <button
          type="button"
          data-testid="load-latest-version"
          @click="engine.loadLatest()"
        >加载最新</button>
        <button
          type="button"
          class="muted"
          data-testid="save-conflict-copy"
          @click="engine.saveAsCopy()"
        >另存副本</button>
      </template>
      <button
        v-else-if="engine.needsRetryConfirmation"
        type="button"
        data-testid="confirm-save-retry"
        @click="engine.confirmRetry()"
      >确认重试</button>
      <button
        v-else
        type="button"
        data-testid="manual-save"
        :disabled="engine.status === 'saving' || engine.status === 'saved' || engine.status === 'offline'"
        @click="engine.saveNow()"
      >{{ engine.status === 'offline' ? '等待联网' : '立即保存' }}</button>
    </div>
  </aside>
</template>

<script lang="ts" setup>
import { computed } from 'vue'

import type { PresentationAutosaveEngine } from '@/editor/presentationAutosaveEngine'


type AutosaveStatusController = Pick<
  PresentationAutosaveEngine,
  | 'status'
  | 'errorCode'
  | 'needsRetryConfirmation'
  | 'recoveryDraft'
  | 'localDraftAvailable'
  | 'conflict'
  | 'acceptRecovery'
  | 'discardRecovery'
  | 'confirmRetry'
  | 'saveNow'
  | 'loadLatest'
  | 'saveAsCopy'
>

const props = defineProps<{ engine: AutosaveStatusController; mobile?: boolean }>()

const statusText = computed(() => {
  if (props.engine.recoveryDraft) return '发现本机未保存草稿'
  if (props.engine.conflict) return `版本冲突：最新为 v${props.engine.conflict.currentVersion}`
  if (props.engine.needsRetryConfirmation) return '网络已恢复，确认后重试'
  if (!props.engine.localDraftAvailable && props.engine.status !== 'saved') {
    return '本机草稿不可用，请保持页面并联网保存'
  }
  const labels = {
    idle: '等待作品加载',
    saved: '已保存',
    dirty: '有未保存修改',
    saving: '正在保存…',
    offline: '离线草稿已保存在本机',
    error: props.engine.errorCode === 'PRESENTATION_DOCUMENT_TOO_LARGE'
      ? '作品超过10MiB，暂存于本机'
      : '保存失败，草稿仍在本机',
    conflict: '作品已在其他页面更新',
  }
  return labels[props.engine.status]
})
</script>

<style lang="scss" scoped>
.save-status { position: fixed; top: 5px; right: 104px; z-index: 70; min-height: 30px; max-width: min(520px, calc(100vw - 360px)); padding: 3px 5px 3px 10px; display: flex; align-items: center; gap: 10px; color: #4b5563; border: 1px solid #e5e7eb; border-radius: 9px; background: rgba(255,255,255,.96); box-shadow: 0 5px 18px rgba(15,23,42,.08); font-size: 12px; }
.status-copy { display: flex; align-items: center; gap: 6px; min-width: 0; }
.status-dot { width: 7px; height: 7px; flex: 0 0 auto; border-radius: 50%; background: #22c55e; }
.status-dirty .status-dot,.status-saving .status-dot { background: #f59e0b; }
.status-offline .status-dot,.status-error .status-dot { background: #ef4444; }
.actions { display: flex; gap: 4px; }
button { min-height: 25px; padding: 0 9px; color: #fff; border: 0; border-radius: 6px; background: #4f46e5; font: inherit; font-weight: 700; cursor: pointer; }
button.muted { color: #4b5563; background: #f3f4f6; }
button:disabled { color: #9ca3af; background: #f3f4f6; cursor: default; }
button:focus-visible { outline: 3px solid rgba(79,70,229,.25); outline-offset: 2px; }
.mobile { position: static; max-width: none; min-height: 42px; padding: 6px 12px; justify-content: space-between; border-width: 0 0 1px; border-radius: 0; box-shadow: none; font-size: 13px; }
@media (max-width: 1024px) and (min-width: 601px) { .save-status:not(.mobile) { right: 96px; max-width: 360px; } }
@media (max-width: 768px) and (min-width: 601px) { .save-status:not(.mobile) .status-copy span:last-child { max-width: 118px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } }
@media (max-width: 390px) { .mobile { flex-wrap: wrap; }.mobile .actions { margin-left: auto; } }
</style>

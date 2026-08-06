<template>
  <div v-if="showEditor" class="editor-state-shell">
    <!-- 持久任务生成期间保留原编辑器画面，但锁住编辑操作，完成后原位载入作品。 -->
    <div class="editor-preview" :class="{ 'is-pending': isGenerating }" :aria-hidden="isGenerating">
      <slot />
    </div>
    <aside v-if="isGenerating" class="generation-banner" data-testid="history-generating" aria-live="polite">
      <span class="spinner" aria-hidden="true"></span>
      <div class="generation-copy">
        <strong>AI 正在生成 PPT</strong>
        <span>{{ generationMessage }}</span>
      </div>
      <div class="generation-actions">
        <button type="button" class="secondary compact" data-testid="retry-history" @click="retry">刷新状态</button>
        <button type="button" class="primary compact" data-testid="back-to-works" @click="goToWorks">返回作品库</button>
      </div>
    </aside>
  </div>

  <main v-else class="load-state" :class="`state-${editorStore.loadStatus}`" aria-live="polite">
    <div v-if="editorStore.loadStatus === 'loading'" class="state-card" data-testid="history-loading">
      <span class="spinner" aria-hidden="true"></span>
      <p class="eyebrow">RESTORING / 恢复中</p>
      <h1>正在取回你的作品</h1>
      <p>正在从服务端加载当前编辑稿，请稍候。</p>
    </div>

    <div v-else-if="editorStore.loadStatus === 'not_found'" class="state-card" data-testid="history-not-found">
      <span class="state-number">404</span>
      <p class="eyebrow">NOT FOUND / 未找到</p>
      <h1>这份作品无法打开</h1>
      <p>作品可能已删除、不存在，或不属于当前账号。</p>
      <button type="button" class="primary" data-testid="back-to-works" @click="goToWorks">返回作品库</button>
    </div>

    <div v-else-if="editorStore.loadStatus === 'unavailable'" class="state-card" data-testid="history-unavailable">
      <span class="pulse-dot" aria-hidden="true"></span>
      <p class="eyebrow">NOT READY / 暂不可编辑</p>
      <h1>{{ unavailableTitle }}</h1>
      <p>{{ unavailableMessage }}</p>
      <div class="actions">
        <button type="button" class="secondary" data-testid="retry-history" @click="retry">刷新状态</button>
        <button v-if="editorStore.unavailableStatus === 'failed'" type="button" class="primary" data-testid="restart-generation" @click="goToGenerator">重新生成</button>
        <button type="button" class="primary" data-testid="back-to-works" @click="goToWorks">返回作品库</button>
      </div>
    </div>

    <div v-else class="state-card" data-testid="history-error">
      <span class="state-number">!</span>
      <p class="eyebrow">TEMPORARY ERROR / 暂时失败</p>
      <h1>作品还没有加载出来</h1>
      <p>网络或服务暂时不可用，已保留原有编辑内容。</p>
      <div class="actions">
        <button type="button" class="secondary" data-testid="retry-history" @click="retry">重新加载</button>
        <button type="button" class="primary" data-testid="back-to-works" @click="goToWorks">返回作品库</button>
      </div>
    </div>
  </main>
</template>

<script lang="ts" setup>
import { computed, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { usePresentationEditorStore } from '@/store/presentationEditor'
import { useSlidesStore } from '@/store/slides'


const route = useRoute()
const router = useRouter()
const editorStore = usePresentationEditorStore()
const slidesStore = useSlidesStore()
const hasPersistentRoute = computed(() => Object.prototype.hasOwnProperty.call(route.params, 'presentationId'))
const routePresentationId = computed(() => {
  const value = route.params.presentationId
  return typeof value === 'string' ? value : ''
})
const isGenerating = computed(() => (
  editorStore.loadStatus === 'unavailable' && editorStore.unavailableStatus === 'generating'
))
const showEditor = computed(() => !hasPersistentRoute.value || editorStore.loadStatus === 'ready' || isGenerating.value)
const previewSlideCount = computed(() => editorStore.unavailableStatus === 'generating'
  ? slidesStore.slides.filter(slide => slide.elements.length > 0).length
  : 0)
const generationMessage = computed(() => previewSlideCount.value > 0
  ? `已生成 ${previewSlideCount.value} 页，正在继续生成；全部完成后自动开放编辑。`
  : '正在准备第一页，生成后将在当前画布逐页展示。')
let statusPollTimer: number | undefined

function isWaitingForGeneration() {
  return editorStore.loadStatus === 'unavailable' && (
    editorStore.unavailableStatus === 'generating' ||
    editorStore.unavailableStatus === 'billing_pending'
  )
}

function scheduleStatusPoll() {
  window.clearTimeout(statusPollTimer)
  if (!isWaitingForGeneration()) return
  statusPollTimer = window.setTimeout(async () => {
    statusPollTimer = undefined
    await editorStore.retry()
    // 状态未变化时 Vue 的 watch 不会再次触发，因此每次请求结束后主动续约轮询。
    scheduleStatusPoll()
  }, 4000)
}

watch(routePresentationId, presentationId => {
  if (!hasPersistentRoute.value) editorStore.useLegacyMode()
  else void editorStore.load(presentationId)
}, { immediate: true })

watch(
  () => [editorStore.loadStatus, editorStore.unavailableStatus, editorStore.requestedId],
  scheduleStatusPoll,
  { immediate: true },
)

onBeforeUnmount(() => window.clearTimeout(statusPollTimer))

const unavailableTitle = computed(() => {
  if (editorStore.unavailableStatus === 'generating') return '作品正在生成'
  if (editorStore.unavailableStatus === 'billing_pending') return '作品正在等待结算'
  if (editorStore.unavailableStatus === 'failed') return '这次生成没有完成'
  return '这份作品暂时不能编辑'
})
const unavailableMessage = computed(() => {
  if (editorStore.unavailableStatus === 'generating') return '生成完成后即可从作品库继续编辑。'
  if (editorStore.unavailableStatus === 'billing_pending') return '结算结果确认前不会开放编辑，以免产生新的冲突稿。'
  if (editorStore.unavailableStatus === 'failed') return '生成服务响应超时或中断，未产生可编辑页面，请重新发起生成。'
  return '请返回作品库检查状态，或稍后再试。'
})

function retry() {
  void editorStore.retry()
}

function goToWorks() {
  void router.push({ name: 'Works' })
}

function goToGenerator() {
  void router.push({ name: 'Outline' })
}
</script>

<style lang="scss" scoped>
.editor-state-shell { position: relative; width: 100%; height: 100%; min-height: 100dvh; overflow: hidden; background: #f3f5f8; }
.editor-preview { width: 100%; height: 100%; min-height: 100dvh; }
.editor-preview.is-pending { pointer-events: none; user-select: none; filter: saturate(.72); }
.generation-banner { position: fixed; z-index: 1000; left: 50%; bottom: 28px; width: min(720px,calc(100vw - 40px)); min-height: 76px; padding: 14px 16px; box-sizing: border-box; display: flex; align-items: center; gap: 14px; transform: translateX(-50%); color: #172033; border: 1px solid rgba(37,99,235,.22); border-radius: 8px; background: rgba(255,255,255,.97); box-shadow: 0 16px 42px rgba(23,32,51,.18); }
.generation-copy { min-width: 0; display: grid; flex: 1; gap: 4px; }
.generation-copy strong { font-size: 15px; }
.generation-copy span { color: #667085; font-size: 13px; line-height: 1.5; }
.generation-actions { display: flex; gap: 8px; flex: none; }
.load-state { min-height: 100%; min-height: 100dvh; padding: 48px; box-sizing: border-box; display: grid; place-items: center; color: #25231f; background: radial-gradient(circle at 12% 16%, rgba(220,83,52,.12), transparent 28%), repeating-linear-gradient(0deg, transparent 0 39px, rgba(59,55,48,.04) 40px), #f5f1e9; }
.state-card { width: min(560px,100%); padding: 54px; box-sizing: border-box; border: 1px solid rgba(37,35,31,.13); border-radius: 20px; background: rgba(255,254,250,.96); box-shadow: 0 24px 70px rgba(55,47,36,.12); text-align: center; }
.eyebrow { margin: 18px 0 12px; color: #d95234 !important; font-size: 11px !important; font-weight: 800; letter-spacing: .18em; }
h1 { margin: 0; font: 500 clamp(30px,5vw,48px)/1.12 Georgia,'Noto Serif SC',serif; }
.state-card > p:last-of-type { margin: 18px auto 0; max-width: 420px; color: #777169; font-size: 15px; line-height: 1.8; }
.state-number { display: inline-grid; width: 70px; height: 70px; place-items: center; color: #d95234; border: 1px solid rgba(217,82,52,.3); border-radius: 50%; font: 500 25px Georgia,serif; background: rgba(217,82,52,.08); }
.spinner { display: inline-block; width: 44px; height: 44px; border: 3px solid rgba(217,82,52,.18); border-top-color: #d95234; border-radius: 50%; animation: spin .8s linear infinite; }
.pulse-dot { display: inline-block; width: 18px; height: 18px; border: 7px solid rgba(217,82,52,.16); border-radius: 50%; background: #d95234; animation: pulse 1.5s ease-in-out infinite; }
.actions { margin-top: 30px; display: flex; justify-content: center; gap: 10px; }
button { min-height: 46px; padding: 0 22px; border-radius: 9px; font: inherit; font-weight: 700; cursor: pointer; }
.primary { margin-top: 30px; color: #fff; border: 1px solid #d95234; background: #d95234; }
.actions .primary { margin-top: 0; }
.compact { min-height: 38px; margin-top: 0; padding: 0 14px; font-size: 13px; }
.secondary { color: #302d28; border: 1px solid rgba(37,35,31,.2); background: #fff; }
button:focus-visible { outline: 3px solid rgba(217,82,52,.28); outline-offset: 3px; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 50% { transform: scale(.88); opacity: .65; } }
@media (max-width: 768px) { .generation-banner { bottom: 16px; width: calc(100vw - 24px); align-items: flex-start; flex-wrap: wrap; }.generation-copy { flex-basis: calc(100% - 60px); }.generation-actions { width: 100%; justify-content: flex-end; }.load-state { padding: 28px; }.state-card { padding: 44px 34px; } }
@media (max-width: 480px) { .generation-banner { gap: 10px; }.generation-actions button { flex: 1; }.load-state { padding: 16px; }.state-card { padding: 40px 22px; border-radius: 16px; }.actions { flex-direction: column; }.actions button,.state-card > .primary { width: 100%; } }
@media (prefers-reduced-motion: reduce) { .spinner,.pulse-dot { animation: none; } }
</style>

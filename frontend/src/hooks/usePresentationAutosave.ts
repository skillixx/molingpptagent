import { onBeforeUnmount, ref, shallowReactive, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useRouter } from 'vue-router'

import { useAuthStore, usePresentationEditorStore, useSlidesStore } from '@/store'
import { PresentationAutosaveEngine, type EditablePresentationSnapshot } from '@/editor/presentationAutosaveEngine'
import { presentationApi } from '@/services/presentations'
import type { PresentationDetail } from '@/services/presentations'
import { presentationDrafts } from '@/services/presentationDrafts'


export default function usePresentationAutosave() {
  const authStore = useAuthStore()
  const editorStore = usePresentationEditorStore()
  const slidesStore = useSlidesStore()
  const router = useRouter()
  const tracking = ref(false)
  let activationEpoch = 0

  function cloneSerializable<T>(value: T): T {
    // Pinia状态是Proxy，先转为纯JSON再写入IndexedDB或网络，避免structuredClone抛DataCloneError。
    return JSON.parse(JSON.stringify(value)) as T
  }

  function currentSnapshot(): EditablePresentationSnapshot | null {
    if (!slidesStore.presentationId || slidesStore.presentationVersion === null) return null
    return {
      presentationId: slidesStore.presentationId,
      version: slidesStore.presentationVersion,
      title: slidesStore.title,
      document: {
        schemaVersion: 1,
        slides: cloneSerializable(slidesStore.slides),
        theme: cloneSerializable(slidesStore.theme),
        viewportSize: slidesStore.viewportSize,
        viewportRatio: slidesStore.viewportRatio,
      },
    }
  }

  function identityScope(): string {
    const user = authStore.user
    return user ? `app-${user.appId}-user-${user.userId}` : 'local-development-user'
  }

  // 只追踪公开状态；深层响应式会把待写稿件重新包装成Proxy，IndexedDB无法结构化克隆。
  const engine = shallowReactive(new PresentationAutosaveEngine({
    save: async snapshot => presentationApi.save(snapshot.presentationId, {
      baseVersion: snapshot.version,
      title: snapshot.title,
      document: snapshot.document,
    }),
    readDraft: (scope, presentationId) => presentationDrafts.read(scope, presentationId),
    writeDraft: (scope, snapshot) => presentationDrafts.write(scope, snapshot),
    deleteDraft: (scope, presentationId) => presentationDrafts.remove(scope, presentationId),
    isOnline: () => navigator.onLine,
    onSavedVersion: version => { slidesStore.presentationVersion = version },
    applyRecovered: snapshot => {
      // 本地草稿只能替换可编辑字段，服务端作品ID与版本仍由当前路由上下文控制。
      slidesStore.$patch({
        title: snapshot.title,
        slides: cloneSerializable(snapshot.document.slides),
        theme: { ...slidesStore.theme, ...cloneSerializable(snapshot.document.theme) },
        slideIndex: 0,
        viewportSize: snapshot.document.viewportSize,
        viewportRatio: snapshot.document.viewportRatio,
      })
    },
    reloadLatest: async presentationId => {
      await editorStore.load(presentationId)
      if (editorStore.loadStatus !== 'ready') throw new Error('latest presentation unavailable')
    },
    saveAsCopy: async snapshot => {
      const copied = await presentationApi.duplicate(
        snapshot.presentationId,
        `${snapshot.title.slice(0, 252)} 副本`,
        snapshot.document,
      )
      return { id: copied.id, currentVersion: copied.currentVersion }
    },
    onCopyCreated: presentationId => {
      void router.replace({ name: 'PresentationEditor', params: { presentationId } })
    },
  }))

  async function applyRestoredPresentation(detail: PresentationDetail) {
    // 恢复响应是新的服务端基线：暂停追踪后替换稿件、清空旧撤销栈，再重新激活保存引擎。
    const epoch = ++activationEpoch
    tracking.value = false
    engine.deactivate()
    await editorStore.replaceLoadedDetail(detail)
    const snapshot = currentSnapshot()
    if (!snapshot || epoch !== activationEpoch) return
    await engine.activate(identityScope(), snapshot)
    if (epoch === activationEpoch) tracking.value = true
  }

  watch(
    () => [editorStore.loadStatus, slidesStore.presentationId] as const,
    async ([status]) => {
      const epoch = ++activationEpoch
      tracking.value = false
      if (status !== 'ready') {
        engine.deactivate()
        return
      }
      const snapshot = currentSnapshot()
      if (!snapshot) return
      await engine.activate(identityScope(), snapshot)
      if (epoch === activationEpoch) tracking.value = true
    },
    { immediate: true },
  )

  watch(
    () => JSON.stringify({
      title: slidesStore.title,
      slides: slidesStore.slides,
      theme: slidesStore.theme,
      viewportSize: slidesStore.viewportSize,
      viewportRatio: slidesStore.viewportRatio,
    }),
    async (_next, previous) => {
      if (!tracking.value || previous === undefined || editorStore.loadStatus !== 'ready') return
      const snapshot = currentSnapshot()
      if (snapshot) await engine.markChanged(snapshot)
    },
  )

  const handleBeforeUnload = (event: BeforeUnloadEvent) => {
    if (!engine.shouldBlockLeave()) return
    event.preventDefault()
    event.returnValue = ''
  }
  const handleOnline = () => engine.handleOnline()
  window.addEventListener('beforeunload', handleBeforeUnload)
  window.addEventListener('online', handleOnline)

  onBeforeRouteLeave(() => {
    if (!engine.shouldBlockLeave()) return true
    return window.confirm('还有内容尚未保存，确定离开当前作品吗？')
  })

  onBeforeUnmount(() => {
    activationEpoch += 1
    tracking.value = false
    engine.deactivate()
    window.removeEventListener('beforeunload', handleBeforeUnload)
    window.removeEventListener('online', handleOnline)
  })

  return { engine, applyRestoredPresentation }
}

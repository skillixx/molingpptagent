import { defineStore } from 'pinia'

import { PresentationApiError, presentationApi } from '@/services/presentations'
import type { PresentationDetail, PresentationStatus } from '@/services/presentations'
import { useMainStore } from './main'
import { useSlidesStore } from './slides'
import { useSnapshotStore } from './snapshot'


export type PresentationLoadStatus = 'idle' | 'loading' | 'ready' | 'not_found' | 'unavailable' | 'error'

const SAFE_PRESENTATION_ID = /^[A-Za-z0-9_-]{1,128}$/

export const usePresentationEditorStore = defineStore('presentationEditor', {
  state: () => ({
    loadStatus: 'idle' as PresentationLoadStatus,
    requestedId: null as string | null,
    unavailableStatus: null as PresentationStatus | null,
    errorCode: null as string | null,
    loadEpoch: 0,
  }),

  actions: {
    useLegacyMode() {
      // 旧/editor继续使用内存稿；递增epoch使此前未完成的详情请求失效。
      this.loadEpoch += 1
      this.requestedId = null
      this.unavailableStatus = null
      this.errorCode = null
      this.loadStatus = 'idle'
      useSlidesStore().clearPresentationContext()
    },

    async load(presentationId: string, options: { background?: boolean } = {}) {
      const epoch = ++this.loadEpoch
      const background = options.background === true && this.requestedId === presentationId
      this.requestedId = presentationId
      this.errorCode = null
      if (!background) this.unavailableStatus = null
      if (!SAFE_PRESENTATION_ID.test(presentationId)) {
        this.loadStatus = 'not_found'
        return
      }
      // 自动轮询必须保留当前生成界面，不能每四秒切换到全屏加载态造成闪烁。
      if (!background) this.loadStatus = 'loading'

      try {
        const detail = await presentationApi.get(presentationId)
        if (epoch !== this.loadEpoch) return
        if (detail.status !== 'ready' && detail.status !== 'draft') {
          if (detail.status === 'generating' && detail.document.slides.length > 0) {
            // 生成预览只读展示；清除持久作品上下文，避免自动保存提前写回未完成作品。
            const slidesStore = useSlidesStore()
            slidesStore.replacePresentation(detail)
            slidesStore.clearPresentationContext()
          }
          this.unavailableStatus = detail.status
          this.loadStatus = 'unavailable'
          return
        }

        await this.replaceLoadedDetail(detail)
        if (epoch === this.loadEpoch) this.loadStatus = 'ready'
      }
      catch (error) {
        if (epoch !== this.loadEpoch) return
        if (background) {
          this.errorCode = error instanceof PresentationApiError
            ? error.code
            : 'PRESENTATION_REQUEST_FAILED'
          return
        }
        if (error instanceof PresentationApiError) {
          this.errorCode = error.code
          this.loadStatus = error.status === 404 ? 'not_found' : 'error'
          return
        }
        this.errorCode = 'PRESENTATION_REQUEST_FAILED'
        this.loadStatus = 'error'
      }
    },

    async retry() {
      if (this.requestedId) await this.load(this.requestedId, { background: true })
    },

    async replaceLoadedDetail(detail: PresentationDetail) {
      // 应用可信服务端详情并重建编辑上下文；调用方负责暂停自动保存追踪。
      const slidesStore = useSlidesStore()
      slidesStore.replacePresentation(detail)
      const mainStore = useMainStore()
      mainStore.setActiveElementIdList([])
      mainStore.setActiveGroupElementId('')
      mainStore.setHiddenElementIdList([])
      const snapshotStore = useSnapshotStore()
      try {
        await snapshotStore.resetSnapshotDatabase()
      }
      catch {
        // IndexedDB撤销栈是本机辅助能力；失败不能把已成功恢复的服务端作品伪装成加载失败。
        snapshotStore.setSnapshotCursor(-1)
        snapshotStore.setSnapshotLength(0)
      }
    },
  },
})

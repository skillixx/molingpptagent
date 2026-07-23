<template>
  <PresentationLoader>
  <!-- 手机端：精简视图，仅显示缩略图 + 下载/返回 -->
  <div class="mobile-editor" v-if="isMobile">
    <div class="mobile-header">
      <button class="mobile-back-btn" @click="handleMobileBack">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15,18 9,12 15,6"></polyline></svg>
        <span>{{ slidesStore.presentationId ? '作品库' : '首页' }}</span>
      </button>
      <h2 class="mobile-title">PPT 预览</h2>
      <button class="mobile-download-btn" @click="handleMobileDownload" :disabled="isGenerating">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"></path><polyline points="7,10 12,15 17,10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
        <span>下载</span>
      </button>
    </div>
    <button
      v-if="archivePending"
      class="mobile-archive-retry"
      :disabled="archiveRetrying"
      @click="retryPptxArchive"
    >
      {{ archiveRetrying ? '正在重试云端归档…' : '本地已下载，点此重试云端归档' }}
    </button>
    <PresentationAutosaveStatus v-if="slidesStore.presentationId" :engine="engine" mobile />
    <PresentationVersionPanel v-if="slidesStore.presentationId" :engine="engine" :apply-restored="applyRestoredPresentation" mobile />
    <div v-if="slidesStore.presentationId" class="mobile-basic-editor">
      <label>
        <span>作品标题</span>
        <input v-model="slidesStore.title" maxlength="255" aria-label="作品标题" />
      </label>
      <label>
        <span>当前页备注</span>
        <textarea
          :value="slidesStore.currentSlide?.remark || ''"
          rows="2"
          aria-label="当前页备注"
          @input="updateMobileRemark"
        ></textarea>
      </label>
    </div>
    <Thumbnails class="mobile-thumbnails" />
    <div v-if="isGenerating" class="mobile-loading">
      <div class="mobile-loading-spinner"></div>
      <span role="status" aria-live="polite">AI 正在生成，已完成 {{ slides.length }} 页，请耐心等待…</span>
    </div>
  </div>

  <!-- PC端：完整编辑器 -->
  <template v-else>
    <div class="pptist-editor">
      <EditorHeader class="layout-header" />
      <PresentationAutosaveStatus v-if="slidesStore.presentationId" :engine="engine" />
      <PresentationVersionPanel v-if="slidesStore.presentationId" :engine="engine" :apply-restored="applyRestoredPresentation" />
      <div class="layout-content">
        <Thumbnails class="layout-content-left" />
        <div class="layout-content-center">
          <CanvasTool class="center-top" />
          <Canvas class="center-body" :style="{ height: `calc(100% - ${remarkHeight + 40}px)` }" />
          <Remark
            class="center-bottom"
            v-model:height="remarkHeight"
            :style="{ height: `${remarkHeight}px` }"
          />
        </div>
        <Toolbar class="layout-content-right" />
      </div>
    </div>

    <SelectPanel v-if="showSelectPanel" />
    <SearchPanel v-if="showSearchPanel" />
    <NotesPanel v-if="showNotesPanel" />
    <MarkupPanel v-if="showMarkupPanel" />
    <SymbolPanel v-if="showSymbolPanel" />

    <Modal
      :visible="!!dialogForExport"
      :width="680"
      @closed="closeExportDialog()"
    >
      <ExportDialog />
    </Modal>
    <div v-if="isGenerating" class="bottom-loading">
      <span role="status" aria-live="polite">AI 正在生成，已完成 {{ slides.length }} 页，请耐心等待…</span>
    </div>
  </template>
  </PresentationLoader>
</template>

<script lang="ts" setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useMainStore, useSlidesStore } from '@/store'
import useGlobalHotkey from '@/hooks/useGlobalHotkey'
import usePasteEvent from '@/hooks/usePasteEvent'
import useExport from '@/hooks/useExport'
import message from '@/utils/message'

import EditorHeader from './EditorHeader/index.vue'
import Canvas from './Canvas/index.vue'
import CanvasTool from './CanvasTool/index.vue'
import Thumbnails from './Thumbnails/index.vue'
import Toolbar from './Toolbar/index.vue'
import Remark from './Remark/index.vue'
import ExportDialog from './ExportDialog/index.vue'
import SelectPanel from './SelectPanel.vue'
import SearchPanel from './SearchPanel.vue'
import NotesPanel from './NotesPanel.vue'
import SymbolPanel from './SymbolPanel.vue'
import MarkupPanel from './MarkupPanel.vue'
import Modal from '@/components/Modal.vue'
import PresentationLoader from './PresentationLoader.vue'
import PresentationAutosaveStatus from './PresentationAutosaveStatus.vue'
import PresentationVersionPanel from './PresentationVersionPanel.vue'
import { shouldUseMobileEditor } from './editorViewport'
import usePresentationAutosave from '@/hooks/usePresentationAutosave'

const router = useRouter()
const mainStore = useMainStore()
const slidesStore = useSlidesStore()
const { slides } = storeToRefs(slidesStore)
const { dialogForExport, showSelectPanel, showSearchPanel, showNotesPanel, showSymbolPanel, showMarkupPanel, isGenerating } = storeToRefs(mainStore)

const closeExportDialog = () => mainStore.setDialogForExport('')

const remarkHeight = ref(40)
const isMobile = ref(shouldUseMobileEditor(navigator.userAgent, window.innerWidth))
const { engine, applyRestoredPresentation } = usePresentationAutosave()

function updateEditorViewport() {
  isMobile.value = shouldUseMobileEditor(navigator.userAgent, window.innerWidth)
}

onMounted(() => window.addEventListener('resize', updateEditorViewport))
onBeforeUnmount(() => window.removeEventListener('resize', updateEditorViewport))

const { exportPPTX, archivePending, archiveRetrying, retryPptxArchive } = useExport()

const handleMobileBack = () => {
  // 历史作品返回作品库；旧生成流程继续返回原大纲入口。
  void router.push(slidesStore.presentationId ? { name: 'Works' } : { name: 'Outline' })
}

// 手机端下载
const handleMobileDownload = async () => {
  try {
    await exportPPTX(slides.value, true, true)
    message.success('PPTX 导出成功')
  } catch {
    // 导出库异常可能携带作品内容，只展示稳定文案，不向控制台输出原始对象。
    message.error('导出失败，请重试')
  }
}

function updateMobileRemark(event: Event) {
  slidesStore.updateSlide({ remark: (event.target as HTMLTextAreaElement).value })
}

// 生命周期钩子必须在setup阶段固定注册；窄屏与横屏切换后仍保留键盘/粘贴能力。
useGlobalHotkey()
usePasteEvent()
</script>

<style lang="scss" scoped>
/* ========== 手机端样式 ========== */
.mobile-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.mobile-back-btn,
.mobile-download-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  padding: 8px 12px;
  border-radius: 8px;
  transition: all 0.2s;
}

.mobile-back-btn {
  color: #64748b;
  &:hover { background: #f1f5f9; }
}

.mobile-download-btn {
  color: #fff;
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
  &:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.mobile-title {
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin: 0;
}

.mobile-thumbnails {
  flex: 1;
  overflow-y: auto;

  :deep(.add-slide) { display: none; }
  :deep(.page-number) { display: none; }

  :deep(.thumbnail-list) {
    padding: 12px 0;
  }

  :deep(.thumbnail-item) {
    padding: 8px 16px;
    justify-content: center;

    .label { display: none; }
    .thumbnail {
      width: 100% !important;
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    }
  }
}

.mobile-loading {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  border-radius: 100px;
  font-size: 14px;
  z-index: 100;
  white-space: nowrap;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.mobile-loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: mobile-spin 0.8s linear infinite;
}

.mobile-archive-retry {
  width: calc(100% - 28px);
  margin: 8px 14px 0;
  padding: 9px 12px;
  border: 1px solid #f0b44d;
  border-radius: 8px;
  background: #fff8e8;
  color: #8a5200;
  font-size: 12px;
  cursor: pointer;
  &:disabled { opacity: .6; cursor: wait; }
}

.mobile-basic-editor { padding: 10px 14px; display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1.4fr); gap: 10px; border-bottom: 1px solid #e5e7eb; background: #fff; }
.mobile-basic-editor label { min-width: 0; display: grid; gap: 4px; color: #64748b; font-size: 11px; font-weight: 700; }
.mobile-basic-editor input,.mobile-basic-editor textarea { width: 100%; min-height: 36px; box-sizing: border-box; padding: 7px 9px; color: #334155; border: 1px solid #cbd5e1; border-radius: 7px; background: #fff; font: inherit; font-size: 13px; line-height: 1.35; resize: vertical; }
.mobile-basic-editor input:focus,.mobile-basic-editor textarea:focus { outline: 3px solid rgba(99,102,241,.18); border-color: #6366f1; }
@media (max-width: 390px) { .mobile-basic-editor { grid-template-columns: 1fr; } }

@keyframes mobile-spin {
  to { transform: rotate(360deg); }
}

/* ========== PC端样式 ========== */
.pptist-editor {
  height: 100%;
}
.layout-header {
  height: 40px;
}
.layout-content {
  height: calc(100% - 40px);
  display: flex;
}
.layout-content-left {
  width: 160px;
  height: 100%;
  flex-shrink: 0;
}
.layout-content-center {
  width: calc(100% - 160px - 260px);

  .center-top {
    height: 40px;
  }
}
.layout-content-right {
  width: 260px;
  height: 100%;
}

.bottom-loading {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 20px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  border-radius: 8px;
  z-index: 1000;
}
</style>

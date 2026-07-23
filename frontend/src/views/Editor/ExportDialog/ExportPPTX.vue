<template>
  <div class="export-pptx-dialog">
    <section class="file-location" data-testid="export-file-location" aria-label="生成文件位置">
      <div><strong>生成文件：</strong><span>{{ title }}.pptx</span></div>
      <div><strong>下载位置：</strong><span>浏览器默认下载目录</span></div>
      <div v-if="presentationId"><strong>云端路径：</strong><span>我的作品 / {{ title }} / 导出历史</span></div>
      <div v-else class="temporary-tip"><strong>作品状态：</strong><span>临时作品，当前不会出现在用户工作台</span></div>
    </section>
    <div class="configs">
      <div class="row">
        <div class="title">导出范围：</div>
        <RadioGroup
          class="config-item"
          v-model:value="rangeType"
        >
          <RadioButton style="width: 33.33%;" value="all">全部</RadioButton>
          <RadioButton style="width: 33.33%;" value="current">当前页</RadioButton>
          <RadioButton style="width: 33.33%;" value="custom">自定义</RadioButton>
        </RadioGroup>
      </div>
      <div class="row" v-if="rangeType === 'custom'">
        <div class="title" :data-range="`（${range[0]} ~ ${range[1]}）`">自定义范围：</div>
        <Slider
          class="config-item"
          range
          :min="1"
          :max="slides.length"
          :step="1"
          v-model:value="range"
        />
      </div>
      <div class="row">
        <div class="title">忽略音频/视频：</div>
        <div class="config-item">
          <Switch v-model:value="ignoreMedia" v-tooltip="'导出时默认忽略音视频，若您的幻灯片中存在音视频元素，且希望将其导出到PPTX文件中，可选择关闭【忽略音视频】选项，但要注意这将会大幅增加导出用时。'" />
        </div>
      </div>
      <div class="row">
        <div class="title">覆盖默认母版：</div>
        <div class="config-item">
          <Switch v-model:value="masterOverwrite" />
        </div>
      </div>

      <div class="tip" v-if="!ignoreMedia">
        提示：1. 支持导出格式：avi、mp4、mov、wmv、mp3、wav；2. 跨域资源无法导出。
      </div>
    </div>
    <div class="btns">
      <Button class="btn export" type="primary" @click="exportPPTX(selectedSlides, masterOverwrite, ignoreMedia)"><IconDownload /> 导出 PPTX</Button>
      <Button v-if="archivePending" class="btn retry" :disabled="archiveRetrying" @click="retryPptxArchive">
        {{ archiveRetrying ? '重试中…' : '重试归档' }}
      </Button>
      <Button class="btn close" @click="emit('close')">关闭</Button>
    </div>
    <p v-if="archivePending" class="archive-tip" role="status">本地文件已保存，云端归档尚未完成。</p>

    <section v-if="presentationId" class="history" aria-label="PPTX导出历史">
      <div class="history-title">
        <strong>历史归档</strong>
        <button type="button" @click="loadHistory" :disabled="historyLoading">刷新</button>
      </div>
      <p v-if="historyError" class="history-empty">历史记录加载失败，可点击刷新重试。</p>
      <p v-else-if="!historyLoading && !history.length" class="history-empty">暂无已归档的PPTX</p>
      <button
        v-for="item in history"
        :key="item.id"
        type="button"
        class="history-item"
        @click="downloadHistory(item)"
      >
        <span>版本 v{{ item.presentationVersion }}</span>
        <small>{{ new Date(item.createdAt).toLocaleString() }}</small>
        <span>再次下载</span>
      </button>
    </section>

    <FullscreenSpin :loading="exporting" tip="正在导出..." />
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { saveAs } from 'file-saver'
import { useSlidesStore } from '@/store'
import useExport from '@/hooks/useExport'
import { downloadArchivedPptx, listPptxExports, type ExportRecord } from '@/services/exports'
import message from '@/utils/message'

import FullscreenSpin from '@/components/FullscreenSpin.vue'
import Switch from '@/components/Switch.vue'
import Slider from '@/components/Slider.vue'
import Button from '@/components/Button.vue'
import RadioButton from '@/components/RadioButton.vue'
import RadioGroup from '@/components/RadioGroup.vue'

const emit = defineEmits<{
  (event: 'close'): void
}>()

const { slides, currentSlide, presentationId, title } = storeToRefs(useSlidesStore())

const { exportPPTX, exporting, archivePending, archiveRetrying, retryPptxArchive } = useExport()

const rangeType = ref<'all' | 'current' | 'custom'>('all')
const range = ref<[number, number]>([1, slides.value.length])
const masterOverwrite = ref(true)
const ignoreMedia = ref(true)
const history = ref<ExportRecord[]>([])
const historyLoading = ref(false)
const historyError = ref(false)

const loadHistory = async () => {
  if (!presentationId.value || historyLoading.value) return
  historyLoading.value = true
  historyError.value = false
  try { history.value = await listPptxExports(presentationId.value) }
  catch { historyError.value = true }
  finally { historyLoading.value = false }
}

const downloadHistory = async (item: ExportRecord) => {
  try { await downloadArchivedPptx(item, `${title.value}-v${item.presentationVersion}.pptx`, saveAs) }
  catch { message.error('历史PPTX下载失败，请刷新后重试') }
}

onMounted(loadHistory)

const selectedSlides = computed(() => {
  if (rangeType.value === 'all') return slides.value
  if (rangeType.value === 'current') return [currentSlide.value]
  return slides.value.filter((item, index) => {
    const [min, max] = range.value
    return index >= min - 1 && index <= max - 1
  })
})
</script>

<style lang="scss" scoped>
.export-pptx-dialog {
  height: 100%;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  flex-direction: column;
  position: relative;
  overflow-y: auto;
  box-sizing: border-box;
  padding: 12px 0;
}
.file-location {
  width: min(100%, 430px);
  box-sizing: border-box;
  padding: 12px 14px;
  border: 1px solid #dfe4f2;
  border-radius: 10px;
  background: #f7f9ff;
  color: #59637a;
  font-size: 12px;
  line-height: 1.8;

  div {
    display: flex;
    gap: 8px;
    min-width: 0;
  }
  strong {
    flex: 0 0 64px;
    color: #35405a;
  }
  span {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .temporary-tip { color: #9a6518; }
}
.configs {
  width: min(100%, 350px);
  min-height: 220px;
  flex: 1 1 260px;
  display: flex;
  flex-direction: column;
  justify-content: center;

  .row {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 25px;
  }

  .title {
    width: 100px;
    position: relative;

    &::after {
      content: attr(data-range);
      position: absolute;
      top: 20px;
      left: 0;
    }
  }
  .config-item {
    flex: 1;
  }

  .tip {
    font-size: 12px;
    color: #aaa;
    line-height: 1.8;
    margin-top: 10px;
  }
}
.btns {
  width: min(100%, 430px);
  height: 64px;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  align-items: center;

  .export {
    flex: 1;
  }
  .close {
    width: 100px;
    margin-left: 10px;
  }
  .retry {
    width: 110px;
    margin-left: 10px;
  }
}

@media (max-width: 560px) {
  .file-location { padding: 10px 12px; }
  .file-location div { display: grid; grid-template-columns: 64px minmax(0, 1fr); }
}
.archive-tip {
  margin: -12px 16px 12px;
  color: #9a5b00;
  font-size: 12px;
  text-align: center;
}
.history {
  width: min(100% - 32px, 430px);
  max-height: 150px;
  overflow: auto;
  border-top: 1px solid #ececec;
  padding-top: 10px;
  flex-shrink: 0;
}
.history-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.history-title button { border: 0; background: transparent; color: #536dfe; cursor: pointer; }
.history-empty { margin: 10px 0; color: #888; font-size: 12px; text-align: center; }
.history-item {
  width: 100%; display: grid; grid-template-columns: 70px 1fr 70px; gap: 8px;
  align-items: center; padding: 8px; border: 0; border-radius: 6px; background: #f7f8fa;
  color: #333; cursor: pointer; text-align: left;
  & + & { margin-top: 6px; }
  small { color: #777; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  span:last-child { color: #536dfe; text-align: right; }
}

@media (max-width: 768px) {
  .configs { width: min(100% - 32px, 350px); }
  .btns { height: auto; padding: 12px 16px; flex-wrap: wrap; gap: 8px; }
  .btns .retry, .btns .close { width: auto; margin-left: 0; flex: 1; }
}

@media (max-width: 390px) {
  .configs .row { align-items: flex-start; margin-bottom: 18px; }
  .configs .title { width: 92px; }
  .btns .export { flex-basis: 100%; }
  .history-item { grid-template-columns: 58px 1fr 62px; font-size: 12px; }
}
</style>

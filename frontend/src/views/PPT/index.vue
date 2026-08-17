<template>
  <div class="aippt-page">
    <!-- 全局背景：渐变 + 网格 -->
    <div class="page-bg" aria-hidden="true">
      <div class="bg-blob b1"></div>
      <div class="bg-blob b2"></div>
      <div class="grid"></div>
    </div>

    <div class="aippt-dialog">
      <!-- 头部：标题/说明 居中、层级清晰 -->
      <header class="header" role="banner">
        <div class="header-content">
          <h1 class="title">PPTAgent</h1>
          <p class="subtitle">从下方挑选合适的模板，开始生成 PPT</p>
          <div class="header-decoration" aria-hidden="true">
            <div class="decoration-dot"></div>
            <div class="decoration-dot"></div>
            <div class="decoration-dot"></div>
          </div>
        </div>
      </header>

      <section class="select-template" aria-label="模板选择">
        <div v-if="isOutlineFromFile" class="generate-option">
          <Checkbox v-model:value="generateFromUploadedFile">根据上传的文件生成PPT</Checkbox>
          <Checkbox v-model:value="generateFromWebSearch">使用网络搜索生成PPT</Checkbox>
        </div>

        <aside
          v-if="loading && persistentGenerationEnabled"
          class="generation-status"
          data-testid="generation-status"
        >
          <div class="generation-status__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 3a9 9 0 1 0 9 9"></path>
              <path d="M12 7v5l3 2"></path>
            </svg>
          </div>
          <div class="generation-status__body">
            <div class="generation-status__heading">
              <div>
                <span class="generation-status__eyebrow">生成流程已启动</span>
                <h2>正在创建云端任务</h2>
              </div>
              <span class="elapsed" data-testid="generation-elapsed" aria-hidden="true">已等待 {{ generationElapsedLabel }}</span>
            </div>
            <p
              class="generation-status__hint"
              data-testid="generation-hint"
              role="status"
              aria-live="polite"
            >{{ generationHint }}</p>

            <ol class="generation-steps" data-testid="generation-steps" aria-label="生成进度">
              <li class="complete">
                <i aria-hidden="true">✓</i>
                <span><b>模板已确认</b><small>{{ selectedTemplateName }}</small></span>
              </li>
              <li class="active" aria-current="step">
                <i aria-hidden="true">2</i>
                <span><b>创建云端任务</b><small>正在校验身份并保存生成请求</small></span>
              </li>
              <li>
                <i aria-hidden="true">3</i>
                <span><b>AI 后台生成</b><small>任务创建后可在编辑器或作品库查看</small></span>
              </li>
            </ol>

            <div class="generation-progress" aria-hidden="true"><i></i></div>
            <div class="generation-status__footer">
              <span>{{ generationDestinationHint }}</span>
              <button
                type="button"
                class="destination-button"
                :aria-pressed="generationDestination === 'works'"
                data-testid="generation-destination"
                @click="toggleGenerationDestination"
              >
                {{ generationDestinationButton }}
              </button>
            </div>
          </div>
        </aside>

        <aside
          v-if="navigationFailed"
          class="generation-status generation-status--success"
          data-testid="generation-navigation-fallback"
        >
          <div class="generation-status__icon" aria-hidden="true">✓</div>
          <div class="generation-status__body">
            <div class="generation-status__heading">
              <div>
                <span class="generation-status__eyebrow">云端任务已创建</span>
                <h2>自动跳转未完成</h2>
              </div>
            </div>
            <p class="generation-status__hint" role="status" aria-live="polite">
              PPT 已在后台正常生成，你可以手动打开编辑器，或前往作品库稍后查看。
            </p>
            <div class="generation-fallback-actions">
              <button type="button" class="destination-button" @click="openCreatedPresentation">
                打开编辑器
              </button>
              <button type="button" class="destination-button destination-button--secondary" @click="openWorks">
                前往作品库
              </button>
            </div>
          </div>
        </aside>

        <div class="templates-container">
          <div class="templates">
            <div
              class="template-card"
              :class="{ selected: selectedTemplate === template.id }"
              v-for="template in templates"
              :key="template.id"
              @click="!loading && (selectedTemplate = template.id)"
            >
              <div class="template-image">
                <img :src="template.cover" :alt="template.name" />
                <div class="overlay">
                  <div class="check-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="20,6 9,17 4,12"></polyline>
                    </svg>
                  </div>
                </div>
              </div>
              <div class="template-info">
                <span class="template-name">{{ template.name || '经典模板' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="actions">
          <Button class="btn btn-primary" type="primary" :disabled="loading || !selectedTemplate" @click="createPPT()">
            <span>{{ generationButtonLabel }}</span>
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12,6 12,12 16,14"></polyline>
            </svg>
          </Button>
          <Button class="btn btn-secondary" :disabled="loading" @click="$router.back()">
            <span>返回大纲</span>
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15,18 9,12 15,6"></polyline>
            </svg>
          </Button>
        </div>
      </section>
    </div>

    
  </div>
</template>

<script lang="ts" setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import api from '@/services'
import useAIPPT from '@/hooks/useAIPPT'
import useAddSlidesOrElements from '@/hooks/useAddSlidesOrElements'
import useSlideHandler from '@/hooks/useSlideHandler'
import type { AIPPTSlide } from '@/types/AIPPT'
import type { Slide, SlideTheme } from '@/types/slides'
import { useMainStore, useSlidesStore } from '@/store'
import Button from '@/components/Button.vue'
import Checkbox from '@/components/Checkbox.vue'
import { isPC } from '@/utils/common'
import message from '@/utils/message'
import { authFrontendConfig } from '@/services/authConfig'
import { PresentationApiError, presentationApi } from '@/services/presentations'
import {
  assertCompleteSlideGeneration,
  expectedSlideCountFromOutline,
  GenerationIncompleteError,
} from '@/services/generationStream'

const route = useRoute()
const router = useRouter()
const mainStore = useMainStore()
const slideStore = useSlidesStore()
const { templates } = storeToRefs(slideStore)
const { sessionId, isOutlineFromFile, generateFromUploadedFile, generateFromWebSearch } =
  storeToRefs(mainStore)

const { AIPPTGenerator, presetImgPool } = useAIPPT()
const { addSlidesFromDataToEnd } = useAddSlidesOrElements()
const { isEmptySlide } = useSlideHandler()

const outline = ref(route.query.outline as string)
const language = ref(route.query.language as string)
const model = ref(route.query.model as string)
const style = ref('通用')
const img = ref('')
const selectedTemplate = ref<string>('')
const persistentRequestId = ref('')
const persistentGenerationEnabled = authFrontendConfig.ssoEnabled
const generationElapsedSeconds = ref(0)
const generationDestination = ref<'editor' | 'works'>('editor')
const createdPresentationId = ref('')
const navigationFailed = ref(false)
let generationTimer: number | undefined
let componentActive = true

onMounted(async () => {
  await slideStore.fetchTemplates()
  selectedTemplate.value = templates.value?.[0]?.id || ''
})
const loading = ref(false)

const selectedTemplateName = computed(() => (
  templates.value.find(template => template.id === selectedTemplate.value)?.name || '已选模板'
))
const generationElapsedLabel = computed(() => {
  const minutes = Math.floor(generationElapsedSeconds.value / 60)
  const seconds = generationElapsedSeconds.value % 60
  return minutes > 0 ? `${minutes} 分 ${seconds} 秒` : `${seconds} 秒`
})
const generationHint = computed(() => {
  if (generationElapsedSeconds.value < 8) {
    return '正在提交生成请求并等待服务端确认，通常只需要几秒。'
  }
  if (generationElapsedSeconds.value < 30) {
    return '请求已经发出，正在等待服务端确认。请勿重复提交，收到确认后会自动跳转。'
  }
  return '等待时间比平时更长，目前尚未收到服务端确认。请检查网络；若请求失败，可使用同一请求安全重试。'
})
const generationButtonLabel = computed(() => {
  if (!loading.value) return '生成PPT'
  if (!persistentGenerationEnabled) return '正在生成…'
  return `正在创建任务 · ${generationElapsedLabel.value}`
})
const generationDestinationHint = computed(() => generationDestination.value === 'works'
  ? '任务创建后将前往作品库，生成会继续进行。'
  : '任务创建后将自动进入编辑器查看实时结果。')
const generationDestinationButton = computed(() => generationDestination.value === 'works'
  ? '改为创建后打开编辑器'
  : '任务创建后去作品库')

const stopGenerationTimer = () => {
  if (generationTimer !== undefined) window.clearInterval(generationTimer)
  generationTimer = undefined
}

const startGenerationTimer = () => {
  stopGenerationTimer()
  generationElapsedSeconds.value = 0
  generationTimer = window.setInterval(() => {
    generationElapsedSeconds.value += 1
  }, 1000)
}

const toggleGenerationDestination = () => {
  generationDestination.value = generationDestination.value === 'editor' ? 'works' : 'editor'
}

onBeforeUnmount(() => {
  componentActive = false
  stopGenerationTimer()
})

const openCreatedPresentation = async () => {
  if (!createdPresentationId.value) return
  await router.push({
    name: 'PresentationEditor',
    params: { presentationId: createdPresentationId.value },
  })
}

const openWorks = async () => {
  await router.push({ name: 'Works' })
}

watch([outline, language, model, selectedTemplate], () => {
  // 用户修改生成意图后必须使用新的幂等键；网络重试则继续复用原键。
  persistentRequestId.value = ''
})

const createRequestId = () => {
  if (persistentRequestId.value) return persistentRequestId.value
  persistentRequestId.value = typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `ppt-${Date.now()}-${Math.random().toString(36).slice(2)}`
  return persistentRequestId.value
}

const presentationTitle = () => {
  const heading = outline.value.match(/^#\s+(.+)$/m)?.[1]?.trim()
  return (heading || 'AI 演示文稿').slice(0, 255)
}

const persistentErrorMessage = (error: unknown) => {
  if (!(error instanceof PresentationApiError)) return '生成任务创建失败，请稍后重试'
  if (error.code === 'BILLING_ENTITLEMENT_REQUIRED') return '请从墨灵的 PPT 资产入口重新进入后再生成'
  // 来源配置错误需要明确提示，避免用户把服务端安全拒绝误认为生成模型故障。
  if (error.code === 'AUTH_ORIGIN_REJECTED') return '当前访问地址未获服务端信任，请联系管理员检查应用地址配置'
  if (error.status === 429) return '生成请求过于频繁，请稍后再试'
  return '生成任务创建失败，请稍后重试'
}

const createPersistentPPT = async () => {
  let result: Awaited<ReturnType<typeof presentationApi.create>>
  try {
    result = await presentationApi.create({
      title: presentationTitle(),
      content: outline.value,
      language: language.value || 'chinese',
      model: model.value || 'deepseek-chat',
      templateId: selectedTemplate.value,
      generateFromUploadedFile: generateFromUploadedFile.value,
      generateFromWebSearch: generateFromWebSearch.value,
    }, createRequestId())
  }
  catch (error) {
    mainStore.setGenerating(false)
    message.error(persistentErrorMessage(error))
    return
  }
  finally {
    stopGenerationTimer()
    loading.value = false
  }

  // 用户等待期间可能主动离开页面，此时任务可以继续，但不应再强制把用户拉回。
  if (!componentActive) return

  createdPresentationId.value = result.presentation.id
  mainStore.setGenerating(false)
  message.success(result.reused ? '已恢复原生成任务' : '生成任务已创建')

  try {
    if (generationDestination.value === 'works') await openWorks()
    else await openCreatedPresentation()
  }
  catch {
    // 任务创建与页面导航是两个结果；导航失败时必须保留成功事实并给出手动入口。
    navigationFailed.value = true
    message.warning('生成任务已创建，但页面自动跳转失败，请手动选择下一步')
  }
}

const createPPT = async () => {
  if (!selectedTemplate.value) return
  navigationFailed.value = false
  createdPresentationId.value = ''
  mainStore.setGenerating(true)
  loading.value = true

  slideStore.resetSlides()

  // 墨灵登录态必须走持久任务，确保 reserve 发生在 Agent 调用之前并由 Worker 统一收尾。
  if (authFrontendConfig.ssoEnabled) {
    startGenerationTimer()
    await createPersistentPPT()
    return
  }

  const expectedSlideCount = expectedSlideCountFromOutline(outline.value)
  let receivedSlideCount = 0

  try {
    const stream = await api.AIPPT_Content({
      content: outline.value,
      language: language.value,
      style: style.value,
      model: model.value,
      generateFromUploadedFile: generateFromUploadedFile.value,
      generateFromWebSearch: generateFromWebSearch.value,
      sessionId: sessionId.value, // 后端已兼容；或改名 user_id
    })
    if (!stream.ok || !stream.body) {
      throw new Error('PPT_STREAM_REQUEST_FAILED')
    }

    // 初始化图片池（mock 兜底）
    const mockImgs = await api.getMockData('imgs')
    presetImgPool(mockImgs)

    const templateData = await api.getFileData(selectedTemplate.value)
    const templateSlides: Slide[] = templateData.slides
    const templateTheme: SlideTheme = templateData.theme
    slideStore.setTheme(templateTheme)

    // 后端已接受生成请求并且模板可用后再进入编辑器，失败时留在当前页便于重试。
    await router.push(`/editor?session_id=${sessionId.value}${isPC() ? '&isPc=true' : ''}`)

    // 根据模板的宽度和高度动态设置 viewportSize 和 viewportRatio
    if (templateData.width && templateData.height) {
      slideStore.setViewportSize(templateData.width)
      slideStore.setViewportRatio(templateData.height / templateData.width)
    }

    const reader: ReadableStreamDefaultReader<Uint8Array> = stream.body.getReader()
    const decoder = new TextDecoder('utf-8')

    let buffer = '' // 用来跨 chunk 缓存

    const processEvent = (evt: string) => {
      // evt 是一条完整的 SSE 事件（不包含尾部空行）
      // 兼容多行 data:，拼接起来
      const dataLines = evt
        .split('\n')
        .filter(l => l.startsWith('data:'))
        .map(l => l.slice(5).trimStart()) // 去掉 'data: '

      const payload = dataLines.join('\n')

      if (!payload) return
      if (payload === '[DONE]') {
        assertCompleteSlideGeneration(receivedSlideCount, expectedSlideCount)
        loading.value = false
        mainStore.setAIPPTDialogState(false)
        mainStore.setGenerating(false)
        return 'DONE'
      }

      // 某些模型可能会包围 ```json``` fence，这里做容错
      const jsonText = payload.replace(/```json|```/g, '').trim()

      try {
        const slide: AIPPTSlide = JSON.parse(jsonText)

        // 处理后端返回的图片池
        if (slide.images?.length) {
          const backendImages = slide.images.map((img: any) => ({
            id: img.id || Math.random().toString(),
            src: img.src,
            width: img.width || 1920,
            height: img.height || 1080
          }))
          presetImgPool(backendImages)
        }

        // 用模板生成并插入
        const slideGenerator = AIPPTGenerator(templateSlides, [slide])
        for (const generatedSlide of slideGenerator) {
          if (isEmptySlide.value) {
            slideStore.setSlides([generatedSlide])
          }
          else {
            addSlidesFromDataToEnd([generatedSlide])
          }
          receivedSlideCount += 1
        }
      }
      catch (e) {
        // 如果这条不是完整 JSON（比如后端按“文本片段”流），可以考虑改成累积 JSON 方案
        console.warn('解析 JSON 失败，跳过本条事件：', e, jsonText)
      }
    }

    const pump = (): any =>
      reader.read().then(({ done, value }) => {
        if (done) {
          // 读流结束：兜底把缓冲里最后一条尝试处理
          if (buffer.trim()) {
            const status = processEvent(buffer)
            buffer = ''
            if (status === 'DONE') return
          }
          throw new Error('PPT_STREAM_INCOMPLETE')
        }

        buffer += decoder.decode(value, { stream: true })

        // SSE 以空行分隔事件：\n\n（注意：可能是 \r\n\r\n）
        const parts = buffer.split(/\r?\n\r?\n/)
        // 最后一段可能是不完整，留在缓冲
        buffer = parts.pop() || ''

        for (const evt of parts) {
          const status = processEvent(evt)
          if (status === 'DONE') {
            reader.cancel()
            return
          }
        }

        return pump()
      })

    await pump()
  }
  catch (error) {
    loading.value = false
    mainStore.setGenerating(false)
    if (error instanceof GenerationIncompleteError) {
      message.error(`PPT仅生成 ${error.received}/${error.expected} 页，已识别为不完整，请返回模板页重试`)
    }
    else {
      message.error('PPT生成中断，请返回模板页重试')
    }
  }
}
</script>

<style lang="scss" scoped>
/* 页面容器，提供稳定的全屏背景承载 */
.aippt-page {
  position: relative;
  min-height: 100dvh;
  overflow-x: hidden;
}

/* 背景层 */
.page-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: radial-gradient(1200px 600px at 10% -10%, rgba(102, 126, 234, 0.12), rgba(0, 0, 0, 0) 60%),
    radial-gradient(1000px 600px at 90% 110%, rgba(118, 75, 162, 0.12), rgba(0, 0, 0, 0) 60%),
    linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  pointer-events: none;
}
.page-bg .grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(15, 23, 42, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.04) 1px, transparent 1px);
  background-size: 32px 32px, 32px 32px;
  mask-image: radial-gradient(60% 50% at 50% 50%, #000 60%, transparent 100%);
}
.bg-blob {
  position: absolute;
  filter: blur(40px);
  opacity: 0.6;
}
.bg-blob.b1 { width: 520px; height: 520px; left: -160px; top: -160px; background: #c7d2fe; }
.bg-blob.b2 { width: 420px; height: 420px; right: -120px; bottom: -120px; background: #e9d5ff; }

/* 主内容卡片 */
.aippt-dialog {
  position: relative;
  z-index: 1;
  margin: 0 auto;
  padding: 40px 24px 32px;
  max-width: 1160px;
  box-sizing: border-box;
}

/* 头部区块：居中布局 */
.header {
  text-align: center;
  margin-bottom: 28px;
  .title {
    font-weight: 900;
    font-size: 36px;
    margin: 0 0 10px 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    letter-spacing: -0.5px;
    line-height: 1.15;
  }
  .subtitle {
    color: #475569;
    font-size: 16px;
    margin: 0 auto;
    font-weight: 500;
    line-height: 1.6;
    max-width: 680px;
  }
  .header-decoration {
    margin: 14px auto 0;
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: center;
    .decoration-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      opacity: 0.7; animation: pulse 2s ease-in-out infinite;
      &:nth-child(2) { animation-delay: 0.25s; }
      &:nth-child(3) { animation-delay: 0.5s; }
    }
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.2); opacity: 1; }
}

/* 模板区域 */
.select-template {
  .generation-status {
    margin-bottom: 20px;
    padding: 22px 24px;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 18px;
    border: 1px solid rgba(59, 130, 246, 0.24);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 18px 45px rgba(37, 99, 235, 0.14);

    &__icon {
      width: 48px;
      height: 48px;
      display: grid;
      place-items: center;
      color: #fff;
      border-radius: 15px;
      background: linear-gradient(135deg, #3b82f6, #4f46e5);
      box-shadow: 0 9px 20px rgba(59, 130, 246, 0.3);

      svg {
        width: 25px;
        height: 25px;
        animation: status-spin 1.6s linear infinite;
      }
    }

    &__body { min-width: 0; }
    &__heading {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;

      h2 {
        margin: 3px 0 0;
        color: #172033;
        font-size: 20px;
        line-height: 1.3;
      }
    }
    &__eyebrow {
      color: #2563eb;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.12em;
    }
    .elapsed {
      flex: 0 0 auto;
      padding: 6px 10px;
      color: #334155;
      border: 1px solid #dbeafe;
      border-radius: 999px;
      background: #eff6ff;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }
    &__hint {
      margin: 10px 0 16px;
      color: #64748b;
      font-size: 13px;
      line-height: 1.65;
    }
    &__footer {
      margin-top: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      color: #64748b;
      font-size: 12px;
    }

    &--success {
      border-color: rgba(34, 197, 94, 0.3);
      box-shadow: 0 18px 45px rgba(22, 163, 74, 0.12);

      .generation-status__icon {
        font-size: 24px;
        font-weight: 800;
        background: linear-gradient(135deg, #22c55e, #15803d);
        box-shadow: 0 9px 20px rgba(34, 197, 94, 0.25);
      }
      .generation-status__eyebrow { color: #15803d; }
    }
  }

  .generation-fallback-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .generation-steps {
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    list-style: none;

    li {
      min-width: 0;
      padding: 11px 12px;
      display: flex;
      align-items: center;
      gap: 9px;
      color: #94a3b8;
      border: 1px solid #e2e8f0;
      border-radius: 11px;
      background: #f8fafc;

      i {
        width: 24px;
        height: 24px;
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        border-radius: 50%;
        background: #e2e8f0;
        font-size: 11px;
        font-style: normal;
        font-weight: 800;
      }
      span { min-width: 0; }
      b, small { display: block; }
      b { color: #64748b; font-size: 12px; }
      small { margin-top: 2px; overflow: hidden; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }

      &.complete {
        color: #15803d;
        border-color: #bbf7d0;
        background: #f0fdf4;
        i { color: #fff; background: #22c55e; }
        b { color: #166534; }
      }
      &.active {
        color: #2563eb;
        border-color: #bfdbfe;
        background: #eff6ff;
        box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.08);
        i { color: #fff; background: #3b82f6; animation: active-step 1.2s ease-in-out infinite; }
        b { color: #1d4ed8; }
      }
    }
  }

  .generation-progress {
    height: 4px;
    margin-top: 14px;
    overflow: hidden;
    border-radius: 999px;
    background: #dbeafe;

    i {
      width: 38%;
      height: 100%;
      display: block;
      border-radius: inherit;
      background: linear-gradient(90deg, #60a5fa, #4f46e5);
      animation: task-progress 1.7s ease-in-out infinite;
    }
  }

  .destination-button {
    min-height: 36px;
    padding: 0 13px;
    flex: 0 0 auto;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 9px;
    background: #eff6ff;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
    transition: 0.2s ease;

    &:hover { border-color: #60a5fa; background: #dbeafe; transform: translateY(-1px); }
    &:focus-visible { outline: 3px solid rgba(59, 130, 246, 0.24); outline-offset: 2px; }

    &--secondary {
      color: #475569;
      border-color: #cbd5e1;
      background: #fff;

      &:hover { border-color: #94a3b8; background: #f8fafc; }
    }
  }

  .templates-container {
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: saturate(120%) blur(2px);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
  }

  .templates {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 18px;
  }

  .template-card {
    position: relative;
    border: 2px solid #e2e8f0;
    border-radius: 14px;
    overflow: hidden;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    background: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 26px -4px rgba(0, 0, 0, 0.12);
      border-color: #cbd5e1;
    }

    &.selected {
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15), 0 12px 28px -6px rgba(59, 130, 246, 0.25);
      .overlay { opacity: 1; visibility: visible; }
      .template-info { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: #fff; }
    }

    .template-image {
      position: relative; aspect-ratio: 16/9; overflow: hidden;
      img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s ease; }
      .overlay {
        position: absolute; inset: 0; background: rgba(59, 130, 246, 0.18);
        display: flex; align-items: center; justify-content: center;
        opacity: 0; visibility: hidden; transition: all 0.25s ease;
        .check-icon {
          width: 32px; height: 32px; color: #fff; background: #3b82f6; border-radius: 50%;
          display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
          svg { width: 16px; height: 16px; }
        }
      }
    }

    .template-info {
      padding: 12px 14px; background: #f8fafc; transition: all 0.25s ease;
      .template-name { font-size: 14px; font-weight: 700; color: inherit; }
    }

    &:hover .template-image img { transform: scale(1.045); }
  }

  .generate-option {
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: saturate(120%) blur(2px);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    color: #475569;
    font-size: 14px;
  }

  .actions {
    display: flex; justify-content: center; gap: 14px; align-items: center; margin-top: 18px;
    .btn {
      min-width: 148px; height: 48px; display: flex; align-items: center; justify-content: center; gap: 8px;
      font-weight: 700; font-size: 14px; border-radius: 12px; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative; overflow: hidden;
      &:disabled { opacity: 0.6; cursor: not-allowed; filter: grayscale(10%); }
      .btn-icon { width: 18px; height: 18px; transition: transform 0.25s ease; }
      &.btn-primary {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); border: none; color: #fff;
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.38);
        &:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(59, 130, 246, 0.5); .btn-icon { transform: rotate(90deg); } }
        &:active:not(:disabled) { transform: translateY(0); }
      }
      &.btn-secondary {
        background: #fff; border: 2px solid #e2e8f0; color: #64748b;
        &:hover:not(:disabled) {
          border-color: #cbd5e1; background: #f8fafc; color: #475569; transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08); .btn-icon { transform: translateX(-2px); }
        }
        &:active:not(:disabled) { transform: translateY(0); }
      }
    }
  }
}

@keyframes status-spin { to { transform: rotate(360deg); } }
@keyframes active-step { 50% { box-shadow: 0 0 0 5px rgba(59, 130, 246, 0.15); } }
@keyframes task-progress { from { transform: translateX(-110%); } to { transform: translateX(270%); } }

/* 响应式 */
@media (max-width: 768px) {
  .aippt-dialog { padding: 24px 16px; }
  .header { .title { font-size: 28px; } .subtitle { font-size: 14px; } }
  .select-template {
    .generation-status {
      padding: 18px;
      grid-template-columns: 1fr;
      gap: 13px;

      &__icon { width: 42px; height: 42px; }
      &__heading h2 { font-size: 18px; }
      &__footer { align-items: stretch; flex-direction: column; }
    }
    .generation-steps { grid-template-columns: 1fr; }
    .generation-steps li small { white-space: normal; }
    .destination-button { width: 100%; min-height: 42px; }
    .generation-fallback-actions { flex-direction: column; }
    .templates-container { padding: 16px; }
    .templates { grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .template-card .template-info { padding: 8px 10px; .template-name { font-size: 12px; } }
    .actions { flex-direction: column; gap: 12px; .btn { width: 100%; max-width: 320px; } }
  }
}
@media (max-width: 480px) {
  .aippt-dialog { padding: 16px 12px; }
  .header .title { font-size: 24px; }
  .select-template {
    .generation-status {
      margin-inline: -2px;
      padding: 16px;

      &__heading {
        align-items: flex-start;
        flex-direction: column;
        gap: 9px;
      }
      .elapsed { align-self: flex-start; }
    }
    .templates-container { padding: 12px; }
    .templates { grid-template-columns: 1fr; gap: 10px; }
  }
}

@media (prefers-reduced-motion: reduce) {
  .generation-status__icon svg,
  .generation-steps li.active i,
  .generation-progress i,
  .header-decoration .decoration-dot {
    animation: none !important;
  }
}
</style>

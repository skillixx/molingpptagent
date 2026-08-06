<template>
  <main class="works-shell">
    <header class="topbar">
      <a class="brand" href="/works" aria-label="墨灵演示作品首页">
        <span class="brand-mark"><IconSlideTwo /></span>
        <span><b>墨灵演示</b><small>AI PRESENTATION</small></span>
      </a>
      <div class="topbar-actions">
        <button class="icon-button" type="button" data-testid="refresh-works" aria-label="刷新作品" @click="store.load()">
          <IconRefresh :class="{ spinning: store.status === 'loading' }" />
        </button>
        <button class="primary-button" type="button" data-testid="new-presentation" @click="goToGenerator">
          <IconPlus /> 新建演示
        </button>
      </div>
    </header>

    <section class="hero">
      <div>
        <p class="eyebrow">WORKSPACE / 作品库</p>
        <h1>让每一次灵感，<em>都有迹可循。</em></h1>
        <p class="hero-copy">在这里继续编辑、整理并管理你的 AI 演示文稿。</p>
      </div>
      <div class="work-count" aria-label="作品总数"><strong>{{ store.total }}</strong><span>份作品</span></div>
    </section>

    <section class="toolbar" aria-label="作品搜索与筛选">
      <label class="search-box">
        <IconSearch />
        <input
          v-model="store.search"
          data-testid="works-search"
          type="search"
          maxlength="100"
          placeholder="搜索作品名称…"
          aria-label="搜索作品名称"
        />
        <button v-if="store.search" type="button" aria-label="清空搜索" @click="clearSearch"><IconCloseSmall /></button>
      </label>

      <div class="desktop-filters" aria-label="按状态筛选">
        <button
          v-for="option in statusOptions"
          :key="option.value"
          type="button"
          :class="{ active: store.statusFilter === option.value }"
          @click="selectStatus(option.value)"
        >{{ option.label }}</button>
      </div>

      <label class="sort-select">
        <span>排序</span>
        <select v-model="store.sort" aria-label="作品排序" @change="store.applyFilters()">
          <option value="updated_desc">最近更新</option>
          <option value="updated_asc">最早更新</option>
          <option value="created_desc">最近创建</option>
          <option value="title_asc">名称排序</option>
        </select>
      </label>

      <button class="mobile-filter-button" data-testid="mobile-filter" type="button" @click="filterDrawerOpen = true">
        <IconListView /> 筛选
        <span v-if="store.statusFilter !== 'all'" class="filter-dot"></span>
      </button>
    </section>

    <p v-if="store.feedback" class="feedback" role="status" aria-live="polite">{{ store.feedback }}</p>

    <section v-if="store.status === 'loading'" class="works-grid" aria-label="正在加载作品">
      <article v-for="index in 8" :key="index" class="work-card skeleton-card" data-testid="works-skeleton">
        <div class="skeleton thumbnail"></div><div class="skeleton line wide"></div><div class="skeleton line"></div>
      </article>
    </section>

    <section v-else-if="store.status === 'error'" class="state-panel error-panel" data-testid="works-error">
      <span class="state-icon"><IconAttention /></span>
      <h2>作品暂时没有加载出来</h2>
      <p>{{ store.errorMessage }}</p>
      <button class="secondary-button" type="button" data-testid="retry-load" @click="store.load()"><IconRefresh /> 重新加载</button>
    </section>

    <section v-else-if="store.items.length === 0" class="state-panel empty-panel" data-testid="works-empty">
      <div class="empty-visual" aria-hidden="true"><span></span><i></i><b>+</b></div>
      <p class="eyebrow">YOUR FIRST STORY</p>
      <h2>{{ store.search || store.statusFilter !== 'all' ? '没有找到匹配的作品' : '还没有演示文稿' }}</h2>
      <p>{{ store.search || store.statusFilter !== 'all' ? '试试其他关键词或清除筛选条件。' : '从一个主题开始，让 AI 帮你搭好第一份演示。' }}</p>
      <button v-if="store.search || store.statusFilter !== 'all'" class="secondary-button" type="button" @click="resetFilters">清除筛选</button>
      <button v-else class="primary-button" type="button" data-testid="new-presentation-empty" @click="goToGenerator"><IconPlus /> 创建第一份演示</button>
    </section>

    <section v-else class="works-grid" aria-label="作品列表">
      <article v-for="(work, index) in store.items" :key="work.id" class="work-card" :class="`status-${work.status}`">
        <button class="thumbnail-button" type="button" :data-testid="`open-${work.id}`" :aria-label="`打开${work.title}`" @click="handlePrimary(work)">
          <div class="thumbnail-art" :class="`art-${index % 4}`">
            <span class="mini-kicker">MOLING / DECK</span>
            <strong>{{ thumbnailTitle(work.title) }}</strong>
            <div class="mini-lines"><i></i><i></i><i></i></div>
            <b>{{ String(work.slideCount).padStart(2, '0') }}</b>
          </div>
          <span class="status-pill" :class="work.status"><i></i>{{ statusMeta[work.status].label }}</span>
          <span v-if="work.status === 'generating'" class="generation-line"><i></i></span>
        </button>
        <div class="card-content">
          <div class="card-heading">
            <button type="button" class="title-button" @click="handlePrimary(work)">{{ work.title }}</button>
            <span class="version">v{{ work.currentVersion }}</span>
          </div>
          <p class="card-meta"><span>{{ work.slideCount }} 页</span><i></i><span>{{ formatDate(work.updatedAt) }}</span></p>
          <div class="card-actions">
            <button type="button" class="open-button" @click="handlePrimary(work)">{{ statusMeta[work.status].action }}</button>
            <button type="button" :data-testid="`duplicate-${work.id}`" aria-label="复制作品" @click="duplicateWork(work.id)"><IconCopy /></button>
            <button type="button" :data-testid="`delete-${work.id}`" aria-label="删除作品" @click="askDelete(work)"><IconDelete /></button>
          </div>
        </div>
      </article>
    </section>

    <nav v-if="store.total > store.pageSize" class="pagination" aria-label="作品分页">
      <button type="button" :disabled="store.page <= 1 || store.status === 'loading'" @click="store.goToPage(store.page - 1)"><IconLeft /> 上一页</button>
      <span>第 <b>{{ store.page }}</b> / {{ store.pageCount }} 页</span>
      <button type="button" :disabled="!store.hasMore || store.status === 'loading'" @click="store.goToPage(store.page + 1)">下一页 <IconRight /></button>
    </nav>

    <Transition name="fade">
      <div v-if="deleteTarget" class="dialog-layer" role="presentation" @mousedown.self="deleteTarget = null">
        <section class="dialog-card delete-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
          <span class="danger-icon"><IconDelete /></span>
          <h2 id="delete-title">删除“{{ deleteTarget.title }}”？</h2>
          <p>删除后将不再出现在作品库中。当前版本不会立即物理清除。</p>
          <p v-if="deleteError" class="form-error" role="alert">{{ deleteError }}</p>
          <div class="dialog-actions">
            <button class="secondary-button" type="button" :disabled="deleting" @click="deleteTarget = null">取消</button>
            <button class="danger-button" type="button" data-testid="confirm-delete" :disabled="deleting" @click="confirmDelete">{{ deleting ? '删除中…' : '确认删除' }}</button>
          </div>
        </section>
      </div>
    </Transition>

    <div class="drawer-layer" :class="{ open: filterDrawerOpen }" :aria-hidden="!filterDrawerOpen" data-testid="filter-drawer" @mousedown.self="filterDrawerOpen = false">
      <aside class="filter-drawer" aria-label="手机筛选面板">
        <div><h2>筛选作品</h2><button type="button" data-testid="close-filter" aria-label="关闭筛选" @click="filterDrawerOpen = false"><IconClose /></button></div>
        <button v-for="option in statusOptions" :key="option.value" type="button" :class="{ active: store.statusFilter === option.value }" @click="selectStatus(option.value, true)"><span>{{ option.label }}</span><IconCheck v-if="store.statusFilter === option.value" /></button>
      </aside>
    </div>
  </main>
</template>

<script lang="ts" setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { icons } from '@/plugins/icon'
import { usePresentationsStore } from '@/store/presentations'
import type { PresentationStatus, PresentationSummary } from '@/services/presentations'
import type { WorksStatusFilter } from '@/store/presentations'


const {
  IconAttention, IconCheck, IconClose, IconCloseSmall, IconCopy, IconDelete,
  IconLeft, IconListView, IconPlus, IconRefresh, IconRight, IconSearch, IconSlideTwo,
} = icons
const router = useRouter()
const store = usePresentationsStore()
const filterDrawerOpen = ref(false)
const deleteTarget = ref<PresentationSummary | null>(null)
const deleting = ref(false)
const deleteError = ref('')
let searchTimer: number | undefined

const statusOptions: { value: WorksStatusFilter; label: string }[] = [
  { value: 'all', label: '全部' }, { value: 'ready', label: '可编辑' },
  { value: 'generating', label: '生成中' }, { value: 'draft', label: '草稿' },
  { value: 'failed', label: '失败' }, { value: 'billing_pending', label: '待结算' },
]
const statusMeta: Record<PresentationStatus, { label: string; action: string }> = {
  ready: { label: '可编辑', action: '继续编辑' },
  generating: { label: '生成中', action: '查看进度' },
  draft: { label: '草稿', action: '继续编辑' },
  failed: { label: '生成失败', action: '重新开始' },
  billing_pending: { label: '待结算', action: '查看状态' },
}

watch(() => store.search, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => void store.applyFilters(), 300)
})
onMounted(() => void store.load())
onBeforeUnmount(() => window.clearTimeout(searchTimer))

function selectStatus(status: WorksStatusFilter, closeDrawer = false) {
  store.statusFilter = status
  if (closeDrawer) filterDrawerOpen.value = false
  void store.applyFilters()
}
function clearSearch() { store.search = '' }
function resetFilters() {
  store.search = ''
  store.statusFilter = 'all'
  void store.applyFilters()
}
function openWork(id: string) {
  void router.push({ name: 'PresentationEditor', params: { presentationId: id } })
}
function handlePrimary(work: PresentationSummary) {
  if (work.status === 'failed') {
    void router.push({ name: 'Outline', query: { source: work.id } })
    return
  }
  if (work.status === 'generating') {
    store.feedback = '作品正在生成，可稍后刷新查看进度。'
    return
  }
  if (work.status === 'billing_pending') {
    store.feedback = '作品正在等待结算，暂时不能编辑。'
    return
  }
  openWork(work.id)
}
function goToGenerator() {
  // 作品库只负责管理；新建统一回到原 PPTAgent 交互生成流程。
  void router.push({ name: 'Outline' })
}
async function duplicateWork(id: string) {
  try { await store.duplicate(id) }
  catch { store.feedback = '复制失败，请稍后重试。' }
}
function askDelete(work: PresentationSummary) {
  deleteError.value = ''
  deleteTarget.value = work
}
async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await store.remove(deleteTarget.value.id)
    deleteTarget.value = null
  }
  catch { deleteError.value = '删除失败，请稍后重试。' }
  finally { deleting.value = false }
}
function thumbnailTitle(title: string) { return title.length > 14 ? `${title.slice(0, 14)}…` : title }
function formatDate(value: string) {
  const date = new Date(value)
  const today = new Date()
  const sameYear = date.getFullYear() === today.getFullYear()
  return new Intl.DateTimeFormat('zh-CN', sameYear
    ? { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
    : { year: 'numeric', month: 'short', day: 'numeric' }).format(date)
}
</script>

<style lang="scss" scoped>
.works-shell {
  --ink: #24231f;
  --muted: #74716a;
  --paper: #f4f2ed;
  --card: #fffefb;
  --accent: #d65234;
  --accent-dark: #ae3b23;
  min-height: 100vh;
  padding: 0 clamp(20px, 5vw, 72px) 64px;
  color: var(--ink);
  background:
    radial-gradient(circle at 82% 4%, rgba(214, 82, 52, .09), transparent 25%),
    linear-gradient(rgba(36, 35, 31, .026) 1px, transparent 1px),
    var(--paper);
  background-size: auto, 100% 48px, auto;
  overflow-x: clip;
}
button, input, textarea, select { font: inherit; }
button { cursor: pointer; }
.topbar {
  width: min(1320px, 100%);
  min-height: 82px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(36, 35, 31, .12);
}
.brand { display: inline-flex; align-items: center; gap: 12px; color: var(--ink); }
.brand-mark { width: 38px; height: 38px; display: grid; place-items: center; color: #fff; background: var(--accent); border-radius: 10px 2px 10px 2px; font-size: 20px; box-shadow: 4px 4px 0 #272621; }
.brand b { display: block; font-size: 17px; letter-spacing: .08em; }
.brand small { display: block; margin-top: 2px; color: var(--muted); font-size: 8px; letter-spacing: .18em; }
.topbar-actions { display: flex; gap: 10px; align-items: center; }
.primary-button, .secondary-button, .danger-button, .icon-button {
  min-height: 42px; padding: 0 18px; display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  border: 1px solid transparent; border-radius: 9px; font-weight: 650; transition: .18s ease;
}
.primary-button { color: #fff; background: var(--accent); box-shadow: 0 8px 20px rgba(214,82,52,.18); }
.primary-button:hover { background: var(--accent-dark); transform: translateY(-1px); }
.secondary-button { color: var(--ink); border-color: rgba(36,35,31,.18); background: #fff; }
.danger-button { color: #fff; background: #b63d32; }
.icon-button { width: 42px; padding: 0; color: var(--ink); border-color: rgba(36,35,31,.14); background: rgba(255,255,255,.6); }
button:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible { outline: 3px solid rgba(214,82,52,.28); outline-offset: 2px; }
button:disabled { cursor: wait; opacity: .55; }
.spinning { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.hero { width: min(1320px, 100%); margin: 0 auto; padding: clamp(44px, 7vw, 88px) 0 42px; display: flex; align-items: end; justify-content: space-between; gap: 40px; }
.eyebrow { margin: 0 0 13px; color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: .18em; }
.hero h1 { max-width: 760px; margin: 0; font-family: Georgia, 'Songti SC', serif; font-size: clamp(38px, 5vw, 72px); font-weight: 500; line-height: 1.08; letter-spacing: -.045em; }
.hero h1 em { color: var(--accent); font-style: normal; white-space: nowrap; }
.hero-copy { margin: 20px 0 0; color: var(--muted); font-size: 15px; }
.work-count { flex: 0 0 auto; padding: 0 0 6px 26px; border-left: 1px solid rgba(36,35,31,.2); }
.work-count strong { display: block; font-family: Georgia, serif; font-size: 42px; line-height: .95; }
.work-count span { display: block; margin-top: 8px; color: var(--muted); font-size: 12px; letter-spacing: .12em; }
.toolbar { width: min(1320px, 100%); margin: 0 auto 28px; display: flex; align-items: center; gap: 12px; }
.search-box { width: min(340px, 30vw); height: 44px; padding: 0 13px; display: flex; align-items: center; gap: 9px; border: 1px solid rgba(36,35,31,.14); border-radius: 9px; background: rgba(255,255,255,.72); }
.search-box:focus-within { border-color: var(--accent); background: #fff; box-shadow: 0 0 0 3px rgba(214,82,52,.08); }
.search-box input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; }
.search-box button { padding: 3px; display: grid; border: 0; background: transparent; }
.desktop-filters { display: flex; align-items: center; gap: 4px; padding: 4px; border: 1px solid rgba(36,35,31,.12); border-radius: 9px; background: rgba(255,255,255,.55); }
.desktop-filters button { min-height: 34px; padding: 0 11px; color: var(--muted); border: 0; border-radius: 6px; background: transparent; font-size: 13px; }
.desktop-filters button.active { color: #fff; background: var(--ink); }
.sort-select { margin-left: auto; display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; }
.sort-select select { min-height: 40px; padding: 0 28px 0 10px; border: 1px solid rgba(36,35,31,.14); border-radius: 8px; background: #fff; }
.mobile-filter-button { display: none; }
.feedback { width: min(1320px,100%); min-height: 22px; margin: -16px auto 18px; color: #805328; font-size: 13px; }
.works-grid { width: min(1320px, 100%); margin: 0 auto; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: clamp(16px, 2vw, 26px); }
.work-card { min-width: 0; overflow: hidden; border: 1px solid rgba(36,35,31,.11); border-radius: 13px; background: var(--card); box-shadow: 0 4px 0 rgba(36,35,31,.04); transition: transform .2s ease, box-shadow .2s ease; }
.work-card:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(46,42,34,.1); }
.thumbnail-button { width: 100%; aspect-ratio: 16 / 9; padding: 12px; position: relative; display: block; overflow: hidden; border: 0; background: #dedbd3; text-align: left; }
.thumbnail-art { width: 100%; height: 100%; padding: 10% 9%; position: relative; overflow: hidden; color: #f8f4e9; background: #27302c; box-shadow: 0 4px 14px rgba(0,0,0,.13); }
.thumbnail-art::after { content: ''; position: absolute; width: 48%; aspect-ratio: 1; right: -12%; bottom: -35%; border: 1px solid currentColor; border-radius: 50%; opacity: .45; box-shadow: 0 0 0 15px transparent, 0 0 0 16px currentColor, 0 0 0 32px transparent, 0 0 0 33px currentColor; }
.art-1 { color: #25211f; background: #e8b94d; }
.art-2 { color: #fff; background: #bd4e37; }
.art-3 { color: #f6eee0; background: #303c62; }
.mini-kicker { display: block; font-size: clamp(5px, .55vw, 8px); letter-spacing: .18em; opacity: .72; }
.thumbnail-art strong { width: 74%; display: block; margin-top: 8%; font-family: Georgia, 'Songti SC', serif; font-size: clamp(12px, 1.35vw, 22px); line-height: 1.2; }
.thumbnail-art > b { position: absolute; left: 9%; bottom: 9%; font: 500 clamp(18px,2.2vw,34px)/1 Georgia,serif; opacity: .7; }
.mini-lines { width: 28%; margin-top: 8%; display: grid; gap: 4px; }
.mini-lines i { height: 2px; background: currentColor; opacity: .5; }
.mini-lines i:nth-child(2) { width: 72%; }.mini-lines i:nth-child(3) { width: 43%; }
.status-pill { position: absolute; top: 20px; right: 20px; padding: 5px 8px; display: inline-flex; align-items: center; gap: 5px; color: #3f423e; background: rgba(255,255,255,.9); border-radius: 999px; font-size: 10px; font-weight: 700; backdrop-filter: blur(8px); }
.status-pill i { width: 6px; height: 6px; border-radius: 50%; background: #59a36a; }
.status-pill.generating i { background: #d89035; animation: pulse 1.2s infinite; }.status-pill.failed i { background: #c94a42; }.status-pill.billing_pending i { background: #765ab7; }.status-pill.draft i { background: #8b8981; }
@keyframes pulse { 50% { opacity: .25; transform: scale(.7); } }
.generation-line { position: absolute; left: 12px; right: 12px; bottom: 12px; height: 3px; overflow: hidden; background: rgba(255,255,255,.25); }
.generation-line i { width: 35%; height: 100%; display: block; background: #fff; animation: progress 1.4s infinite ease-in-out; }
@keyframes progress { from { transform: translateX(-100%); } to { transform: translateX(390%); } }
.card-content { padding: 17px 17px 14px; }
.card-heading { display: flex; align-items: start; gap: 8px; }
.title-button { min-width: 0; padding: 0; flex: 1; overflow: hidden; color: var(--ink); border: 0; background: transparent; font-size: 15px; font-weight: 700; text-align: left; text-overflow: ellipsis; white-space: nowrap; }
.version { padding: 2px 5px; color: var(--muted); background: #f0eee8; border-radius: 4px; font-size: 9px; }
.card-meta { margin: 8px 0 14px; display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 11px; }
.card-meta i { width: 3px; height: 3px; border-radius: 50%; background: #b3b0a9; }
.card-actions { padding-top: 11px; display: flex; gap: 6px; border-top: 1px solid rgba(36,35,31,.08); }
.card-actions button { width: 34px; height: 32px; display: grid; place-items: center; color: var(--muted); border: 0; border-radius: 6px; background: transparent; }
.card-actions button:hover { color: var(--ink); background: #f0eee8; }
.card-actions .open-button { width: auto; padding: 0 11px; margin-right: auto; color: var(--accent); background: rgba(214,82,52,.08); font-size: 12px; font-weight: 700; }
.state-panel { width: min(760px, 100%); min-height: 390px; margin: 18px auto; padding: 48px 24px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.state-panel h2 { margin: 10px 0; font: 500 clamp(27px,3vw,38px)/1.2 Georgia,'Songti SC',serif; }.state-panel > p:not(.eyebrow) { max-width: 430px; margin: 0 0 24px; color: var(--muted); line-height: 1.7; }
.state-icon { width: 58px; height: 58px; display: grid; place-items: center; color: #a64035; border-radius: 50%; background: #f4deda; font-size: 25px; }
.empty-visual { width: 150px; height: 112px; margin-bottom: 30px; position: relative; transform: rotate(-3deg); border: 1px solid rgba(36,35,31,.25); background: #fff; box-shadow: 10px 10px 0 #d9d4c9; }
.empty-visual span { position: absolute; inset: 16px 16px auto; height: 8px; background: var(--accent); }.empty-visual i { position: absolute; width: 65px; height: 45px; left: 16px; bottom: 18px; background: #252b28; }.empty-visual b { position: absolute; right: 18px; bottom: 12px; color: var(--accent); font: 42px/1 Georgia; }
.skeleton-card { min-height: 278px; padding: 12px; }.skeleton { border-radius: 6px; background: linear-gradient(90deg,#e5e1d9 25%,#f2efe9 45%,#e5e1d9 65%); background-size: 300% 100%; animation: shimmer 1.4s infinite; }.skeleton.thumbnail { aspect-ratio: 16/9; }.skeleton.line { width: 50%; height: 11px; margin: 12px 5px; }.skeleton.line.wide { width: 78%; margin-top: 18px; }
@keyframes shimmer { to { background-position: -150% 0; } }
.pagination { width: min(1320px,100%); margin: 34px auto 0; display: flex; align-items: center; justify-content: center; gap: 20px; color: var(--muted); font-size: 12px; }.pagination button { min-height: 38px; padding: 0 13px; display: flex; align-items: center; gap: 5px; border: 1px solid rgba(36,35,31,.14); border-radius: 8px; background: #fff; }
.dialog-layer { position: fixed; z-index: 4500; inset: 0; padding: 20px; display: grid; place-items: center; background: rgba(31,29,25,.48); backdrop-filter: blur(8px); }
.dialog-card { width: min(520px,100%); padding: clamp(25px,4vw,42px); position: relative; border: 1px solid rgba(255,255,255,.5); border-radius: 16px; background: #fffefb; box-shadow: 0 28px 80px rgba(20,18,15,.25); }
.dialog-card h2 { margin: 0 0 8px; font: 500 30px/1.2 Georgia,'Songti SC',serif; }.dialog-card > p:not(.eyebrow,.form-error) { margin: 0 0 24px; color: var(--muted); line-height: 1.6; }
.dialog-card label { margin-top: 17px; display: grid; gap: 8px; font-size: 12px; font-weight: 700; }.dialog-card input,.dialog-card textarea { width: 100%; box-sizing: border-box; padding: 12px 13px; border: 1px solid rgba(36,35,31,.17); border-radius: 8px; outline: 0; background: #fff; resize: vertical; }.dialog-card textarea { line-height: 1.6; }
.dialog-close { position: absolute; top: 16px; right: 16px; width: 34px; height: 34px; display: grid; place-items: center; border: 0; border-radius: 50%; background: #f0eee8; }.dialog-actions { margin-top: 25px; display: flex; justify-content: flex-end; gap: 10px; }.form-error { margin: 12px 0 0; color: #a13930; font-size: 12px; }
.delete-dialog { text-align: center; }.danger-icon { width: 58px; height: 58px; margin: 0 auto 18px; display: grid; place-items: center; color: #b33d32; border-radius: 50%; background: #f4deda; font-size: 24px; }.delete-dialog .dialog-actions { justify-content: center; }
.drawer-layer { display: none; }
.fade-enter-active,.fade-leave-active { transition: opacity .18s ease; }.fade-enter-from,.fade-leave-to { opacity: 0; }
@media (max-width: 1199px) { .works-grid { grid-template-columns: repeat(3,minmax(0,1fr)); }.desktop-filters button { padding: 0 8px; }.mini-kicker { font-size: 6px; } }
@media (max-width: 960px) {
  .works-shell { padding-inline: 32px; }.works-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }.desktop-filters { display: none; }.mobile-filter-button { min-height: 40px; padding: 0 12px; position: relative; display: inline-flex; align-items: center; gap: 7px; border: 1px solid rgba(36,35,31,.14); border-radius: 8px; background: #fff; }.filter-dot { width: 7px; height: 7px; position: absolute; top: 6px; right: 6px; border-radius: 50%; background: var(--accent); }.search-box { width: auto; flex: 1; }.drawer-layer { position: fixed; z-index: 4600; inset: 0; display: block; visibility: hidden; background: rgba(31,29,25,.35); opacity: 0; transition: .2s; }.drawer-layer.open { visibility: visible; opacity: 1; }.filter-drawer { width: min(360px,88vw); height: 100%; margin-left: auto; padding: 26px; box-sizing: border-box; display: flex; flex-direction: column; gap: 7px; background: #fffefb; transform: translateX(100%); transition: transform .25s ease; }.drawer-layer.open .filter-drawer { transform: none; }.filter-drawer > div { margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; }.filter-drawer h2 { margin: 0; font: 500 27px Georgia,serif; }.filter-drawer > div button { width: 36px; height: 36px; display: grid; place-items: center; border: 0; border-radius: 50%; background: #efede7; }.filter-drawer > button { min-height: 48px; padding: 0 14px; display: flex; align-items: center; justify-content: space-between; color: var(--muted); border: 0; border-radius: 8px; background: transparent; text-align: left; }.filter-drawer > button.active { color: var(--accent); background: rgba(214,82,52,.08); font-weight: 700; }
}
@media (max-width: 600px) {
  .works-shell { padding: 0 16px 44px; background-size: auto,100% 40px,auto; }.topbar { min-height: 68px; }.brand small { display: none; }.brand-mark { width: 34px; height: 34px; }.topbar-actions { gap: 6px; }.topbar-actions .primary-button { min-width: 42px; width: 42px; padding: 0; font-size: 0; }.topbar-actions .primary-button :deep(svg) { font-size: 18px; }.hero { padding: 42px 0 28px; align-items: start; }.hero h1 { font-size: 40px; }.hero-copy { font-size: 13px; }.work-count { padding-left: 14px; }.work-count strong { font-size: 30px; }.work-count span { font-size: 9px; }.toolbar { margin-bottom: 20px; flex-wrap: wrap; }.search-box { order: 1; flex-basis: calc(100% - 104px); }.mobile-filter-button { order: 2; }.sort-select { order: 3; width: 100%; justify-content: flex-end; }.sort-select select { flex: 1; }.works-grid { grid-template-columns: 1fr; gap: 17px; }.thumbnail-art strong { font-size: 21px; }.mini-kicker { font-size: 7px; }.thumbnail-art > b { font-size: 31px; }.card-content { padding: 16px; }.state-panel { min-height: 360px; }.dialog-layer { padding: 12px; align-items: end; }.dialog-card { max-height: calc(100vh - 24px); padding: 28px 20px 22px; overflow-y: auto; border-radius: 18px 18px 8px 8px; }.dialog-actions { position: sticky; bottom: -22px; margin-inline: -20px; padding: 14px 20px 0; background: #fffefb; }.dialog-actions button { flex: 1; }.pagination { gap: 9px; }.pagination button { padding: 0 9px; }.pagination span { font-size: 10px; }
}
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; } }
</style>

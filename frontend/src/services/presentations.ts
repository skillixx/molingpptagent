import type { Slide, SlideTheme } from '@/types/slides'


export type PresentationStatus = 'draft' | 'generating' | 'ready' | 'failed' | 'billing_pending'
export type PresentationSort = 'updated_desc' | 'updated_asc' | 'created_desc' | 'title_asc'
export type CheckpointReason = 'manual' | 'ai' | 'export' | 'periodic'
export type StoredCheckpointReason = CheckpointReason | 'restore'

export interface PresentationSummary {
  id: string
  title: string
  status: PresentationStatus
  currentVersion: number
  slideCount: number
  templateId: string | null
  thumbnailFileId: string | null
  createdAt: string
  updatedAt: string
}

export interface PresentationListQuery {
  page: number
  pageSize: number
  search?: string
  status?: PresentationStatus
  sort: PresentationSort
}

export interface PresentationListResult {
  items: PresentationSummary[]
  page: number
  pageSize: number
  total: number
  hasMore: boolean
}

export interface PresentationDocument {
  schemaVersion: 1
  slides: Slide[]
  theme: Partial<SlideTheme>
  viewportSize: number
  viewportRatio: number
}

export interface PresentationDetail extends PresentationSummary {
  document: PresentationDocument
  generationTaskId?: string | null
  generationProgress?: number | null
  generationErrorCode?: string | null
}

export interface SavePresentationInput {
  baseVersion: number
  title: string
  document: PresentationDocument
}

export interface PresentationConflictSummary {
  title: string
  currentVersion: number
  updatedAt: string
}

export interface PresentationVersionSummary {
  id: string
  version: number
  reason: StoredCheckpointReason
  createdAt: string
  contentSha256: string
  uncompressedBytes: number
}

export interface PresentationVersionListResult {
  items: PresentationVersionSummary[]
  total: number
}

export interface CreatePresentationInput {
  title: string
  content: string
  language?: string
  model?: string
  templateId?: string | null
  generateFromUploadedFile?: boolean
  generateFromWebSearch?: boolean
}

export interface SaveDraftPresentationInput {
  title: string
  templateId?: string | null
  document: PresentationDocument
}

export class PresentationApiError extends Error {
  status: number
  code: string
  latest: PresentationConflictSummary | null

  constructor(
    status: number,
    code = 'PRESENTATION_REQUEST_FAILED',
    latest: PresentationConflictSummary | null = null,
  ) {
    // 禁止把服务端正文、请求内容或网络异常拼接到浏览器错误中。
    super('作品请求失败')
    this.name = 'PresentationApiError'
    this.status = status
    this.code = code
    this.latest = latest
  }
}

const statusValues = new Set<PresentationStatus>([
  'draft', 'generating', 'ready', 'failed', 'billing_pending',
])

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new PresentationApiError(502)
  return value as Record<string, unknown>
}

function integer(value: unknown, minimum = 0): number {
  if (!Number.isInteger(value) || Number(value) < minimum) throw new PresentationApiError(502)
  return Number(value)
}

function nullableString(value: unknown): string | null {
  if (value === null) return null
  if (typeof value !== 'string') throw new PresentationApiError(502)
  return value
}

function parseSummary(value: unknown): PresentationSummary {
  const data = record(value)
  if (
    typeof data.id !== 'string' || !data.id ||
    typeof data.title !== 'string' || !data.title ||
    typeof data.status !== 'string' || !statusValues.has(data.status as PresentationStatus) ||
    typeof data.created_at !== 'string' || Number.isNaN(Date.parse(data.created_at)) ||
    typeof data.updated_at !== 'string' || Number.isNaN(Date.parse(data.updated_at))
  ) throw new PresentationApiError(502)
  return {
    id: data.id,
    title: data.title,
    status: data.status as PresentationStatus,
    currentVersion: integer(data.current_version, 1),
    slideCount: integer(data.slide_count),
    templateId: nullableString(data.template_id),
    thumbnailFileId: nullableString(data.thumbnail_file_id),
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  }
}

const checkpointReasons = new Set<StoredCheckpointReason>([
  'manual', 'ai', 'export', 'periodic', 'restore',
])

function parseVersionSummary(value: unknown): PresentationVersionSummary {
  const data = record(value)
  if (
    typeof data.id !== 'string' || !data.id ||
    typeof data.reason !== 'string' || !checkpointReasons.has(data.reason as StoredCheckpointReason) ||
    typeof data.created_at !== 'string' || Number.isNaN(Date.parse(data.created_at)) ||
    typeof data.content_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(data.content_sha256)
  ) throw new PresentationApiError(502)
  return {
    id: data.id,
    version: integer(data.version, 1),
    reason: data.reason as StoredCheckpointReason,
    createdAt: data.created_at,
    contentSha256: data.content_sha256,
    uncompressedBytes: integer(data.uncompressed_bytes),
  }
}

function finiteNumber(value: unknown, fallback: number, minimum: number, maximum: number): number {
  if (value === undefined) return fallback
  if (typeof value !== 'number' || !Number.isFinite(value) || value < minimum || value > maximum) {
    throw new PresentationApiError(502)
  }
  return value
}

function parseTheme(value: unknown): Partial<SlideTheme> {
  if (value === undefined) return {}
  const theme = record(value)
  if (theme.themeColors !== undefined && (
    !Array.isArray(theme.themeColors) ||
    theme.themeColors.length === 0 ||
    theme.themeColors.some(color => typeof color !== 'string' || !color)
  )) throw new PresentationApiError(502)
  for (const key of ['backgroundColor', 'fontColor', 'fontName'] as const) {
    if (theme[key] !== undefined && typeof theme[key] !== 'string') throw new PresentationApiError(502)
  }
  if (theme.outline !== undefined) {
    const outline = record(theme.outline)
    if (outline.width !== undefined && (typeof outline.width !== 'number' || !Number.isFinite(outline.width) || outline.width < 0)) {
      throw new PresentationApiError(502)
    }
    if (outline.color !== undefined && typeof outline.color !== 'string') throw new PresentationApiError(502)
    if (outline.style !== undefined && !['solid', 'dashed', 'dotted'].includes(String(outline.style))) {
      throw new PresentationApiError(502)
    }
  }
  if (theme.shadow !== undefined) {
    const shadow = record(theme.shadow)
    for (const key of ['h', 'v', 'blur'] as const) {
      if (shadow[key] !== undefined && (typeof shadow[key] !== 'number' || !Number.isFinite(shadow[key]))) {
        throw new PresentationApiError(502)
      }
    }
    if (shadow.color !== undefined && typeof shadow.color !== 'string') throw new PresentationApiError(502)
  }
  return theme as Partial<SlideTheme>
}

function parseDocument(value: unknown): PresentationDocument {
  const document = record(value)
  if (document.schema_version !== undefined && document.schema_version !== 1) {
    throw new PresentationApiError(502, 'PRESENTATION_SCHEMA_UNSUPPORTED')
  }
  if (!Array.isArray(document.slides)) throw new PresentationApiError(502)
  const slides = document.slides.map(value => {
    const slide = record(value)
    if (typeof slide.id !== 'string' || !slide.id || !Array.isArray(slide.elements)) {
      throw new PresentationApiError(502)
    }
    for (const element of slide.elements) {
      const parsed = record(element)
      if (typeof parsed.id !== 'string' || !parsed.id || typeof parsed.type !== 'string' || !parsed.type) {
        throw new PresentationApiError(502)
      }
    }
    if (slide.remark !== undefined && typeof slide.remark !== 'string') throw new PresentationApiError(502)
    if (slide.notes !== undefined && !Array.isArray(slide.notes)) throw new PresentationApiError(502)
    return slide as unknown as Slide
  })
  return {
    schemaVersion: 1,
    slides,
    theme: parseTheme(document.theme),
    viewportSize: finiteNumber(document.viewport_size, 1000, 320, 10000),
    viewportRatio: finiteNumber(document.viewport_ratio, 0.5625, 0.1, 3),
  }
}

async function request(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(path, {
      ...init,
      credentials: 'include',
      cache: 'no-store',
      headers: { Accept: 'application/json', ...init.headers },
    })
  }
  catch {
    throw new PresentationApiError(0)
  }
}

async function failure(response: Response): Promise<never> {
  let code = 'PRESENTATION_REQUEST_FAILED'
  let latest: PresentationConflictSummary | null = null
  try {
    const data = record(await response.json())
    if (typeof data.code === 'string' && /^[A-Z0-9_]{1,64}$/.test(data.code)) code = data.code
    if (code === 'PRESENTATION_VERSION_CONFLICT') {
      const summary = record(data.latest)
      if (
        typeof summary.title === 'string' && summary.title &&
        Number.isInteger(summary.current_version) && Number(summary.current_version) >= 1 &&
        typeof summary.updated_at === 'string' && !Number.isNaN(Date.parse(summary.updated_at))
      ) {
        // 只保留冲突摘要白名单，服务端即使误带稿件正文也不会进入错误对象。
        latest = {
          title: summary.title,
          currentVersion: Number(summary.current_version),
          updatedAt: summary.updated_at,
        }
      }
    }
  }
  catch {
    // 非JSON和畸形错误体统一收敛，绝不透传原始响应。
  }
  throw new PresentationApiError(response.status, code, latest)
}

function serializeDocument(document: PresentationDocument) {
  return {
    schema_version: document.schemaVersion,
    slides: document.slides,
    theme: document.theme,
    viewport_size: document.viewportSize,
    viewport_ratio: document.viewportRatio,
  }
}

export const presentationApi = {
  async list(query: PresentationListQuery): Promise<PresentationListResult> {
    const params = new URLSearchParams({
      page: String(query.page),
      page_size: String(query.pageSize),
      sort: query.sort,
    })
    if (query.search) params.set('search', query.search)
    if (query.status) params.set('status', query.status)
    const response = await request(`/api/presentations?${params}`, { method: 'GET' })
    if (!response.ok) return failure(response)
    try {
      const data = record(await response.json())
      if (!Array.isArray(data.items) || typeof data.has_more !== 'boolean') throw new PresentationApiError(502)
      return {
        items: data.items.map(parseSummary),
        page: integer(data.page, 1),
        pageSize: integer(data.page_size, 1),
        total: integer(data.total),
        hasMore: data.has_more,
      }
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async create(input: CreatePresentationInput, idempotencyKey: string) {
    const response = await request('/api/presentations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify({
        title: input.title,
        content: input.content,
        language: input.language || 'chinese',
        model: input.model || 'deepseek-chat',
        template_id: input.templateId ?? null,
        generate_from_uploaded_file: input.generateFromUploadedFile ?? false,
        generate_from_web_search: input.generateFromWebSearch ?? true,
      }),
    })
    if (response.status !== 202) return failure(response)
    try {
      const data = record(await response.json())
      const task = record(data.task)
      if (typeof task.id !== 'string' || typeof data.reused !== 'boolean') throw new PresentationApiError(502)
      return { presentation: parseSummary(data.presentation), taskId: task.id, reused: data.reused }
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async saveDraft(input: SaveDraftPresentationInput, idempotencyKey: string) {
    const response = await request('/api/presentations/drafts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify({
        title: input.title,
        template_id: input.templateId ?? null,
        slides: serializeDocument(input.document),
      }),
    })
    if (response.status !== 200 && response.status !== 201) return failure(response)
    try {
      const data = record(await response.json())
      const presentation = record(data.presentation)
      if (typeof data.reused !== 'boolean') throw new PresentationApiError(502)
      return {
        presentation: {
          ...parseSummary(presentation),
          document: parseDocument(presentation.slides),
        } as PresentationDetail,
        reused: data.reused,
      }
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async get(presentationId: string): Promise<PresentationDetail> {
    const response = await request(`/api/presentations/${encodeURIComponent(presentationId)}`, {
      method: 'GET',
    })
    if (!response.ok) return failure(response)
    try {
      const data = record(await response.json())
      const generationProgress = data.generation_progress === null || data.generation_progress === undefined
        ? null
        : integer(data.generation_progress)
      return {
        ...parseSummary(data),
        document: parseDocument(data.slides),
        generationTaskId: data.generation_task_id === undefined ? null : nullableString(data.generation_task_id),
        generationProgress,
        generationErrorCode: data.generation_error_code === undefined ? null : nullableString(data.generation_error_code),
      }
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async save(presentationId: string, input: SavePresentationInput): Promise<PresentationDetail> {
    const response = await request(`/api/presentations/${encodeURIComponent(presentationId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        base_version: input.baseVersion,
        title: input.title,
        slides: serializeDocument(input.document),
      }),
    })
    if (!response.ok) return failure(response)
    try {
      const data = record(await response.json())
      return { ...parseSummary(data), document: parseDocument(data.slides) }
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async duplicate(
    presentationId: string,
    title?: string,
    document?: PresentationDocument,
  ): Promise<PresentationDetail> {
    const response = await request(`/api/presentations/${encodeURIComponent(presentationId)}/duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...(title ? { title } : {}),
        ...(document ? { slides: serializeDocument(document) } : {}),
      }),
    })
    if (response.status !== 201) return failure(response)
    try {
      const data = record(await response.json())
      return { ...parseSummary(data), document: parseDocument(data.slides) }
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async listVersions(presentationId: string): Promise<PresentationVersionListResult> {
    const response = await request(
      `/api/presentations/${encodeURIComponent(presentationId)}/versions`,
      { method: 'GET' },
    )
    if (!response.ok) return failure(response)
    try {
      const data = record(await response.json())
      if (!Array.isArray(data.items)) throw new PresentationApiError(502)
      const items = data.items.map(parseVersionSummary)
      const total = integer(data.total)
      if (total !== items.length) throw new PresentationApiError(502)
      return { items, total }
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async createCheckpoint(
    presentationId: string,
    baseVersion: number,
    reason: CheckpointReason,
  ): Promise<PresentationVersionSummary> {
    const response = await request(
      `/api/presentations/${encodeURIComponent(presentationId)}/versions`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_version: baseVersion, reason }),
      },
    )
    if (response.status !== 200 && response.status !== 201) return failure(response)
    try {
      return parseVersionSummary(await response.json())
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async restoreVersion(
    presentationId: string,
    version: number,
    baseVersion: number,
  ): Promise<PresentationDetail> {
    const response = await request(
      `/api/presentations/${encodeURIComponent(presentationId)}/versions/${version}/restore`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_version: baseVersion }),
      },
    )
    if (!response.ok) return failure(response)
    try {
      const data = record(await response.json())
      return { ...parseSummary(data), document: parseDocument(data.slides) }
    }
    catch (error) {
      if (error instanceof PresentationApiError) throw error
      throw new PresentationApiError(502)
    }
  },

  async remove(presentationId: string): Promise<void> {
    const response = await request(`/api/presentations/${encodeURIComponent(presentationId)}`, {
      method: 'DELETE',
    })
    if (response.status === 204) return
    return failure(response)
  },
}

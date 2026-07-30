import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PresentationApiError, presentationApi } from '@/services/presentations'


const fetchMock = vi.fn()
vi.stubGlobal('fetch', fetchMock)

function response(body: unknown, status = 200): Response {
  return new Response(body === null ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const item = {
  id: 'presentation-1',
  title: '季度复盘',
  status: 'ready',
  current_version: 2,
  slide_count: 12,
  template_id: null,
  thumbnail_file_id: null,
  created_at: '2026-07-23T01:00:00Z',
  updated_at: '2026-07-23T02:00:00Z',
}

beforeEach(() => fetchMock.mockReset())

describe('presentationApi', () => {
  it('列表只发送受限查询并解析服务端字段', async () => {
    fetchMock.mockResolvedValue(response({ items: [item], page: 2, page_size: 10, total: 11, has_more: false }))

    const result = await presentationApi.list({
      page: 2,
      pageSize: 10,
      search: '季度',
      status: 'ready',
      sort: 'title_asc',
    })

    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/api/presentations?')
    expect(String(url)).toContain('search=%E5%AD%A3%E5%BA%A6')
    expect(init).toMatchObject({ credentials: 'include', cache: 'no-store' })
    expect(result.items[0]).toMatchObject({ id: 'presentation-1', slideCount: 12, currentVersion: 2 })
  })

  it('创建使用幂等头且请求体不能携带owner', async () => {
    fetchMock.mockResolvedValue(response({
      presentation: item,
      task: { id: 'task-1', status: 'pending', stage: 'queued', progress: 0, retryable: true },
      reused: false,
    }, 202))

    await presentationApi.create(
      { title: '季度复盘', content: '生成经营复盘', language: 'chinese', model: 'deepseek-chat' },
      'browser-request-1',
    )

    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers).toMatchObject({ 'Idempotency-Key': 'browser-request-1' })
    expect(String(init.body)).not.toContain('owner')
    expect(JSON.parse(String(init.body))).toMatchObject({
      generate_from_uploaded_file: false,
      generate_from_web_search: true,
    })
  })

  it('把临时编辑稿保存为草稿作品且不创建生成任务', async () => {
    fetchMock.mockResolvedValue(response({
      presentation: {
        ...item,
        status: 'draft',
        current_version: 1,
        slide_count: 1,
        slides: {
          schema_version: 1,
          slides: [{ id: 'slide-1', elements: [] }],
          theme: {},
          viewport_size: 1000,
          viewport_ratio: 0.5625,
        },
      },
      reused: false,
    }, 201))

    const result = await presentationApi.saveDraft({
      title: 'Linux 入门',
      templateId: 'template_1',
      document: {
        schemaVersion: 1,
        slides: [{ id: 'slide-1', elements: [] }],
        theme: {},
        viewportSize: 1000,
        viewportRatio: 0.5625,
      },
    }, 'save-session-1')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/presentations/drafts')
    expect(init).toMatchObject({ method: 'POST', credentials: 'include' })
    expect(init.headers).toMatchObject({ 'Idempotency-Key': 'save-session-1' })
    expect(String(init.body)).not.toContain('owner')
    expect(result.presentation).toMatchObject({ status: 'draft', currentVersion: 1 })
  })

  it('删除只接受204，错误不透传服务端敏感正文', async () => {
    fetchMock.mockResolvedValueOnce(response(null, 204))
    await expect(presentationApi.remove('presentation-1')).resolves.toBeUndefined()

    fetchMock.mockResolvedValueOnce(response({ code: 'RAW', message: 'secret upstream detail' }, 500))
    const error = await presentationApi.remove('presentation-1').catch(error => error as PresentationApiError)
    expect(error).toMatchObject({
      name: 'PresentationApiError',
      status: 500,
    })
    expect(error.message).toBe('作品请求失败')
    expect(error.message).not.toContain('secret upstream detail')
  })

  it('畸形成功响应按协议错误处理', async () => {
    fetchMock.mockResolvedValue(response({ items: 'not-array' }))
    await expect(presentationApi.list({ page: 1, pageSize: 20, sort: 'updated_desc' }))
      .rejects.toBeInstanceOf(PresentationApiError)
  })

  it('详情接口恢复完整编辑稿且不发送owner', async () => {
    fetchMock.mockResolvedValue(response({
      ...item,
      slides: {
        schema_version: 1,
        slides: [{ id: 'slide-1', elements: [] }],
        theme: { themeColors: ['#123456'], fontColor: '#222222' },
        viewport_size: 1200,
        viewport_ratio: 0.75,
      },
    }))

    const detail = await presentationApi.get('presentation-1')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/presentations/presentation-1')
    expect(init).toMatchObject({ method: 'GET', credentials: 'include', cache: 'no-store' })
    expect(String(url)).not.toContain('owner')
    expect(detail.document).toMatchObject({
      schemaVersion: 1,
      viewportSize: 1200,
      viewportRatio: 0.75,
      slides: [{ id: 'slide-1', elements: [] }],
    })
  })

  it('详情稿件结构损坏或404时保留稳定错误边界', async () => {
    fetchMock.mockResolvedValueOnce(response({ ...item, slides: { slides: [{ id: '', elements: [] }] } }))
    await expect(presentationApi.get('broken')).rejects.toMatchObject({ status: 502 })

    fetchMock.mockResolvedValueOnce(response({ code: 'PRESENTATION_NOT_FOUND', message: '不应透传' }, 404))
    await expect(presentationApi.get('missing')).rejects.toMatchObject({
      status: 404,
      code: 'PRESENTATION_NOT_FOUND',
      message: '作品请求失败',
    })
  })

  it('可解析精确10MiB的UTF-8当前稿', async () => {
    const document = { schema_version: 1, slides: [{ id: 'boundary', elements: [], remark: '' }] }
    const baseBytes = new TextEncoder().encode(JSON.stringify(document)).byteLength
    document.slides[0].remark = 'x'.repeat(10 * 1024 * 1024 - baseBytes)
    expect(new TextEncoder().encode(JSON.stringify(document)).byteLength).toBe(10 * 1024 * 1024)
    fetchMock.mockResolvedValue(response({ ...item, slide_count: 1, slides: document }))

    const detail = await presentationApi.get('presentation-1')
    expect(detail.document.slides[0].remark?.length).toBe(document.slides[0].remark.length)
  })

  it('保存发送规范当前稿且解析服务端新版本', async () => {
    fetchMock.mockResolvedValue(response({
      ...item,
      current_version: 3,
      title: '已保存标题',
      slides: {
        schema_version: 1,
        slides: [{ id: 'slide-1', elements: [], remark: '已保存' }],
        viewport_size: 1000,
        viewport_ratio: 0.5625,
      },
    }))

    const saved = await presentationApi.save('presentation-1', {
      baseVersion: 2,
      title: '已保存标题',
      document: {
        schemaVersion: 1,
        slides: [{ id: 'slide-1', elements: [], remark: '已保存' }],
        theme: {},
        viewportSize: 1000,
        viewportRatio: 0.5625,
      },
    })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/presentations/presentation-1')
    expect(init).toMatchObject({ method: 'PATCH', credentials: 'include' })
    expect(JSON.parse(String(init.body))).toEqual({
      base_version: 2,
      title: '已保存标题',
      slides: {
        schema_version: 1,
        slides: [{ id: 'slide-1', elements: [], remark: '已保存' }],
        theme: {},
        viewport_size: 1000,
        viewport_ratio: 0.5625,
      },
    })
    expect(saved.currentVersion).toBe(3)
    expect(String(init.body)).not.toContain('owner')
  })

  it('保存超限和网络错误保持稳定错误对象', async () => {
    fetchMock.mockResolvedValueOnce(response({ code: 'PRESENTATION_DOCUMENT_TOO_LARGE', message: 'raw' }, 413))
    await expect(presentationApi.save('presentation-1', {
      baseVersion: 2,
      title: '超限',
      document: { schemaVersion: 1, slides: [], theme: {}, viewportSize: 1000, viewportRatio: 0.5625 },
    })).rejects.toMatchObject({ status: 413, code: 'PRESENTATION_DOCUMENT_TOO_LARGE' })

    fetchMock.mockRejectedValueOnce(new Error('secret network detail'))
    await expect(presentationApi.save('presentation-1', {
      baseVersion: 2,
      title: '断网',
      document: { schemaVersion: 1, slides: [], theme: {}, viewportSize: 1000, viewportRatio: 0.5625 },
    })).rejects.toMatchObject({ status: 0, message: '作品请求失败' })
  })

  it('409解析最新版本摘要但不透传服务端稿件', async () => {
    fetchMock.mockResolvedValue(response({
      code: 'PRESENTATION_VERSION_CONFLICT',
      message: 'raw conflict',
      latest: {
        title: '标签A版本',
        current_version: 7,
        updated_at: '2026-07-23T05:00:00Z',
        slides: { secret: '不能进入错误对象' },
      },
    }, 409))

    await expect(presentationApi.save('presentation-1', {
      baseVersion: 6,
      title: '标签B版本',
      document: { schemaVersion: 1, slides: [], theme: {}, viewportSize: 1000, viewportRatio: 0.5625 },
    })).rejects.toMatchObject({
      status: 409,
      code: 'PRESENTATION_VERSION_CONFLICT',
      latest: { title: '标签A版本', currentVersion: 7, updatedAt: '2026-07-23T05:00:00Z' },
      message: '作品请求失败',
    })
  })

  it('另存副本可携带本地冲突稿且不发送owner或旧版本', async () => {
    fetchMock.mockResolvedValue(response({
      ...item,
      id: 'copy-1',
      title: '冲突稿副本',
      current_version: 1,
      slides: { schema_version: 1, slides: [{ id: 'local', elements: [] }] },
    }, 201))
    const copied = await presentationApi.duplicate('presentation-1', '冲突稿副本', {
      schemaVersion: 1,
      slides: [{ id: 'local', elements: [] }],
      theme: {},
      viewportSize: 1000,
      viewportRatio: 0.5625,
    })
    const [, init] = fetchMock.mock.calls[0]
    const body = JSON.parse(String(init.body))
    expect(body.title).toBe('冲突稿副本')
    expect(body.slides.slides[0].id).toBe('local')
    expect(JSON.stringify(body)).not.toMatch(/owner|base_version/)
    expect(copied).toMatchObject({ id: 'copy-1', currentVersion: 1 })
  })

  it('版本列表只解析摘要并拒绝畸形哈希', async () => {
    fetchMock.mockResolvedValueOnce(response({
      items: [{
        id: 'version-2', version: 2, reason: 'manual',
        created_at: '2026-07-23T05:00:00Z',
        content_sha256: 'a'.repeat(64), uncompressed_bytes: 128,
      }],
      total: 1,
    }))
    const result = await presentationApi.listVersions('presentation-1')
    expect(result.items[0]).toEqual({
      id: 'version-2', version: 2, reason: 'manual',
      createdAt: '2026-07-23T05:00:00Z',
      contentSha256: 'a'.repeat(64), uncompressedBytes: 128,
    })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/presentations/presentation-1/versions')

    fetchMock.mockResolvedValueOnce(response({
      items: [{ id: 'bad', version: 1, reason: 'manual', created_at: 'bad', content_sha256: 'raw', uncompressed_bytes: 1 }],
      total: 1,
    }))
    await expect(presentationApi.listVersions('presentation-1')).rejects.toMatchObject({ status: 502 })
  })

  it('创建手动检查点只发送原因和当前版本', async () => {
    fetchMock.mockResolvedValue(response({
      id: 'version-2', version: 2, reason: 'manual',
      created_at: '2026-07-23T05:00:00Z', content_sha256: 'b'.repeat(64), uncompressed_bytes: 256,
    }, 201))
    await presentationApi.createCheckpoint('presentation-1', 2, 'manual')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/presentations/presentation-1/versions')
    expect(init.method).toBe('POST')
    expect(JSON.parse(String(init.body))).toEqual({ base_version: 2, reason: 'manual' })
    expect(String(init.body)).not.toContain('owner')
  })

  it('恢复历史提交当前基线并解析生成的新版本', async () => {
    fetchMock.mockResolvedValue(response({
      ...item,
      current_version: 3,
      slides: { schema_version: 1, slides: [{ id: 'restored', elements: [] }] },
    }))
    const restored = await presentationApi.restoreVersion('presentation-1', 1, 2)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/presentations/presentation-1/versions/1/restore')
    expect(JSON.parse(String(init.body))).toEqual({ base_version: 2 })
    expect(restored).toMatchObject({ currentVersion: 3 })
    expect(restored.document.slides[0].id).toBe('restored')
  })
})

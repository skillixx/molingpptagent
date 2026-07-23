import { describe, expect, it, vi } from 'vitest'

import { archivePptx, downloadAndArchivePptx, sha256Hex } from '@/services/exports'


describe('downloadAndArchivePptx', () => {
  it('先保存同一Blob，归档失败仍保留本地成功并允许用同一请求键重试', async () => {
    const blob = new Blob(['pptx-byte-identical'], { type: 'application/pptx' })
    const save = vi.fn()
    const archive = vi.fn().mockRejectedValueOnce(new Error('storage unavailable'))

    const result = await downloadAndArchivePptx({
      blob, filename: '季度汇报.pptx', requestId: 'export-1', save, archive,
    })

    expect(save).toHaveBeenCalledWith(blob, '季度汇报.pptx')
    expect(archive).toHaveBeenCalledWith(blob, 'export-1')
    expect(result).toEqual({ localSaved: true, archived: false, requestId: 'export-1' })

    archive.mockResolvedValueOnce({ id: 'record-1' })
    const retry = await downloadAndArchivePptx({
      blob, filename: '季度汇报.pptx', requestId: result.requestId, save, archive,
      skipLocalSave: true,
    })
    expect(save).toHaveBeenCalledTimes(1)
    expect(archive).toHaveBeenLastCalledWith(blob, 'export-1')
    expect(retry.archived).toBe(true)
  })

  it('上传浏览器生成的原始Blob并携带独立SHA与幂等键', async () => {
    const blob = new Blob(['abc'], { type: 'application/pptx' })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      id: 'export-1', presentation_id: 'presentation-1', presentation_version: 3,
      file_id: 'file-1', sha256: await sha256Hex(blob), size_bytes: 3,
      created_at: '2026-07-23T01:00:00+00:00', download_url: '/api/files/file-1/download', reused: false,
    }), { status: 201, headers: { 'Content-Type': 'application/json' } }))

    await archivePptx('presentation-1', 3, blob, 'request-1')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/presentations/presentation-1/exports/pptx')
    expect(init?.body).toBe(blob)
    expect(init?.headers).toMatchObject({
      'Idempotency-Key': 'request-1',
      'X-Presentation-Version': '3',
      'X-Content-SHA256': 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    })
    fetchMock.mockRestore()
  })
})

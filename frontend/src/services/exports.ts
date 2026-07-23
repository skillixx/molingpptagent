const PPTX_MIME = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

export interface ExportRecord {
  id: string
  presentationId: string
  presentationVersion: number
  fileId: string
  sha256: string
  sizeBytes: number
  createdAt: string
  downloadUrl: string
  reused: boolean
}

function mapExportRecord(data: Record<string, unknown>): ExportRecord {
  return {
    id: String(data.id), presentationId: String(data.presentation_id),
    presentationVersion: Number(data.presentation_version), fileId: String(data.file_id),
    sha256: String(data.sha256), sizeBytes: Number(data.size_bytes),
    createdAt: String(data.created_at), downloadUrl: String(data.download_url),
    reused: Boolean(data.reused),
  }
}

interface DownloadAndArchiveInput {
  blob: Blob
  filename: string
  requestId: string
  save: (blob: Blob, filename: string) => void
  archive: (blob: Blob, requestId: string) => Promise<unknown>
  skipLocalSave?: boolean
}

export async function sha256Hex(blob: Blob): Promise<string> {
  const bytes = typeof blob.arrayBuffer === 'function'
    ? await blob.arrayBuffer()
    : await new Promise<ArrayBuffer>((resolve, reject) => {
      // 兼容旧WebView与测试DOM；FileReader只读取内存，不会改变原Blob对象。
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as ArrayBuffer)
      reader.onerror = () => reject(new Error('BLOB_READ_FAILED'))
      reader.readAsArrayBuffer(blob)
    })
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
}

export async function archivePptx(
  presentationId: string,
  presentationVersion: number,
  blob: Blob,
  requestId: string,
): Promise<ExportRecord> {
  const sha256 = await sha256Hex(blob)
  const response = await fetch(
    `/api/presentations/${encodeURIComponent(presentationId)}/exports/pptx`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': PPTX_MIME,
        'Idempotency-Key': requestId,
        'X-Presentation-Version': String(presentationVersion),
        'X-Content-SHA256': sha256,
      },
      body: blob,
    },
  )
  if (!response.ok) throw new Error('PPTX_ARCHIVE_FAILED')
  const data = await response.json() as Record<string, unknown>
  return mapExportRecord(data)
}

export async function archiveThumbnail(presentationId: string, blob: Blob): Promise<void> {
  const response = await fetch(
    `/api/presentations/${encodeURIComponent(presentationId)}/thumbnail`,
    {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'image/png', 'X-Content-SHA256': await sha256Hex(blob) },
      body: blob,
    },
  )
  if (!response.ok) throw new Error('THUMBNAIL_ARCHIVE_FAILED')
}

export async function listPptxExports(presentationId: string): Promise<ExportRecord[]> {
  const response = await fetch(`/api/presentations/${encodeURIComponent(presentationId)}/exports`, {
    credentials: 'include', headers: { 'Accept': 'application/json' },
  })
  if (!response.ok) throw new Error('PPTX_HISTORY_FAILED')
  const data = await response.json() as { items?: Record<string, unknown>[] }
  return (data.items || []).map(mapExportRecord)
}

export async function downloadArchivedPptx(
  record: ExportRecord,
  filename: string,
  save: (blob: Blob, filename: string) => void,
): Promise<void> {
  const response = await fetch(record.downloadUrl, { credentials: 'include' })
  if (!response.ok) throw new Error('PPTX_DOWNLOAD_FAILED')
  const blob = await response.blob()
  // 代理下载后仍在浏览器端复核摘要，损坏对象绝不落盘伪装成成功。
  if (await sha256Hex(blob) !== record.sha256) throw new Error('PPTX_INTEGRITY_FAILED')
  save(blob, filename)
}

export async function downloadAndArchivePptx(input: DownloadAndArchiveInput): Promise<{
  localSaved: boolean
  archived: boolean
  requestId: string
}> {
  // 下载和归档必须持有同一个Blob对象；归档失败不能撤销浏览器已经完成的本地保存。
  if (!input.skipLocalSave) input.save(input.blob, input.filename)
  try {
    await input.archive(input.blob, input.requestId)
    return { localSaved: true, archived: true, requestId: input.requestId }
  }
  catch {
    return { localSaved: true, archived: false, requestId: input.requestId }
  }
}

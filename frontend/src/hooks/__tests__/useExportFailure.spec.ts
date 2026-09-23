import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { Slide } from '@/types/slides'
import useExport from '@/hooks/useExport'

const { write, error } = vi.hoisted(() => ({ write: vi.fn(), error: vi.fn() }))
vi.mock('pptxgenjs', () => ({ default: class {
  layout = ''
  addSlide() { return { addImage: vi.fn() } }
  write() { return write() }
} }))
vi.mock('file-saver', () => ({ saveAs: vi.fn() }))
vi.mock('@/utils/message', () => ({ default: { error, warning: vi.fn(), success: vi.fn() } }))

const documentWithImage = (src: string): Slide[] => [{ id: 'image-failure-slide', elements: [{
  id: 'image', type: 'image', src, left: 20, top: 20, width: 200, height: 100, rotate: 0, fixedRatio: false,
}] }]

describe('PPTX 导出失败恢复', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    write.mockResolvedValue(new Blob(['pptx-test']))
  })
  afterEach(() => vi.unstubAllGlobals())

  it('读取图片失败也提供统一错误反馈，并允许原实例重试', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))
    const exporter = useExport()
    // 失败发生在生成图片数据阶段，必须与最终 write 失败一样释放导出状态。
    await expect(exporter.exportPPTX(documentWithImage('/api/data/missing.png'), false, true)).rejects.toThrow('PPTX_EXPORT_FAILED')
    expect(exporter.exporting.value).toBe(false)
    expect(error).toHaveBeenCalledWith('导出失败')
    expect(write).not.toHaveBeenCalled()
    const result = await exporter.exportPPTX(documentWithImage('data:image/png;base64,fixture'), false, true)
    expect(result.localSaved).toBe(true)
    expect(exporter.exporting.value).toBe(false)
    expect(write).toHaveBeenCalledTimes(1)
  })

  it('写出失败仍反馈一次并重置状态', async () => {
    write.mockRejectedValueOnce(new Error('write failed'))
    const exporter = useExport()
    await expect(exporter.exportPPTX(documentWithImage('data:image/png;base64,fixture'), false, true)).rejects.toThrow('PPTX_EXPORT_FAILED')
    expect(error).toHaveBeenCalledTimes(1)
    expect(exporter.exporting.value).toBe(false)
  })
})

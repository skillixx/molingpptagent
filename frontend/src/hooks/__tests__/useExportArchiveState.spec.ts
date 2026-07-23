import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import useExport from '@/hooks/useExport'


describe('PPTX归档重试状态', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('导出弹窗卸载再创建时仍共享待重试状态', () => {
    const firstDialog = useExport()
    firstDialog.archivePending.value = true

    const reopenedDialog = useExport()
    expect(reopenedDialog.archivePending).toBe(firstDialog.archivePending)
    expect(reopenedDialog.archivePending.value).toBe(true)

    reopenedDialog.archivePending.value = false
  })
})

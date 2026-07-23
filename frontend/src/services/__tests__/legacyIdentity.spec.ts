import { afterEach, describe, expect, it, vi } from 'vitest'

import api from '../index'

describe('旧文件生成接口身份边界', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('上传表单不再发送客户端user_id', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('ok'))
    vi.stubGlobal('fetch', fetchMock)
    const file = new File(['hello'], 'same-name.txt', { type: 'text/plain' })

    await api.AIPPT_Outline_From_File(file, 'chinese')

    const body = fetchMock.mock.calls[0][1].body as FormData
    expect(body.get('file')).toBe(file)
    expect(body.get('language')).toBe('chinese')
    expect(body.get('user_id')).toBeNull()
  })
})

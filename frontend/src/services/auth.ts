export interface AuthUser {
  userId: number
  appId: number
  productId: number
}

export type AuthFailureReason = 'expired' | 'forbidden' | 'platform' | 'logged_out'

export class AuthApiError extends Error {
  reason: AuthFailureReason
  status: number

  constructor(reason: AuthFailureReason, status: number) {
    // 错误消息保持固定，不拼接服务端正文、Cookie或网络异常细节。
    super('认证请求失败')
    this.name = 'AuthApiError'
    this.reason = reason
    this.status = status
  }
}

function parseAuthUser(payload: unknown): AuthUser {
  if (!payload || typeof payload !== 'object') throw new AuthApiError('platform', 502)
  const data = payload as Record<string, unknown>
  const values = [data.user_id, data.app_id, data.product_id]
  if (!values.every(value => Number.isInteger(value) && Number(value) > 0)) {
    throw new AuthApiError('platform', 502)
  }
  return {
    userId: Number(data.user_id),
    appId: Number(data.app_id),
    productId: Number(data.product_id),
  }
}

async function request(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(path, {
      ...init,
      credentials: 'include',
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        ...init.headers,
      },
    })
  }
  catch {
    throw new AuthApiError('platform', 0)
  }
}

export const authApi = {
  async getCurrentUser(): Promise<AuthUser> {
    const response = await request('/api/auth/me', { method: 'GET' })
    if (response.status === 401) throw new AuthApiError('expired', 401)
    if (response.status === 403) throw new AuthApiError('forbidden', 403)
    if (!response.ok) throw new AuthApiError('platform', response.status)
    try {
      return parseAuthUser(await response.json())
    }
    catch (error) {
      if (error instanceof AuthApiError) throw error
      throw new AuthApiError('platform', 502)
    }
  },

  async logout(): Promise<void> {
    const response = await request('/api/auth/logout', { method: 'POST' })
    if (response.status === 204) return
    if (response.status === 403) throw new AuthApiError('forbidden', 403)
    if (response.status === 401) return
    throw new AuthApiError('platform', response.status)
  },
}

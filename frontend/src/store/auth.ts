import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { AuthApiError, authApi } from '@/services/auth'
import type { AuthFailureReason, AuthUser } from '@/services/auth'


export const AUTH_SYNC_KEY = 'trainppt:auth-event'
export type AuthStatus = 'idle' | 'loading' | 'authenticated' | 'anonymous' | 'error'

export const useAuthStore = defineStore('auth', () => {
  const status = ref<AuthStatus>('idle')
  const user = ref<AuthUser | null>(null)
  const failureReason = ref<AuthFailureReason | null>(null)
  let initialized = false
  let pendingInitialization: Promise<void> | null = null
  let stateEpoch = 0

  const isAuthenticated = computed(() => status.value === 'authenticated' && user.value !== null)

  function markAuthenticated(nextUser: AuthUser) {
    stateEpoch += 1
    pendingInitialization = null
    user.value = nextUser
    status.value = 'authenticated'
    failureReason.value = null
    initialized = true
  }

  function markAnonymous(reason: AuthFailureReason = 'expired') {
    stateEpoch += 1
    pendingInitialization = null
    user.value = null
    status.value = 'anonymous'
    failureReason.value = reason
    initialized = true
  }

  async function initialize(force = false): Promise<void> {
    if (!force && initialized) return
    if (pendingInitialization) return pendingInitialization
    status.value = 'loading'
    const requestEpoch = stateEpoch
    const request = authApi.getCurrentUser()
      .then(nextUser => {
        // 退出、跨标签失效或更新一轮认证后，旧响应不得重新复活已失效身份。
        if (requestEpoch !== stateEpoch) return
        user.value = nextUser
        status.value = 'authenticated'
        failureReason.value = null
        initialized = true
      })
      .catch(error => {
        if (requestEpoch !== stateEpoch) return
        user.value = null
        initialized = true
        if (error instanceof AuthApiError && error.reason === 'expired') {
          status.value = 'anonymous'
          failureReason.value = 'expired'
          return
        }
        status.value = 'error'
        failureReason.value = error instanceof AuthApiError ? error.reason : 'platform'
      })
      .finally(() => {
        if (pendingInitialization === request) pendingInitialization = null
      })
    pendingInitialization = request
    return request
  }

  async function logout(): Promise<void> {
    // 先废弃所有在途/me结果，再调用服务端撤销，避免慢响应覆盖退出状态。
    stateEpoch += 1
    pendingInitialization = null
    status.value = 'loading'
    try {
      await authApi.logout()
      markAnonymous('logged_out')
      // localStorage事件会通知其他标签；随机后缀保证连续退出也产生不同值。
      localStorage.setItem(AUTH_SYNC_KEY, `logout:${Date.now()}:${Math.random()}`)
    }
    catch (error) {
      status.value = 'error'
      failureReason.value = error instanceof AuthApiError ? error.reason : 'platform'
      throw error
    }
  }

  function startCrossTabSync(onInvalidated: () => void): () => void {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== AUTH_SYNC_KEY || !event.newValue?.startsWith('logout:')) return
      markAnonymous('expired')
      onInvalidated()
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }

  return {
    status,
    user,
    failureReason,
    isAuthenticated,
    initialize,
    logout,
    markAuthenticated,
    markAnonymous,
    startCrossTabSync,
  }
})

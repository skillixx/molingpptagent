import type { Pinia } from 'pinia'
import type { Router } from 'vue-router'

import { useAuthStore } from '@/store/auth'


export async function resolveAuthNavigation(
  authStore: ReturnType<typeof useAuthStore>,
  ssoEnabled: boolean,
  requiresAuth: boolean,
  targetPath: string,
) {
  if (!ssoEnabled || !requiresAuth) return true
  // 每次受保护导航都重新向服务端确认，不能用首次登录结果永久放行。
  await authStore.initialize(true)
  if (authStore.isAuthenticated) return true
  return {
    name: 'AuthFailure',
    query: {
      reason: authStore.failureReason || 'platform',
      // 只保存Vue Router生成的站内fullPath，失败页仍会再次校验是否以单斜杠开头。
      redirect: targetPath,
    },
  }
}

export function installAuthGuard(router: Router, pinia: Pinia, ssoEnabled: boolean) {
  router.beforeEach(to => resolveAuthNavigation(
    useAuthStore(pinia),
    ssoEnabled,
    to.meta.requiresAuth === true,
    to.fullPath,
  ))
}

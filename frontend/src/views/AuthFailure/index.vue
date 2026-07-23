<template>
  <main class="auth-failure-shell">
    <section class="auth-failure-card" aria-labelledby="auth-failure-title">
      <div class="status-mark" aria-hidden="true">!</div>
      <p class="eyebrow">墨灵身份验证</p>
      <h1 id="auth-failure-title">{{ content.title }}</h1>
      <p class="description">{{ content.description }}</p>

      <div class="actions">
        <button class="primary-action" type="button" :disabled="retrying" @click="retryAuth">
          {{ retrying ? '正在检查…' : '重新检查登录' }}
        </button>
        <button class="secondary-action" type="button" @click="returnToMoling">
          返回墨灵
        </button>
      </div>

      <p v-if="actionMessage" class="action-message" role="status" aria-live="polite">
        {{ actionMessage }}
      </p>
      <p class="security-note">为保护账号安全，请勿复制或分享地址栏中的登录参数。</p>
    </section>
  </main>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { authFrontendConfig } from '@/services/authConfig'
import { useAuthStore } from '@/store/auth'
import type { AuthFailureReason } from '@/services/auth'


const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const retrying = ref(false)
const actionMessage = ref('')

const reason = computed<AuthFailureReason>(() => {
  const value = typeof route.query.reason === 'string' ? route.query.reason : 'platform'
  return ['expired', 'forbidden', 'platform', 'logged_out'].includes(value)
    ? value as AuthFailureReason
    : 'platform'
})

const content = computed(() => ({
  expired: {
    title: '登录状态已过期',
    description: '请返回墨灵，从“我的资产”重新进入应用。',
  },
  forbidden: {
    title: '请求来源未通过验证',
    description: '请关闭当前页面，并从墨灵的应用入口重新打开。',
  },
  platform: {
    title: '暂时无法确认登录状态',
    description: '平台或网络暂时不可用，请稍后重试；系统不会降级为匿名账号。',
  },
  logged_out: {
    title: '你已安全退出',
    description: '当前浏览器会话已结束，如需继续使用请从墨灵重新进入。',
  },
}[reason.value]))

function safeRedirect(): string {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  // 双斜杠可能被浏览器解释为外部主机，认证恢复只能回到单斜杠站内路径。
  return target.startsWith('/') && !target.startsWith('//') ? target : '/'
}

async function retryAuth() {
  retrying.value = true
  actionMessage.value = ''
  await authStore.initialize(true)
  retrying.value = false
  if (authStore.isAuthenticated) {
    await router.replace(safeRedirect())
    return
  }
  actionMessage.value = authStore.failureReason === 'expired'
    ? '登录仍已过期，请从墨灵重新进入。'
    : '暂时仍无法连接，请稍后再试。'
}

function returnToMoling() {
  if (!authFrontendConfig.molingPortalUrl) {
    actionMessage.value = '当前部署未配置墨灵返回地址，请联系管理员。'
    return
  }
  // 用户主动返回墨灵时不应被旧编辑器的通用离开确认阻断。
  window.onbeforeunload = null
  window.location.assign(authFrontendConfig.molingPortalUrl)
}
</script>

<style lang="scss" scoped>
.auth-failure-shell {
  box-sizing: border-box;
  width: 100%;
  min-height: 100dvh;
  padding: clamp(24px, 7vw, 96px);
  display: grid;
  place-items: center;
  overflow-x: hidden;
  background:
    radial-gradient(circle at 15% 15%, rgba(74, 108, 247, 0.14), transparent 34%),
    linear-gradient(145deg, #f7f9ff 0%, #eef2ff 100%);
}

.auth-failure-card {
  box-sizing: border-box;
  width: min(100%, 620px);
  padding: clamp(28px, 5vw, 56px);
  border: 1px solid rgba(58, 82, 180, 0.14);
  border-radius: clamp(20px, 3vw, 32px);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 28px 80px rgba(36, 52, 118, 0.14);
}

.status-mark {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: #eef1ff;
  color: #4358c7;
  font-size: 30px;
  font-weight: 700;
}

.eyebrow {
  margin-top: 28px;
  color: #6170b9;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

h1 {
  margin-top: 10px;
  color: #17204a;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.2;
}

.description {
  margin-top: 18px;
  color: #566083;
  font-size: clamp(15px, 1.8vw, 17px);
  line-height: 1.75;
}

.actions {
  margin-top: 34px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

button {
  min-height: 46px;
  padding: 0 22px;
  border-radius: 12px;
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 15px;
  font-weight: 650;
  transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
}

button:focus-visible {
  outline: 3px solid rgba(67, 88, 199, 0.28);
  outline-offset: 2px;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.primary-action {
  color: #fff;
  background: #4358c7;
  box-shadow: 0 10px 24px rgba(67, 88, 199, 0.24);
}

.secondary-action {
  color: #35448e;
  border-color: #cfd6f7;
  background: #fff;
}

.action-message {
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 10px;
  color: #7a4b00;
  background: #fff6dc;
  line-height: 1.6;
}

.security-note {
  margin-top: 26px;
  padding-top: 20px;
  border-top: 1px solid #e9ecf8;
  color: #7b829f;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .auth-failure-shell {
    place-items: start center;
    padding-top: max(48px, env(safe-area-inset-top));
    padding-bottom: max(32px, env(safe-area-inset-bottom));
  }
}

@media (max-width: 480px) {
  .auth-failure-shell {
    padding-left: 16px;
    padding-right: 16px;
  }

  .auth-failure-card {
    padding: 26px 20px;
    border-radius: 20px;
  }

  .actions,
  button {
    width: 100%;
  }
}
</style>

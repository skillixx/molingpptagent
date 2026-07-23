<template>
  <aside v-if="authStore.user" class="session-control" aria-label="当前登录会话">
    <span class="identity" :title="`墨灵用户 ${authStore.user.userId}`">
      <span class="identity-avatar" aria-hidden="true">墨</span>
      <span class="identity-copy">
        <span class="identity-label">墨灵用户</span>
        <strong class="identity-value">{{ authStore.user.userId }}</strong>
      </span>
    </span>
    <button
      type="button"
      class="logout-button"
      aria-label="退出当前账号"
      title="安全退出当前账号"
      :aria-busy="loggingOut"
      :disabled="loggingOut"
      @click="handleLogout"
    >
      <svg class="logout-button-icon" aria-hidden="true" viewBox="0 0 24 24">
        <path d="M10 5H6.8A1.8 1.8 0 0 0 5 6.8v10.4A1.8 1.8 0 0 0 6.8 19H10M14 8l4 4-4 4m4-4H9" />
      </svg>
      <span>{{ loggingOut ? '退出中…' : '退出' }}</span>
    </button>
    <span v-if="feedback" class="feedback" role="status" aria-live="polite">{{ feedback }}</span>
  </aside>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/store/auth'


const authStore = useAuthStore()
const router = useRouter()
const loggingOut = ref(false)
const feedback = ref('')

async function handleLogout() {
  loggingOut.value = true
  feedback.value = ''
  try {
    await authStore.logout()
    await router.replace({ name: 'AuthFailure', query: { reason: 'logged_out' } })
  }
  catch {
    // Store已把错误归类；组件只显示稳定提示，不呈现服务端正文或网络细节。
    feedback.value = '退出失败，请稍后重试。'
  }
  finally {
    loggingOut.value = false
  }
}
</script>

<style lang="scss" scoped>
.session-control {
  box-sizing: border-box;
  position: fixed;
  z-index: 3000;
  // 控件收进编辑器首行高度内，避免遮住右侧“设计/切换/动画”标签。
  top: 5px;
  right: 12px;
  max-width: calc(100vw - 24px);
  min-height: 34px;
  padding: 3px 3px 3px 7px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(67, 88, 199, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 4px 14px rgba(24, 36, 92, 0.12);
  backdrop-filter: blur(10px);
}

.identity {
  width: 78px;
  min-width: 0;
  max-width: 78px;
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.identity-avatar {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #4358c7;
  background: #eef1ff;
  font-size: 12px;
  font-weight: 700;
}

.identity-copy {
  min-width: 0;
  display: grid;
  line-height: 1.05;
}

.identity-label {
  color: #8a93ad;
  font-size: 9px;
}

.identity-value {
  overflow: hidden;
  color: #3f496c;
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
}

.logout-button {
  min-width: 62px;
  min-height: 28px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: 0;
  border-radius: 999px;
  color: #fff;
  background: linear-gradient(135deg, #5f71df, #4358c7);
  box-shadow: 0 3px 8px rgba(67, 88, 199, 0.24);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
}

.logout-button-icon {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.logout-button:hover:not(:disabled) {
  filter: brightness(1.06);
  box-shadow: 0 5px 12px rgba(67, 88, 199, 0.3);
  transform: translateY(-1px);
}

.logout-button:active:not(:disabled) {
  box-shadow: 0 2px 6px rgba(67, 88, 199, 0.22);
  transform: translateY(0);
}

.logout-button:focus-visible {
  outline: 3px solid rgba(67, 88, 199, 0.3);
  outline-offset: 2px;
}

.logout-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.feedback {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  max-width: 180px;
  padding: 7px 9px;
  border: 1px solid rgba(194, 79, 62, 0.14);
  border-radius: 8px;
  color: #a13b2f;
  background: #fff4f1;
  box-shadow: 0 6px 18px rgba(91, 34, 27, 0.12);
  font-size: 12px;
  line-height: 1.35;
}

@media (max-width: 768px) {
  .session-control {
    top: 5px;
    right: 8px;
    max-width: calc(100vw - 16px);
  }

  .identity-label {
    display: none;
  }

  .identity {
    width: auto;
    max-width: 58px;
  }
}

@media (max-width: 420px) {
  .identity-copy {
    display: none;
  }

  .logout-button {
    min-width: 58px;
    min-height: 32px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .logout-button {
    transition: none;
  }
}
</style>

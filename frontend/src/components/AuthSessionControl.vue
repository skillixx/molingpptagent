<template>
  <aside v-if="authStore.user" class="session-control" aria-label="当前登录会话">
    <span class="identity">墨灵用户 {{ authStore.user?.userId }}</span>
    <button type="button" :disabled="loggingOut" @click="handleLogout">
      {{ loggingOut ? '退出中…' : '退出' }}
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
  top: 12px;
  right: 12px;
  max-width: calc(100vw - 24px);
  min-height: 40px;
  padding: 6px 7px 6px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(67, 88, 199, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 8px 24px rgba(24, 36, 92, 0.14);
  backdrop-filter: blur(12px);
}

.identity {
  overflow: hidden;
  color: #4e587c;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

button {
  min-width: 56px;
  min-height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  color: #fff;
  background: #4358c7;
  cursor: pointer;
}

button:focus-visible {
  outline: 3px solid rgba(67, 88, 199, 0.3);
  outline-offset: 2px;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.feedback {
  max-width: 180px;
  color: #a13b2f;
  font-size: 12px;
  line-height: 1.35;
}

@media (max-width: 480px) {
  .session-control {
    left: 12px;
    justify-content: flex-end;
  }

  .identity {
    margin-right: auto;
  }

  .feedback {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    padding: 8px 10px;
    border-radius: 8px;
    background: #fff4f1;
  }
}
</style>

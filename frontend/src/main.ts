import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { installAuthGuard } from '@/router/authGuard'
import { authFrontendConfig } from '@/services/authConfig'
import { useAuthStore } from '@/store/auth'

import '@icon-park/vue-next/styles/index.css'
import 'prosemirror-view/style/prosemirror.css'
import 'animate.css'
import '@/assets/styles/prosemirror.scss'
import '@/assets/styles/global.scss'
import '@/assets/styles/font.scss'

import Icon from '@/plugins/icon'
import Directive from '@/plugins/directive'

const app = createApp(App)
const pinia = createPinia()
app.use(Icon)
app.use(Directive)
app.use(pinia)
installAuthGuard(router, pinia, authFrontendConfig.ssoEnabled)

if (authFrontendConfig.ssoEnabled) {
  const authStore = useAuthStore(pinia)
  const redirectIfSessionExpired = async () => {
    if (router.currentRoute.value.meta.requiresAuth !== true) return
    await authStore.initialize(true)
    if (!authStore.isAuthenticated) {
      await router.replace({
        name: 'AuthFailure',
        query: { reason: authStore.failureReason || 'platform' },
      })
    }
  }
  authStore.startCrossTabSync(() => {
    if (router.currentRoute.value.meta.requiresAuth === true) {
      void router.replace({ name: 'AuthFailure', query: { reason: 'expired' } })
    }
  })
  document.addEventListener('visibilitychange', () => {
    // 标签页从后台恢复时重新询问服务端，不能长期信任首次加载的身份快照。
    if (document.visibilityState === 'visible') void redirectIfSessionExpired()
  })
}
app.use(router)
app.mount('#app')

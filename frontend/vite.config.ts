import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  // 正式部署在根域；绝对资源路径保证/editor/:id等history深链不会请求/editor/assets。
  base: '/',
  plugins: [
    vue(),
  ],
  server: {
    host: '127.0.0.1',
    // 与原 molinppt 统一使用 5778，strictPort 可避免端口占用时静默漂移。
    port: 5778,
    strictPort: true,
    proxy: {
      // 登录票据只能由主 API 服务端校验；保留查询串并原样转发，避免 Vue 空路由白屏。
      '/enter': {
        target: 'http://127.0.0.1:6800',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://127.0.0.1:6800',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      }
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `
          @import '@/assets/styles/variable.scss';
          @import '@/assets/styles/mixin.scss';
        `
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})

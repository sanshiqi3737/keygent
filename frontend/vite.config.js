import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const DEV_PORT = Number(process.env.VITE_DEV_PORT || 5173)
const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'
// Electron 用 loadFile(file://) 打开本地 dist 时须用相对资源路径，否则 /assets/* 会指向磁盘根路径而白屏
const ELECTRON_FILE = String(process.env.VITE_ELECTRON_FILE || '').trim() === '1'

export default defineConfig({
  base: ELECTRON_FILE ? './' : '/',
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: {
        main: 'index.html',
        admin: 'admin.html',
      },
    },
  },
  server: {
    port: DEV_PORT,
    proxy: {
      // 与 api.js 中 checkBackendHealth() 使用的 /health 一致（未设置 VITE_PUBLIC_API_BASE 时为同源相对路径）
      '/health': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
    },
  },
})

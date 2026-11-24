import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
    },
    // Dev-прокси: фронт ходит по относительным путям (/llm, /payment, ...),
    // здесь они перенаправляются на локальный backend:8000. Это снимает
    // хардкод localhost:8000 из кода и повторяет поведение nginx в проде.
    proxy: {
      // Генерация через LLM может длиться минуты — увеличиваем таймаут прокси
      // для /llm, чтобы dev-режим совпадал с боевым (nginx proxy_read_timeout 300s).
      '/llm': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 300000,
        proxyTimeout: 300000,
      },
      '/payment': 'http://localhost:8000',
      '/session': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})










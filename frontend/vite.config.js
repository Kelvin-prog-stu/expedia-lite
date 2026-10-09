import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// BACKEND_URL and FRONTEND_PORT let a second copy of the app run beside the real one,
// for tests against a throwaway database. Normally unset.
const backend = process.env.BACKEND_URL || 'http://localhost:8000'
const port = Number(process.env.FRONTEND_PORT) || 5173

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port,
    proxy: {
      // Forwards /api calls to the FastAPI backend during development.
      '/api': backend,
    },
  },
})

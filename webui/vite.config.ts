// webui/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Prefer process.env (Amplify/CI), fallback to .env.production that Vite loads.
  const apiBase = process.env.VITE_API_BASE_URL ?? ''

  return {
    plugins: [react()],
    define: {
      // Make sure code like import.meta.env.VITE_API_BASE_URL has a concrete string at build
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(apiBase.replace(/\/+$/, '')),
    },
  }
})

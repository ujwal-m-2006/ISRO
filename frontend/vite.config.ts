import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

// https://vitejs.dev/config/

// The backend's actual port shifts whenever autoPort reassigns it (another
// process already holding 8000), so it writes its resolved port to
// backend/.dev-port on startup — read that here instead of hardcoding a
// fallback number, which has repeatedly gone stale across sessions.
function resolveBackendPort(): number {
  if (process.env.BACKEND_PORT) return Number(process.env.BACKEND_PORT)
  try {
    const raw = readFileSync(resolve(__dirname, '../backend/.dev-port'), 'utf-8').trim()
    const parsed = Number(raw)
    if (parsed > 0) return parsed
  } catch {
    // backend hasn't started yet, or file doesn't exist — fall through
  }
  return 8000
}

const backendPort = resolveBackendPort()

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  server: {
    port: process.env.PORT ? Number(process.env.PORT) : 3000,
    open: true,
    proxy: {
      '/api': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
        secure: false,
        ws: true
      }
    }
  }
})
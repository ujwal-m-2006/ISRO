import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
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
        target: `http://localhost:${process.env.BACKEND_PORT || 58510}`,
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: `http://localhost:${process.env.BACKEND_PORT || 58510}`,
        changeOrigin: true,
        secure: false,
        ws: true
      }
    }
  }
})
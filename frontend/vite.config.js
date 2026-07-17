import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    proxy: {
      // All REST calls (/api/**) and the WebSocket endpoint
      // (/api/test-cases/:id/execute) share the same /api prefix.
      // Setting ws: true tells Vite to also upgrade matching
      // connections to WebSocket when the client asks for it.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
        secure: false
      },
    },
  },
})

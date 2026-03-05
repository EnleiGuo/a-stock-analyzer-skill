import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,  // 允许局域网 IP 访问
    port: 4661,
    proxy: {
      '/api': {
        target: 'http://localhost:4662',
        changeOrigin: true,
      },
    },
  },
})

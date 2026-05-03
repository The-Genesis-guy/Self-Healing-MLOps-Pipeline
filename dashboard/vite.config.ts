import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/pipeline': 'http://localhost:8000',
      '/models': 'http://localhost:8000',
      '/drift': 'http://localhost:8000',
      '/metrics': 'http://localhost:8000',
    }
  }
})

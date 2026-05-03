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
    // Proxy API requests to backend. When running inside Docker Compose
    // use the `backend` service hostname; when running locally use localhost.
    proxy: {
      '/pipeline': process.env.DOCKER === 'true' ? 'http://backend:8000' : 'http://localhost:8000',
      '/models': process.env.DOCKER === 'true' ? 'http://backend:8000' : 'http://localhost:8000',
      '/drift': process.env.DOCKER === 'true' ? 'http://backend:8000' : 'http://localhost:8000',
      '/metrics': process.env.DOCKER === 'true' ? 'http://backend:8000' : 'http://localhost:8000',
    }
  }
})

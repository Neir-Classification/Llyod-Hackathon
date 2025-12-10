import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/speech-to-text': 'http://localhost:8000',
      '/text-to-speech': 'http://localhost:8000',
      '/rag-query': 'http://localhost:8000'
    }
  }
})

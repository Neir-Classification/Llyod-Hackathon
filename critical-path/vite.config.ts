import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/speech-to-text': 'http://localhost:8000',
      '/speech-to-text-chunk': 'http://localhost:8000',
      '/text-to-speech': 'http://localhost:8000',
      '/rag-query': 'http://localhost:8000',
      '/rag-audio-query': 'http://localhost:8000',
      '/rag-audio-query-chunk': 'http://localhost:8000',
      // Dual-pipeline endpoints
      '/intent-detect': 'http://localhost:8000',
      '/quick-response-audio': 'http://localhost:8000',
      '/rag-query-dual': 'http://localhost:8000',
      '/rag-audio-dual': 'http://localhost:8000',
      '/warm-cache': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      // WebSocket for real-time dual-pipeline
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    }
  }
})

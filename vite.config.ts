import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/speech-to-text': 'http://localhost:8000',
      '/text-to-speech': 'http://localhost:8000',
      '/rag-query': 'http://localhost:8000',
      // Empathy Engine endpoints
      '/empathy-rag-query': 'http://localhost:8000',
      '/adaptive-tts': 'http://localhost:8000',
      '/analyze-sentiment': 'http://localhost:8000',
      // Audio query endpoints
      '/rag-audio-query': 'http://localhost:8000',
      '/rag-audio-query-chunk': 'http://localhost:8000',
      '/speech-to-text-chunk': 'http://localhost:8000'
    }
  }
})

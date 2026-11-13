import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// O front fala com a API pelo caminho /api; em desenvolvimento o Vite repassa ao FastAPI.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})

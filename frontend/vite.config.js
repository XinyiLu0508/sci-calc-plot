import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// base: './' 让构建产物可部署到任意子路径（GitHub Pages / Vercel 均适用）
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5173,
    // 本地开发：把 /api 代理到 FastAPI（uvicorn 默认 8000）
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
});

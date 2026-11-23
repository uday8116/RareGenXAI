import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

const localProxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: localProxy,
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
    proxy: localProxy,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.js'],
    css: true,
    include: ['src/**/*.test.{js,jsx}'],
    testTimeout: 10000,
  },
});

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    sourcemap: true // 启用 Source Maps,生产环境请关闭
  },
  plugins: [react()],
  resolve: {
    alias: {
      src: '/src',
    },
  },
});

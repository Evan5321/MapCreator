// @ts-check
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

// 以本配置文件所在目录为站点根，避免从仓库根执行 `vite build` 时找不到 index.html。
const webRoot = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  root: webRoot,
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // 开发时把 API 转发到本地 FastAPI
      '/api': 'http://127.0.0.1:8765',
    },
  },
});

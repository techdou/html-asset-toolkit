import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 单文件打包推荐配置：base 设为相对路径
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    // 减少 code splitting，让单文件打包更可靠
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
})

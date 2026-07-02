# Vite + Vue — 单文件打包指南

## 推荐配置

`vite.config.js` 中设置 `base: './'`：

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',
})
```

## 构建并打包

```bash
npm run build
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build
```

## 输出

```text
dist/index.html -> dist/index.single.html
```

## 常见坑

- **Vue Router**：history 模式离线打开不稳定，课程演示建议用 hash 模式（`createWebHashHistory`）。
- **异步组件**：Vue 的异步组件 `defineAsyncComponent` 依赖动态 import，打包后可能失败。建议在打包构建前将异步组件改为同步导入。
- **图片引用**：Vue SFC 中 `src="@/assets/logo.png"` 经过 Vite 处理后会变成 `/assets/logo-hash.png`，工具会正确内嵌。

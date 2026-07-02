# Vite + React — 单文件打包指南

## 推荐配置

`vite.config.js` 中设置 `base: './'`，让构建产物使用相对路径，便于工具解析：

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './',
})
```

## 构建并打包

```bash
npm run build
# 构建产物在 dist/
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build
```

或一键构建+打包：

```bash
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py .
```

## 输出

```text
dist/index.html      -> dist/index.single.html
dist/assets/         -> 全部内嵌
```

## 常见坑

- **Vite 默认用 `/assets/...` 绝对路径**：设置 `base: './'` 改为相对路径，或保持默认（工具会按 `dist/` 根目录解析）。
- **代码分割**：Vite 默认会分割 chunk。如果打包后动态 import 失败，在 `build.rollupOptions` 中配置 `manualChunks` 为单一 chunk，或使用 `--css-js-mode tag`。
- **动态 import()**：打包后 JS 中的 `import()` 会变成 Data URL，部分浏览器对 Data URL module 的动态 import 支持有限。对于复杂应用，考虑关闭 code splitting。
- **大型依赖**：Three.js、Monaco 等大库会让单文件非常大。先用 `estimate_size.py` 预估：
  ```bash
  python scripts/estimate_size.py dist/index.html
  ```

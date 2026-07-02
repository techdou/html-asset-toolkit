# Create React App (CRA) — 单文件打包指南

## 推荐配置

在 `package.json` 中添加 `homepage` 字段，让 CRA 输出相对路径：

```json
{
  "homepage": "."
}
```

## 构建并打包

```bash
npm run build
# CRA 构建产物在 build/（注意不是 dist/）
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build
```

或显式指定入口（CRA 用 `build/` 目录）：

```bash
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build --entry build/index.html
```

## 输出

```text
build/index.html -> build/index.single.html
build/static/    -> 全部内嵌
```

## 常见坑

- **CRA 默认输出到 `build/` 而非 `dist/`**：wrapper 会自动检测 `build/index.html`。
- **`homepage: "."`**：不设置则 CRA 会用绝对路径 `/static/...`，工具会按 `build/` 根目录解析。设置后变为相对路径。
- **Service Worker**：CRA 默认注册 service worker（workbox）。单文件 HTML 不需要 SW，建议在 `index.js` 中取消 `registerServiceWorker`。
- **SplitChunks**：CRA 默认分割 vendor chunk，打包后多个 JS chunk 会内嵌为 Data URL module，部分浏览器可能不支持 Data URL module 的动态 import。

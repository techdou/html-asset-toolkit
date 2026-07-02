# Vue CLI — 单文件打包指南

## 推荐配置

在 `vue.config.js` 中设置 `publicPath: './'`：

```js
module.exports = {
  publicPath: './',
}
```

## 构建并打包

```bash
npm run build
# Vue CLI 构建产物在 dist/
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build
```

## 输出

```text
dist/index.html -> dist/index.single.html
dist/js/        -> 全部内嵌
dist/css/       -> 全部内嵌
```

## 常见坑

- **Vue Router history 模式**：离线打开时深层路由不稳定。改用 `hash` 模式：
  ```js
  const router = new VueRouter({ mode: 'hash', routes })
  ```
- **`publicPath: './'`**：不设置则输出 `/js/...`、`/css/...` 绝对路径。工具会按 `dist/` 根目录解析，但设为相对路径更保险。
- **Webpack SplitChunks**：Vue CLI 默认分割 runtime chunk。如有问题，在 `configureWebpack` 中禁用 splitChunks。

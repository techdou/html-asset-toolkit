# Webpack 静态配置 — 单文件打包指南

## 推荐配置

`webpack.config.js` 关键点：使用相对 `publicPath`，减少 code splitting：

```js
const path = require('path')

module.exports = {
  mode: 'production',
  entry: './src/index.js',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js',
    publicPath: './',  // 相对路径，便于工具解析
  },
  // 对于课程演示，禁用 code splitting 让单文件更可靠
  optimization: {
    splitChunks: false,
    runtimeChunk: false,
  },
  // ... loaders 和 plugins 按需配置
}
```

## 构建并打包

```bash
npx webpack --config webpack.config.js
# 或 npm run build
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build
```

确保你的 HTML 模板（如 `dist/index.html`）引用了构建输出的 JS/CSS。

## 输出

```text
dist/index.html -> dist/index.single.html
dist/bundle.js  -> 内嵌
dist/*.css      -> 内嵌
```

## 常见坑

- **`publicPath`**：设为 `./` 或空字符串。如果设为 `/`，工具仍会按 `dist/` 根目录解析。
- **Code splitting**：Webpack 默认分割 async chunks。课程演示建议 `splitChunks: false` 减少打包后的 Data URL module 数量。
- **HTMLWebpackPlugin**：确保生成的 HTML 正确引用了 JS/CSS 的文件名。
- **Asset modules**：Webpack 5 的 `asset/resource` 会输出单独文件。对于小图片，改用 `asset/inline`（直接 Base64 内嵌），减少打包层级。

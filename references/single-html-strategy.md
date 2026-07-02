# 单文件 HTML 打包策略

## 场景判断

适合打包成单文件 HTML：

- 课程演示、课堂讲解、百宝箱 HTML。
- 离线交付给老师、学生、甲方试用。
- 互动式富文本页面，不希望携带 `assets/` 文件夹。
- React/Vue/Vite 构建后的纯静态页面，需要作为一个可打开的 HTML 文件交付。

不建议打包成单文件 HTML：

- 正式线上 Web 项目。
- 需要浏览器缓存、CDN、分包加载的大型项目。
- 视频、模型、PDF 特别大的资源型站点。
- 强依赖服务端 API、认证、SSR 的应用。

## 开发版与交付版

### 普通课程 HTML

```text
开发版：
course-demo/
├── index.html
└── assets/

交付版：
course-demo/dist/index.single.html
```

### React/Vue 静态构建

```text
开发版：
my-app/
├── package.json
├── src/
└── public/

构建版：
my-app/dist/index.html
my-app/dist/assets/

交付版：
my-app/dist/index.single.html
```

## 推荐体积阈值

| 单文件体积 | 判断 |
|---:|---|
| 10 MB 以下 | 很适合单文件交付 |
| 10–50 MB | 可接受，适合课程演示 |
| 50–100 MB | 偏重，需要验证打开速度 |
| 100 MB 以上 | 不推荐，除非明确要求 |

## 资源处理建议

| 资源 | 建议 |
|---|---|
| 图片 | 可压缩为 WebP 后嵌入 |
| SVG | 默认 Base64；需要更小体积可用 utf8，但不利于可逆提取 |
| MP3/WAV | 短讲解音频可嵌入 |
| MP4/WebM | 先压缩，再看体积 |
| GLB/STL | 小模型可嵌入，大模型建议 Draco/Meshopt/简模后再嵌入 |
| CSS/JS | 课程和构建产物可嵌入；正式项目不建议 |
| 字体 | 课程演示可嵌入；多字重字体容易变大 |
| PDF | 小 PDF 可嵌入，大 PDF 建议转图片或拆页面 |

## React/Vue 特别建议

- 先执行 `npm run build`，不要直接打包 `src/` 开发文件。
- 优先处理 `dist/index.html` 或 `build/index.html`。
- 若可控制构建配置，建议输出相对路径，例如 Vite `base: './'`、Vue CLI `publicPath: './'`、CRA `homepage: '.'`。
- 若构建产物使用 `/assets/...` 或 `/static/...`，本工具默认会按构建目录解析。
- 若应用使用 history 路由，离线双击打开深层页面不稳定；课程演示更适合 hash 路由。
- 构建后的 sourcemap 不是交付必需资源，通常不需要嵌入。

## 质量检查

最终交付前必须：

1. 打开 `.manifest.json` 看是否有 missing 或 skipped。
2. 运行 `validate_single_html.py`。
3. 本地双击打开单文件 HTML。
4. 检查交互按钮、样式、图片、音视频、模型、字体是否正常。
5. React/Vue 页面要检查路由入口、动态导入 chunk、图标、字体和 public 目录资源。

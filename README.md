# HTML Asset Toolkit 🖼️

> 把课程演示 HTML、离线教学资源、交互式富文本 HTML、百宝箱 HTML，以及 React / Vue / Vite / CRA / Vue CLI / webpack 等静态构建产物，打包成**双击即开的单文件 HTML**。

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![No Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)

---

## 为什么需要它？

在 AI Native 时代，**单文件 HTML 是讲义和演示的最佳载体**：

- 📱 **零依赖传播** — 微信/钉钉/飞书直接发送，无需服务器
- 🎨 **富文本表现力** — 原生支持排版、动画、交互、响应式
- 📦 **资源不丢失** — 图片、音频、视频、3D 模型全部内嵌进 HTML

**但 HTML 讲义有个痛点：图片是外部文件，分发时容易丢失。** 这个工具包解决了这个问题——把 `index.html + assets/` 变成单个自包含的 HTML 文件。

```text
课程 HTML：index.html + assets/  →  dist/index.single.html
React/Vue 构建：npm run build 后的 dist/index.html  →  dist/index.single.html
```

## 核心能力

| 能力 | 脚本 | 说明 |
|------|------|------|
| **资源内嵌** | `inline_assets.py` | 图片/SVG/音频/视频/GLB/STL/字体/PDF/CSS/JS/WASM → Base64 Data URL |
| **标签内联** | `inline_assets.py --css-js-mode tag` | CSS → `<style>`、JS → `<script>`，CSP/ES Module/`file://` 兼容性更好 |
| **前端一键打包** | `package_frontend_build.py` | React/Vue/Vite 项目：构建 → 定位入口 → 内嵌 → 验证，一条命令 |
| **体积预估** | `estimate_size.py` | 打包前预估最终 HTML 大小，不写任何文件 |
| **本地预览** | `serve_preview.py` | 自动检测端口的 HTTP 服务器，可选自动打开浏览器 |
| **验证检查** | `validate_single_html.py` | 扫描残留本地引用、解码嵌入的 CSS/JS 检查内部路径 |
| **资源提取** | `extract_assets.py` | 从单文件 HTML 提取 Base64 资源回文件 |
| **智能重命名** | `rename_extracted_assets.py` | 根据 alt/标题/上下文语义重命名提取的资源 |

## 快速开始

### 场景 A：普通课程 HTML

```text
course-demo/
├── index.html
└── assets/
    ├── images/
    ├── audio/
    └── styles/
```

```bash
cd course-demo
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html --css-js-mode tag
python /path/to/html-asset-toolkit/scripts/validate_single_html.py dist/index.single.html
```

交付：`course-demo/dist/index.single.html` — 单文件，图片音频全部内嵌，直接发送。

### 场景 B：React / Vue 项目一键打包

```bash
cd my-app
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --css-js-mode tag
```

wrapper 自动完成：检测包管理器 → `npm run build` → 定位 `dist/index.html` → 内嵌资源 → 验证。

### 场景 C：预估体积再决定是否打包

```bash
# 预估最终大小（不写文件）
python /path/to/html-asset-toolkit/scripts/estimate_size.py dist/index.html

# 打包前预估，超 50MB 自动中止
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --estimate --max-total-mb 50
```

### 场景 D：浏览器验证

```bash
# 启动本地预览服务器，自动打开浏览器
python /path/to/html-asset-toolkit/scripts/serve_preview.py dist/index.single.html --open
```

## 🏷️ 标签内联模式（推荐）

v3.0.0 新增 `--css-js-mode tag`，**默认推荐使用**：

```html
<!-- data-url 模式（旧默认）-->
<link rel="stylesheet" href="data:text/css;base64,QGJvZHk...">
<script type="module" src="data:text/javascript;base64,aW1wb3J0..."></script>

<!-- tag 模式（推荐）-->
<style>body { margin: 0; }</style>
<script type="module">import { createApp } from ...</script>
```

| 优势 | 说明 |
|------|------|
| ✅ ES Module 可靠 | `<script type="module" src="data:...">` 在部分浏览器静默失败，tag 模式全平台可靠 |
| ✅ CSP 兼容 | 嵌入有 CSP 限制的平台（LMS/企业 wiki/公众号）时，data URL 常被拦截 |
| ✅ `file://` 离线 | 双击打开本地文件时，tag 内联不受跨域限制 |
| ✅ DevTools 可读 | 标签内容直接显示源码，而非 Base64 乱码 |

仅在需要 `extract_assets.py` 可逆提取时才用默认的 `data-url` 模式。详见 [`references/inline-modes.md`](./references/inline-modes.md)。

## 支持的资源类型

| 类别 | 格式 |
|------|------|
| 图片 | PNG, JPG, WebP, GIF, SVG, ICO, BMP, AVIF |
| 音频 | MP3, WAV, OGG, M4A, AAC, FLAC |
| 视频 | MP4, WebM, MOV |
| 3D 模型 | GLB, glTF, STL, OBJ, USDZ |
| 文档 | PDF, JSON, CSV, XML |
| 代码 | CSS, JS, MJS, WASM |
| 字体 | WOFF2, WOFF, TTF, OTF |

## 安装

将整个 `html-asset-toolkit/` 文件夹放到 Agent 的 skills 目录：

```text
.claude/skills/html-asset-toolkit/          # Claude Code
.zcode/skills/html-asset-toolkit/           # ZCode
.agents/skills/html-asset-toolkit/          # 通用
```

**无需安装依赖** — 核心脚本仅用 Python 标准库。可选安装 Pillow 以启用图片 WebP 压缩：

```bash
pip install pillow
```

## 命令速查

### 内嵌资源

```bash
# 普通课程 HTML（推荐 tag 模式）
python scripts/inline_assets.py index.html --css-js-mode tag

# React/Vue 构建产物
python scripts/inline_assets.py dist/index.html --preset react-vue-build --css-js-mode tag

# 图片压缩为 WebP 后嵌入
python scripts/inline_assets.py index.html --image-mode webp --max-width 1800

# 限制体积
python scripts/inline_assets.py index.html --max-asset-mb 25 --max-total-mb 80
```

### 前端一键打包

```bash
python scripts/package_frontend_build.py .                          # 完整构建+打包
python scripts/package_frontend_build.py . --skip-build             # 仅打包已有 build
python scripts/package_frontend_build.py . --css-js-mode tag         # 推荐：标签内联
python scripts/package_frontend_build.py . --estimate --max-total-mb 50  # 预估+超限中止
```

### 预估 / 验证 / 预览

```bash
python scripts/estimate_size.py index.html              # 预估体积
python scripts/estimate_size.py index.html --json       # JSON 报告
python scripts/validate_single_html.py dist/index.single.html
python scripts/validate_single_html.py dist/index.single.html --strict
python scripts/serve_preview.py dist/index.single.html --open  # 本地预览
```

### 提取 / 重命名

```bash
python scripts/extract_assets.py dist/index.single.html --output-dir extracted-assets --replace
python scripts/rename_extracted_assets.py extracted-assets --name-from auto
```

## 输出约定

```text
普通源 HTML：
  course/index.html      →  course/dist/index.single.html
  course/chapter01.html  →  course/dist/chapter01.single.html

前端构建产物（输出在同级，避免 dist/dist/）：
  app/dist/index.html    →  app/dist/index.single.html
  app/build/index.html   →  app/build/index.single.html
```

## 自测

```bash
cd html-asset-toolkit
python tests/smoke_test.py
# 覆盖：普通HTML打包、React/Vue build打包、标签内联、体积预估、验证、预览服务器
```

## 文档索引

| 文档 | 内容 |
|------|------|
| [`SKILL.md`](./SKILL.md) | Agent 技能定义、触发条件、执行契约 |
| [`references/inline-modes.md`](./references/inline-modes.md) | data-url vs tag 模式选择指南 |
| [`references/parameters.md`](./references/parameters.md) | 全部 CLI 参数参考 |
| [`references/react-vue-build-packaging.md`](./references/react-vue-build-packaging.md) | 前端构建打包工作流 |
| [`references/js-asset-detection.md`](./references/js-asset-detection.md) | Vite/esbuild JS 资源检测 |
| [`references/quality-gate.md`](./references/quality-gate.md) | 交付前检查清单 |
| [`references/troubleshooting.md`](./references/troubleshooting.md) | 常见问题排查 |
| [`references/mime-data-url-matrix.md`](./references/mime-data-url-matrix.md) | MIME 类型速查 |
| [`references/single-html-strategy.md`](./references/single-html-strategy.md) | 单文件打包策略 |
| [`references/threejs-model-recipes.md`](./references/threejs-model-recipes.md) | GLB/STL 加载方案 |
| [`examples/frameworks/`](./examples/frameworks/) | Vite/Vue/CRA/webpack 框架示例 |
| [`CHANGELOG.md`](./CHANGELOG.md) | 版本更新记录 |

## 使用建议

| 场景 | 建议 |
|------|------|
| 课程演示、教学交付、百宝箱 HTML | ✅ 内嵌资源，交付单文件 |
| React/Vue 课程 Demo | ✅ `npm run build` 后用 `--css-js-mode tag` 打包 |
| 正式线上 Web 项目 | ❌ 不建议内嵌，保留 assets 外联 |
| 大 MP4 / GLB / STL | ⚠️ 先压缩，再用 `estimate_size.py` 预估 |
| 超过 100 MB 的单 HTML | ⚠️ 重型交付，打开会慢 |

## 技术约束

- **零硬依赖** — 核心脚本仅用 Python 标准库（`http.server`、`base64`、`re`、`argparse`）
- **确定性输出** — 相同输入产生相同输出，适合 Agent 程序化调用
- **向后兼容** — v3.0.0 新功能均有默认值，默认行为 = v2.6.0
- **递归处理** — CSS 内的 `url()`/`@import`、JS 内的资源字符串都会递归内嵌
- **Vite/esbuild 兼容** — 识别压缩后的反引号模板字面量路径 `` `/buildings/a.jpg` ``

## License

[MIT](./LICENSE)

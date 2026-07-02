# HTML Asset Toolkit Skill

> **v3.0.0 新增**：标签内联模式（`--css-js-mode tag`）、体积预估（`estimate_size.py`）、本地预览服务器（`serve_preview.py`）、框架专项示例（`examples/frameworks/`）。

用于把课程演示 HTML、离线教学资源、交互式富文本 HTML、百宝箱 HTML，以及 React / Vue / Vite / Create React App / Vue CLI / webpack 等静态构建产物，打包成可以离线打开的单文件 HTML。

核心目标：

```text
普通课程 HTML：index.html + assets/ -> dist/index.single.html
React/Vue 构建产物：npm run build 后的 dist/index.html 或 build/index.html -> index.single.html
```

支持图片、SVG、MP3、MP4、WebM、GLB、STL、字体、PDF、CSS、JS、WASM 等资源的 Base64/Data URL 内嵌。v2.6.0 重点增强了 Vite/esbuild 打包后 JS 中反引号模板字符串路径的识别，例如 `` `/buildings/buildingA.jpg` ``。

## 安装位置

将整个 `html-asset-toolkit/` 文件夹放到 Claude / OpenClaw / Codex 支持的 skills 目录中，例如：

```text
.claude/skills/html-asset-toolkit/
```

目录根部必须保留：

```text
html-asset-toolkit/SKILL.md
```

## 最常用场景 A：普通课程 HTML

你的课程项目：

```text
course-demo/
├── index.html
└── assets/
```

Skill 工具：

```text
/path/to/html-asset-toolkit/
```

运行：

```bash
cd course-demo
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html
python /path/to/html-asset-toolkit/scripts/validate_single_html.py dist/index.single.html
```

最终交付：

```text
course-demo/dist/index.single.html
```

这里的 `dist/` 是当前课程项目的子目录，不是 Skill 自己的目录。

## 最常用场景 B：React / Vue 项目一键构建并打包

你的前端项目：

```text
my-app/
├── package.json
├── src/
└── public/
```

推荐直接运行包装脚本：

```bash
cd my-app
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py .
```

该脚本会自动执行：

```text
1. 检测 npm / pnpm / yarn / bun
2. 运行构建命令，默认 npm run build
3. 查找 dist/index.html、build/index.html 或 out/index.html
4. 把构建产物中的 assets、CSS、JS、图片、字体、媒体等资源嵌入 HTML
5. 输出 index.single.html
6. 运行 validate_single_html.py 验证
```

常见输出：

```text
Vite / Vue CLI：my-app/dist/index.single.html
Create React App：my-app/build/index.single.html
静态导出：my-app/out/index.single.html
```

## 最常用场景 C：React / Vue 已经 build 好，只负责打包

Vite / Vue CLI 常见输出：

```text
my-app/
└── dist/
    ├── index.html
    └── assets/
        ├── index-xxxxx.js
        ├── index-xxxxx.css
        └── logo-xxxxx.svg
```

运行：

```bash
cd my-app
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build
```

或者显式处理入口：

```bash
python /path/to/html-asset-toolkit/scripts/inline_assets.py dist/index.html --preset react-vue-build
python /path/to/html-asset-toolkit/scripts/validate_single_html.py dist/index.single.html
```

Create React App：

```bash
python /path/to/html-asset-toolkit/scripts/inline_assets.py build/index.html --preset create-react-app
python /path/to/html-asset-toolkit/scripts/validate_single_html.py build/index.single.html
```

## 输出规则

### 1. 普通源 HTML

```text
输入 HTML 所在目录 / dist / <原文件名>.single.html
```

例如：

```text
course-demo/index.html     -> course-demo/dist/index.single.html
course-demo/chapter01.html -> course-demo/dist/chapter01.single.html
course-demo/demo.html      -> course-demo/dist/demo.single.html
```

### 2. 前端构建产物 HTML

如果输入文件已经位于 `dist/`、`build/` 或 `out/` 生产构建目录下，默认输出到同级目录，避免生成 `dist/dist/`：

```text
my-app/dist/index.html  -> my-app/dist/index.single.html
my-app/build/index.html -> my-app/build/index.single.html
my-app/out/index.html   -> my-app/out/index.single.html
```

`public/index.html` 不再作为构建产物自动选择；它通常是源模板。确实需要处理时，请显式传 `--entry public/index.html`，并按普通/泛型 HTML 验证结果。

## React / Vue 构建支持能力

可处理 HTML 中的构建资源引用：

```html
<script type="module" src="/assets/index-xxxxx.js"></script>
<link rel="stylesheet" href="/assets/index-xxxxx.css">
<link rel="icon" href="/favicon.ico">
```

也会处理 CSS / JS 内部资源：

```css
@import "./theme.css";
.hero { background-image: url('/assets/bg-xxxxx.png'); }
@font-face { src: url('/assets/font-xxxxx.woff2'); }
```

```js
const logo = "/assets/logo-xxxxx.svg";
const model = "/assets/model-xxxxx.glb";
import("/assets/chunk-xxxxx.js");
```

也支持 Vite/esbuild 压缩后常见的静态模板字符串路径：

```js
var BUILDING_IMAGES=[`/buildings/buildingA.jpg`,`/buildings/buildingB.jpg`];
```

但动态模板字符串无法静态解析：

```js
const img = `/buildings/${buildingName}.jpg`;
```

这种情况建议改成静态路径映射表，或者通过 bundler import 显式引入资源。

对于 Vite、Vue CLI、Create React App 中常见的 `/assets/...`、`/static/...`、`/css/...`、`/js/...` 根路径，工具会按构建目录解析，而不是按系统根目录解析。

## 常用命令

### 一键构建并打包前端项目

```bash
python scripts/package_frontend_build.py .
python scripts/package_frontend_build.py . --skip-build
python scripts/package_frontend_build.py . --build-command "npm run build"
python scripts/package_frontend_build.py . --entry dist/index.html
```

### 指定输出路径

相对 `--out` 会按输入 HTML 所在目录解析：

```bash
python scripts/inline_assets.py index.html --out dist/index.single.html
```

### 指定根路径解析目录

当构建产物中的资源使用 `/assets/...` 根路径，但 HTML 不在站点根目录时，使用 `--root-dir`：

```bash
python scripts/inline_assets.py dist/index.html --root-dir dist
```

默认情况下，`dist/index.html` 会自动把 `/assets/app.js` 解析为 `dist/assets/app.js`。

### 只嵌入指定格式

```bash
python scripts/inline_assets.py index.html --include-ext .png,.jpg,.svg,.mp3,.mp4,.glb,.stl,.css,.js
```

### 限制体积

```bash
python scripts/inline_assets.py index.html --max-asset-mb 25 --max-total-mb 80
```

### 图片压缩为 WebP 后嵌入

```bash
pip install pillow
python scripts/inline_assets.py index.html --image-mode webp --max-width 1800 --max-height 1800 --webp-quality 82
```

### 提取 Base64 资源

```bash
python scripts/extract_assets.py dist/index.single.html --output-dir extracted-assets --replace
python scripts/rename_extracted_assets.py extracted-assets --name-from auto
```

### 验证单文件 HTML

```bash
python scripts/validate_single_html.py dist/index.single.html
python scripts/validate_single_html.py dist/index.single.html --json
```

验证器不仅检查 HTML 表层引用，也会解码嵌入后的 `data:text/javascript;base64,...` 和 `data:text/css;base64,...`，检查里面是否还残留 `/assets/...`、`/buildings/...` 等本地资源路径。

## 使用建议

| 场景 | 建议 |
|---|---|
| 课程演示、教学交付、百宝箱 HTML | 可以内嵌资源，交付单文件 |
| 正式线上 Web 项目 | 不建议内嵌，保留 assets 外联 |
| React/Vue 课程 Demo | `npm run build` 后打包 `dist/index.html` 或 `build/index.html` |
| 大 MP4 / GLB / STL | 先压缩，再决定是否内嵌 |
| 超过 100 MB 的单 HTML | 视为重型交付，打开会慢 |

## 快速自测

```bash
cd html-asset-toolkit
python tests/smoke_test.py  # 覆盖普通 HTML、React/Vue build、Vite 反引号路径
```

## v2.6.0 稳健性规则

### React / Vue 构建产物入口

`package_frontend_build.py` 默认只自动查找生产构建入口：

```text
dist/index.html
build/index.html
out/index.html
```

`public/index.html` 不再自动选择，因为它在 React / Vue / Vite 项目里通常是源模板或静态源文件，不一定是 `npm run build` 后的产物。如确实要处理它，必须显式传入：

```bash
python scripts/package_frontend_build.py . --skip-build --entry public/index.html
```

### wrapper 路径解析

在 `package_frontend_build.py` 中，`--root-dir` 和 `--assets-root` 的相对路径按项目根目录解析：

```bash
cd my-app
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build --entry dist/index.html --root-dir dist
```

这里的 `--root-dir dist` 表示 `my-app/dist`，不会被错误解析为 `my-app/dist/dist`。

### 严格模式与 warning

```bash
python scripts/package_frontend_build.py . --skip-build --entry dist/index.html --strict
```

`--strict` 会让：

1. `inline_assets.py` 对缺失或超限本地资源返回失败；
2. `validate_single_html.py` 对 warning 返回失败；
3. wrapper 在 summary 中输出 `validation_warning_count` 和 `validation_warnings`。

也可以只让验证 warning 失败：

```bash
python scripts/package_frontend_build.py . --skip-build --entry dist/index.html --fail-on-warning
```


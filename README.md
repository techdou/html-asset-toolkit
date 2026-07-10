# HTML Asset Toolkit 🖼️

> Package HTML and static frontend builds into one portable single-file HTML — double-click to open, zero external files.
>
> 把课程演示 HTML、离线教学资源、交互式富文本 HTML、百宝箱 HTML，以及 React / Vue / Vite / CRA / Vue CLI / webpack 等静态构建产物，打包成**双击即开的单文件 HTML**。

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![No Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)
[![Version](https://img.shields.io/badge/version-v4.2.0-orange)](./CHANGELOG.md)

---

## English

### Why?

In the AI-native era, **single-file HTML is the best carrier for lectures and demos**:

- 📱 **Zero-dependency distribution** — send via WeChat / DingTalk / Feishu / email, no server needed.
- 🎨 **Rich media** — native support for typography, animation, interaction, responsive layout.
- 📦 **No lost assets** — images, audio, video, 3D models all embedded inside one HTML.

**The pain point: HTML lectures reference external files that get lost when distributed.** This toolkit solves it — turn `index.html + assets/` into one self-contained HTML file.

```text
Course HTML:   index.html + assets/  →  dist/index.single.html
React/Vue:     npm run build → dist/index.html  →  dist/index.single.html
```

### Core capabilities

| Capability | Script | Description |
|---|---|---|
| **Asset inlining** | `inline_assets.py` | Image/SVG/audio/video/GLB/STL/fonts/PDF/CSS/JS/WASM → Base64 Data URL |
| **Tag inlining** | `inline_assets.py --css-js-mode tag` | CSS → `<style>`, JS → `<script>`; better CSP / ES Module / `file://` compatibility |
| **CSS/JS-only inlining** | `inline_assets.py --no-js` / `--no-css` / `--css-prepend` | Inline only CSS or only JS, or prepend a reset to each stylesheet. Replaces the legacy `inline-html-assets` skill. |
| **Frontend packaging** | `package_frontend_build.py` | React/Vue/Vite: build → locate entry → inline → validate, one command |
| **Size estimation** | `estimate_size.py` | Preview final HTML size before embedding, writes nothing |
| **Local preview** | `serve_preview.py` | HTTP server with auto port detection, optional auto-open browser |
| **Validation** | `validate_single_html.py` | Scan remaining local refs, decode embedded CSS/JS to check internal paths |
| **Asset extraction** | `extract_assets.py` | Extract Base64 assets back to editable files |
| **Inline block extraction** | `extract_style_script.py` | Split inline `<style>`/`<script>` into external `.css`/`.js`; complements `extract_assets.py` |
| **Smart rename** | `rename_extracted_assets.py` | Rename extracted assets by alt/title/context; `--update-html` rewrites references in lockstep |

### Quick start

**Scenario A — Plain course HTML:**

```bash
cd course-demo
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html --css-js-mode tag
python /path/to/html-asset-toolkit/scripts/validate_single_html.py dist/index.single.html
```

Deliverable: `course-demo/dist/index.single.html` — single file, all images/audio embedded.

**Scenario B — React/Vue one-command packaging:**

```bash
cd my-app
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --css-js-mode tag
```

The wrapper auto-detects the package manager → runs `npm run build` → locates `dist/index.html` → inlines assets → validates.

**Scenario C — Estimate size before packaging:**

```bash
python /path/to/html-asset-toolkit/scripts/estimate_size.py dist/index.html
# Abort via wrapper if projected size exceeds limit
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --estimate --max-total-mb 50
```

**Scenario D — Browser verification:**

```bash
python /path/to/html-asset-toolkit/scripts/serve_preview.py dist/index.single.html --open
```

**Scenario E — Inline only CSS or only JS** (legacy `inline-html-assets` use case):

```bash
# Inline only CSS, keep <script src> as external references
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html --css-js-mode tag --no-js

# Prepend a CSS reset to every inlined stylesheet
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html --css-js-mode tag --css-prepend "*{box-sizing:border-box}"
```

> ℹ️ **Merged skill**: As of v4.2.0 the standalone `inline-html-assets` skill has been retired. Its CSS/JS-only inlining capability is fully covered here via `--no-css` / `--no-js` / `--css-prepend`, which work in both `data-url` and `tag` mode and compose with `--include-ext`. See [CHANGELOG.md](./CHANGELOG.md).

### Tag-inline mode (recommended)

`--css-js-mode tag` is the **recommended default** inlining mode:

```html
<!-- data-url mode (legacy default) -->
<link rel="stylesheet" href="data:text/css;base64,QGJvZHk...">
<script type="module" src="data:text/javascript;base64,aW1wb3J0..."></script>

<!-- tag mode (recommended) -->
<style>body { margin: 0; }</style>
<script type="module">import { createApp } from ...</script>
```

| Advantage | Why |
|---|---|
| ✅ ES Module reliable | `<script type="module" src="data:...">` silently fails in some browsers; tag mode is reliable everywhere |
| ✅ CSP compatible | data URLs are often blocked on CSP-restricted platforms (LMS / enterprise wiki / WeChat OA) |
| ✅ `file://` offline | No cross-origin restrictions when opening local files by double-click |
| ✅ DevTools readable | Tag contents show source directly, not Base64 gibberish |

Only keep the default `data-url` when you need `extract_assets.py` reversible extraction. See [`references/inline-modes.md`](./references/inline-modes.md).

---

## 中文

### 为什么需要它？

在 AI Native 时代，**单文件 HTML 是讲义和演示的最佳载体**：

- 📱 **零依赖传播** — 微信/钉钉/飞书直接发送，无需服务器
- 🎨 **富文本表现力** — 原生支持排版、动画、交互、响应式
- 📦 **资源不丢失** — 图片、音频、视频、3D 模型全部内嵌进 HTML

**但 HTML 讲义有个痛点：图片是外部文件，分发时容易丢失。** 这个工具包解决了这个问题——把 `index.html + assets/` 变成单个自包含的 HTML 文件。

```text
课程 HTML：index.html + assets/  →  dist/index.single.html
React/Vue：npm run build 后的 dist/index.html  →  dist/index.single.html
```

### 核心能力

| 能力 | 脚本 | 说明 |
|---|---|---|
| **资源内嵌** | `inline_assets.py` | 图片/SVG/音频/视频/GLB/STL/字体/PDF/CSS/JS/WASM → Base64 Data URL |
| **标签内联** | `inline_assets.py --css-js-mode tag` | CSS → `<style>`、JS → `<script>`，CSP/ES Module/`file://` 兼容性更好 |
| **仅内联 CSS/JS** | `inline_assets.py --no-js` / `--no-css` / `--css-prepend` | 只内联 CSS 或只内联 JS，或给每个内联样式表注入 reset。取代已下线的 `inline-html-assets` 技能 |
| **前端一键打包** | `package_frontend_build.py` | React/Vue/Vite 项目：构建 → 定位入口 → 内嵌 → 验证，一条命令 |
| **体积预估** | `estimate_size.py` | 打包前预估最终 HTML 大小，不写任何文件 |
| **本地预览** | `serve_preview.py` | 自动检测端口的 HTTP 服务器，可选自动打开浏览器 |
| **验证检查** | `validate_single_html.py` | 扫描残留本地引用、解码嵌入的 CSS/JS 检查内部路径 |
| **资源提取** | `extract_assets.py` | 从单文件 HTML 提取 Base64 资源回文件 |
| **内联块提取** | `extract_style_script.py` | 把内联 `<style>`/`<script>` 拆成外部 `.css`/`.js`，与 `extract_assets.py` 互补 |
| **智能重命名** | `rename_extracted_assets.py` | 根据 alt/标题/上下文语义重命名提取的资源，`--update-html` 同步改写引用 |

### 快速开始

**场景 A — 普通课程 HTML：**

```bash
cd course-demo
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html --css-js-mode tag
python /path/to/html-asset-toolkit/scripts/validate_single_html.py dist/index.single.html
```

交付：`course-demo/dist/index.single.html` — 单文件，图片音频全部内嵌，直接发送。

**场景 B — React / Vue 项目一键打包：**

```bash
cd my-app
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --css-js-mode tag
```

wrapper 自动完成：检测包管理器 → `npm run build` → 定位 `dist/index.html` → 内嵌资源 → 验证。

**场景 C — 预估体积再决定是否打包：**

```bash
python /path/to/html-asset-toolkit/scripts/estimate_size.py dist/index.html
# 打包前预估，超限自动中止
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --estimate --max-total-mb 50
```

**场景 D — 浏览器验证：**

```bash
python /path/to/html-asset-toolkit/scripts/serve_preview.py dist/index.single.html --open
```

**场景 E — 只内联 CSS 或只内联 JS**（原 `inline-html-assets` 的场景）：

```bash
# 只内联 CSS，保留 <script src> 外链不动
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html --css-js-mode tag --no-js

# 给每个内联样式表注入 CSS reset
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html --css-js-mode tag --css-prepend "*{box-sizing:border-box}"
```

> ℹ️ **技能合并**：自 v4.2.0 起原独立的 `inline-html-assets` 技能已下线。其「只内联 CSS/JS」的能力已完整并入本工具包，通过 `--no-css` / `--no-js` / `--css-prepend` 实现，在 data-url 和 tag 模式下都生效，并可与 `--include-ext` 组合。详见 [CHANGELOG.md](./CHANGELOG.md)。

### 🏷️ 标签内联模式（推荐）

`--css-js-mode tag` 是**默认推荐**的内嵌方式：

```html
<!-- data-url 模式（旧默认）-->
<link rel="stylesheet" href="data:text/css;base64,QGJvZHk...">
<script type="module" src="data:text/javascript;base64,aW1wb3J0..."></script>

<!-- tag 模式（推荐）-->
<style>body { margin: 0; }</style>
<script type="module">import { createApp } from ...</script>
```

| 优势 | 说明 |
|---|---|
| ✅ ES Module 可靠 | `<script type="module" src="data:...">` 在部分浏览器静默失败，tag 模式全平台可靠 |
| ✅ CSP 兼容 | 嵌入有 CSP 限制的平台（LMS/企业 wiki/公众号）时，data URL 常被拦截 |
| ✅ `file://` 离线 | 双击打开本地文件时，tag 内联不受跨域限制 |
| ✅ DevTools 可读 | 标签内容直接显示源码，而非 Base64 乱码 |

仅在需要 `extract_assets.py` 可逆提取时才用默认的 `data-url` 模式。详见 [`references/inline-modes.md`](./references/inline-modes.md)。

---

## Supported asset types / 支持的资源类型

| Category / 类别 | Formats / 格式 |
|---|---|
| Image / 图片 | PNG, JPG, JPEG, WebP, GIF, SVG, ICO, BMP, AVIF |
| Audio / 音频 | MP3, WAV, OGG, OGA, M4A, AAC, FLAC |
| Video / 视频 | MP4, WebM, MOV, M4V |
| 3D Model / 3D 模型 | GLB, glTF, STL, OBJ, USDZ |
| Document / 文档 | PDF, JSON, CSV, XML, TXT |
| Code / 代码 | CSS, JS, MJS, WASM |
| Font / 字体 | WOFF2, WOFF, TTF, OTF, EOT |

Auxiliary: MTL (material files for OBJ models). Total **40 extensions** across 7 categories.

## Output convention / 输出约定

```text
Plain source HTML / 普通源 HTML：
  course/index.html      →  course/dist/index.single.html
  course/chapter01.html  →  course/dist/chapter01.single.html

Frontend build output / 前端构建产物（输出在同级，避免 dist/dist/）：
  app/dist/index.html    →  app/dist/index.single.html
  app/build/index.html   →  app/build/index.single.html
  app/out/index.html     →  app/out/index.single.html
```

## Command reference / 命令速查

### Inlining / 内嵌资源

```bash
# Plain course HTML (tag mode recommended)
python scripts/inline_assets.py index.html --css-js-mode tag

# React/Vue build output
python scripts/inline_assets.py dist/index.html --preset react-vue-build --css-js-mode tag

# Image compression to WebP before embedding
python scripts/inline_assets.py index.html --image-mode webp --max-width 1800

# Size limits
python scripts/inline_assets.py index.html --max-asset-mb 25 --max-total-mb 80
```

### Frontend packaging / 前端一键打包

```bash
python scripts/package_frontend_build.py .                          # Full build + package
python scripts/package_frontend_build.py . --skip-build             # Package existing build only
python scripts/package_frontend_build.py . --css-js-mode tag         # Recommended: tag inlining
python scripts/package_frontend_build.py . --estimate --max-total-mb 50  # Estimate + abort if over
```

### Estimate / Validate / Preview / 预估 / 验证 / 预览

```bash
python scripts/estimate_size.py index.html              # Estimate size
python scripts/estimate_size.py index.html --json       # JSON report
python scripts/validate_single_html.py dist/index.single.html
python scripts/validate_single_html.py dist/index.single.html --strict
python scripts/serve_preview.py dist/index.single.html --open  # Local preview
```

### Extract / Rename / 提取 / 重命名

```bash
# Extract Base64 assets back to files
python scripts/extract_assets.py dist/index.single.html --output-dir extracted-assets --replace

# Split inline <style>/<script> into external .css/.js (complements the above)
python scripts/extract_style_script.py index.html

# Smart rename, --update-html rewrites references to avoid broken links
python scripts/rename_extracted_assets.py extracted-assets --name-from auto --update-html page.externalized.html
```

## Installation / 安装

Place the entire `html-asset-toolkit/` folder into your Agent's skills directory:

```text
.agents/skills/html-asset-toolkit/          # Universal (recommended, cross-tool)
.zcode/skills/html-asset-toolkit/           # ZCode
.claude/skills/html-asset-toolkit/          # Claude Code
```

**No dependencies required** — core scripts use only the Python standard library. Optionally install Pillow to enable WebP image compression:

```bash
pip install pillow
```

Requires **Python 3.10+**.

## Testing / 自测

```bash
cd html-asset-toolkit
python tests/smoke_test.py
```

Covers: plain HTML packaging, React/Vue build packaging, tag inlining, size estimation, validation, preview server, inline block extraction, near_text naming, HTML-aware rename (including scoped-rewrite regression check). 19 test cases total.

## Documentation / 文档

| Document | Content |
|---|---|
| [`SKILL.md`](./SKILL.md) | Agent skill definition, trigger conditions, execution contract / Agent 技能定义、触发条件、执行契约 |
| [`references/inline-modes.md`](./references/inline-modes.md) | data-url vs tag mode selection guide / data-url vs tag 模式选择指南 |
| [`references/parameters.md`](./references/parameters.md) | Full CLI parameter reference / 全部 CLI 参数参考 |
| [`references/react-vue-build-packaging.md`](./references/react-vue-build-packaging.md) | Frontend build packaging workflow / 前端构建打包工作流 |
| [`references/js-asset-detection.md`](./references/js-asset-detection.md) | Vite/esbuild JS asset detection / Vite/esbuild JS 资源检测 |
| [`references/quality-gate.md`](./references/quality-gate.md) | Pre-handoff checklist / 交付前检查清单 |
| [`references/troubleshooting.md`](./references/troubleshooting.md) | Common issues / 常见问题排查 |
| [`references/mime-data-url-matrix.md`](./references/mime-data-url-matrix.md) | MIME type quick reference / MIME 类型速查 |
| [`references/single-html-strategy.md`](./references/single-html-strategy.md) | Single-file packaging strategy / 单文件打包策略 |
| [`references/threejs-model-recipes.md`](./references/threejs-model-recipes.md) | GLB/STL loading recipes / GLB/STL 加载方案 |
| [`examples/frameworks/`](./examples/frameworks/) | Vite/Vue/CRA/webpack framework examples / 框架示例 |
| [`CHANGELOG.md`](./CHANGELOG.md) | Version history / 版本更新记录 |

## Usage guidelines / 使用建议

| Scenario / 场景 | Recommendation / 建议 |
|---|---|
| Course demos, teaching handoff, 百宝箱 HTML | ✅ Inline assets, deliver single file / 内嵌资源，交付单文件 |
| React/Vue course demo | ✅ `npm run build` then package with `--css-js-mode tag` |
| Production online web project / 正式线上 Web 项目 | ❌ Don't inline; keep assets external / 不建议内嵌，保留 assets 外联 |
| Large MP4 / GLB / STL | ⚠️ Compress first, then estimate with `estimate_size.py` / 先压缩，再预估 |
| Single HTML over 100 MB | ⚠️ Heavy artifact; will open slowly / 重型交付，打开会慢 |

## Technical constraints / 技术约束

- **Zero hard dependencies / 零硬依赖** — core scripts use only Python standard library (`http.server`, `base64`, `re`, `argparse`)
- **Deterministic output / 确定性输出** — same input produces same output, suitable for Agent programmatic invocation
- **Backward compatible / 向后兼容** — new parameters all have sensible defaults; since v4 the rename separator defaults to `-` (pass `--separator _` to restore the pre-v4 style)
- **Recursive processing / 递归处理** — `url()`/`@import` inside CSS and asset strings inside JS are recursively inlined
- **Vite/esbuild compatible / Vite/esbuild 兼容** — recognizes minified backtick template-literal paths like `` `/buildings/a.jpg` ``

## Contributing / 贡献

Issues and Pull Requests are welcome at [github.com/techdou/html-asset-toolkit](https://github.com/techdou/html-asset-toolkit).

When contributing code:

1. Run `python tests/smoke_test.py` before submitting — all cases must pass.
2. Keep scripts dependency-free (Python standard library only); Pillow remains optional.
3. Update `CHANGELOG.md` under the appropriate version section.
4. Documentation lives in `references/`; keep `SKILL.md` under 500 lines (progressive disclosure).

欢迎在 [github.com/techdou/html-asset-toolkit](https://github.com/techdou/html-asset-toolkit) 提交 Issue 和 PR。贡献代码时：

1. 提交前运行 `python tests/smoke_test.py`，全部用例必须通过。
2. 保持脚本零依赖（仅 Python 标准库），Pillow 仍为可选。
3. 在 `CHANGELOG.md` 对应版本节下更新记录。
4. 详细文档放在 `references/`，`SKILL.md` 控制在 500 行以内（progressive disclosure）。

## License

[MIT](./LICENSE) © 2025 techdou

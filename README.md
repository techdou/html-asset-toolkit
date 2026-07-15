# HTML Asset Toolkit 🖼️

> Package HTML and static frontend builds into one portable single-file HTML — double-click to open, zero external files.
>
> 把课程演示 HTML、离线教学资源、交互式富文本 HTML、百宝箱 HTML，以及 React / Vue / Vite / CRA / Vue CLI / webpack 等静态构建产物，打包成**双击即开的单文件 HTML**。

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![No Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)
[![Version](https://img.shields.io/badge/version-v4.3.0-orange)](./CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-13%20passing-brightgreen)](./tests/smoke_test.py)

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
| **Tag inlining** | `inline_assets.py --css-js-mode tag` | CSS → `<style>`, JS → `<script>`; better CSP / ES Module / `file://` compatibility. Auto-escapes `</script>`/`</style>` in content |
| **CSS/JS-only inlining** | `inline_assets.py --no-js` / `--no-css` / `--css-prepend` | Inline only CSS or only JS, or prepend a reset to each stylesheet. Replaces the legacy `inline-html-assets` skill. |
| **Frontend packaging** | `package_frontend_build.py` | React/Vue/Vite: build → locate entry → inline → validate, one command |
| **Next.js export** | `inline_assets.py --preset nextjs` | Auto-resolves `_next/static/` paths from bare `static/` refs; no manual symlink |
| **Draco offline** | `inline_assets.py --fetch-cdn draco` | Download Three.js Draco decoders into the build dir for offline 3D models |
| **Size estimation** | `estimate_size.py` | Preview final HTML size before embedding, writes nothing |
| **Local preview** | `serve_preview.py` | HTTP server with auto port detection, optional auto-open browser |
| **Validation** | `validate_single_html.py` | Scan remaining local refs, decode embedded CSS/JS to check internal paths; detect unescaped `</script>` and Draco CDN dependencies |
| **Asset extraction** | `extract_assets.py` | Extract Base64 assets back to editable files |
| **Inline block extraction** | `extract_style_script.py` | Split inline `<style>`/`<script>` into external `.css`/`.js`; complements `extract_assets.py` |
| **Smart rename** | `rename_extracted_assets.py` | Rename extracted assets by alt/title/context; `--update-html` rewrites references in lockstep |

### Quick start

**Scenario A — Plain course HTML:**

```bash
python scripts/inline_assets.py index.html --css-js-mode tag
python scripts/validate_single_html.py dist/index.single.html
```

**Scenario B — React/Vue/Vite project (one command):**

```bash
python scripts/package_frontend_build.py . --css-js-mode tag
```

The wrapper detects the package manager, runs the build, locates the entry (`dist/`, `build/`, or `out/`), inlines, and validates.

**Scenario C — Existing build output:**

```bash
python scripts/inline_assets.py dist/index.html --preset react-vue-build --css-js-mode tag
python scripts/validate_single_html.py dist/index.single.html
```

**Scenario D — Next.js static export:**

```bash
python scripts/inline_assets.py out/index.html --preset nextjs --css-js-mode tag
```

Dynamic-import chunks (`static/chunks/x.js`) are auto-resolved under `_next/` — no manual symlink.

> ℹ️ **Merged skill**: As of v4.2.0 the standalone `inline-html-assets` skill has been retired. Its CSS/JS-only inlining capability is fully covered here via `--no-css` / `--no-js` / `--css-prepend`, which work in both `data-url` and `tag` mode and compose with `--include-ext`. See [CHANGELOG.md](./CHANGELOG.md).

### Tag-inline mode (recommended)

```bash
python scripts/inline_assets.py index.html --css-js-mode tag
```

Replaces `<link rel="stylesheet">` with `<style>` and `<script src>` with inline `<script>`. Better for CSP / ES Module / `file://` compatibility. Since v4.3.0, any `</script>` / `</style>` inside the inlined content is auto-escaped as `<\/script>` / `<\/style>` so the HTML parser cannot close the tag early — essential for React/Vue minified runtimes. The validator reports an unescaped closing tag as a hard error.

---

## 中文

### 为什么需要？

- 📱 **零依赖分发** — 微信 / 钉钉 / 飞书 / 邮件直接发，无需服务器。
- 🎨 **富媒体** — 原生支持排版、动画、交互、响应式。
- 📦 **资源不丢** — 图片、音频、视频、3D 模型全部嵌入一个 HTML。

**痛点：HTML 课件引用的外部文件在分发时丢失。** 本工具把 `index.html + assets/` 打包成一个自包含 HTML 文件。

```text
课程 HTML：   index.html + assets/  →  dist/index.single.html
React/Vue：   npm run build → dist/index.html  →  dist/index.single.html
```

### 核心能力

| 能力 | 脚本 | 说明 |
|---|---|---|
| **资源内嵌** | `inline_assets.py` | 图片/SVG/音频/视频/GLB/STL/字体/PDF/CSS/JS/WASM → Base64 Data URL |
| **标签内联** | `inline_assets.py --css-js-mode tag` | CSS → `<style>`、JS → `<script>`，CSP/ES Module/`file://` 兼容性更好；自动转义内容里的 `</script>`/`</style>` |
| **仅内联 CSS/JS** | `inline_assets.py --no-js` / `--no-css` / `--css-prepend` | 只内联 CSS 或只内联 JS，或给每个内联样式表注入 reset。取代已下线的 `inline-html-assets` 技能 |
| **前端一键打包** | `package_frontend_build.py` | React/Vue/Vite 项目：构建 → 定位入口 → 内嵌 → 验证，一条命令 |
| **Next.js 导出** | `inline_assets.py --preset nextjs` | 自动从 `_next/static/` 解析裸 `static/` 引用，无需手动 symlink |
| **Draco 离线** | `inline_assets.py --fetch-cdn draco` | 下载 Three.js Draco 解码器到构建目录，支持离线 3D 模型 |
| **体积预估** | `estimate_size.py` | 打包前预估最终 HTML 大小，不写任何文件 |
| **本地预览** | `serve_preview.py` | 自动检测端口的 HTTP 服务器，可选自动打开浏览器 |
| **验证检查** | `validate_single_html.py` | 扫描残留本地引用、解码嵌入的 CSS/JS 检查内部路径；检测未转义的 `</script>` 和 Draco CDN 依赖 |
| **资源提取** | `extract_assets.py` | 从单文件 HTML 提取 Base64 资源回文件 |
| **内联块提取** | `extract_style_script.py` | 把内联 `<style>`/`<script>` 拆成外部 `.css`/`.js`，与 `extract_assets.py` 互补 |
| **智能重命名** | `rename_extracted_assets.py` | 根据 alt/标题/上下文语义重命名提取的资源，`--update-html` 同步改写引用 |

### 快速开始

**场景 A — 普通课程 HTML：**

```bash
python scripts/inline_assets.py index.html --css-js-mode tag
python scripts/validate_single_html.py dist/index.single.html
```

**场景 B — React/Vue/Vite 项目（一条命令）：**

```bash
python scripts/package_frontend_build.py . --css-js-mode tag
```

**场景 C — 已有构建产物：**

```bash
python scripts/inline_assets.py dist/index.html --preset react-vue-build --css-js-mode tag
python scripts/validate_single_html.py dist/index.single.html
```

**场景 D — Next.js 静态导出：**

```bash
python scripts/inline_assets.py out/index.html --preset nextjs --css-js-mode tag
```

> ℹ️ **技能合并**：自 v4.2.0 起原独立的 `inline-html-assets` 技能已下线。其「只内联 CSS/JS」的能力已完整并入本工具包，通过 `--no-css` / `--no-js` / `--css-prepend` 实现，在 data-url 和 tag 模式下都生效，并可与 `--include-ext` 组合。详见 [CHANGELOG.md](./CHANGELOG.md)。

---

## Project structure / 项目结构

```text
html-asset-toolkit/
├── scripts/                    # 核心 Python 脚本（纯标准库，零依赖）
│   ├── inline_assets.py        # 主打包：HTML + assets → 单文件 HTML
│   ├── validate_single_html.py # 验证产物：残留引用、未转义标签、Draco 检测
│   ├── package_frontend_build.py # 前端一键打包（构建+定位+内联+验证）
│   ├── estimate_size.py        # 体积预估（不写文件）
│   ├── serve_preview.py        # 本地预览服务器
│   ├── extract_assets.py       # 提取 Base64 资源回文件
│   ├── extract_style_script.py # 提取内联 <style>/<script> 块
│   └── rename_extracted_assets.py # 智能重命名 + HTML 引用同步
├── references/                 # 渐进式参考文档
│   ├── parameters.md           # 完整 CLI 参数参考
│   ├── inline-modes.md         # data-url vs tag 模式选择
│   ├── react-vue-build-packaging.md
│   ├── threejs-model-recipes.md
│   ├── troubleshooting.md
│   └── ...
├── examples/                   # 测试夹具 + 示例
│   ├── index.html              # 普通课程 HTML 示例
│   ├── react-vue-build/dist/   # React/Vue 构建产物夹具
│   └── frameworks/             # 各框架配置提示
├── tests/
│   └── smoke_test.py           # 冒烟测试（13 个用例）
├── SKILL.md                    # Agent skill 定义（渐进式路由）
├── CHANGELOG.md
├── LICENSE
└── requirements.txt            # 仅 Pillow 为可选依赖（WebP 转换）
```

## Requirements / 环境要求

- **Python 3.10+**（仅使用标准库）
- **可选**：[Pillow](https://python-pillow.org/) — 启用 `--image-mode webp` 图片转换

```bash
pip install -r requirements.txt   # 仅安装可选的 Pillow
```

## Development & testing / 开发与测试

运行冒烟测试（覆盖全部脚本的端到端流程）：

```bash
python tests/smoke_test.py
```

测试会使用 `examples/` 下的夹具自动构建、打包、验证，无需外部依赖。13 个用例覆盖：普通 HTML、React/Vue 构建、tag 模式、Next.js 路径回退、Draco 检测、提取/重命名等。

## Documentation / 文档

| 文档 | 内容 |
|---|---|
| [SKILL.md](./SKILL.md) | Agent skill 定义、路由规则、执行契约 |
| [references/parameters.md](./references/parameters.md) | 完整 CLI 参数参考 |
| [references/inline-modes.md](./references/inline-modes.md) | data-url vs tag 模式、CSP 兼容性、`</script>` 转义机制 |
| [references/react-vue-build-packaging.md](./references/react-vue-build-packaging.md) | React/Vue/Next.js 打包流程 |
| [references/threejs-model-recipes.md](./references/threejs-model-recipes.md) | GLB/STL 加载、Draco 离线方案 |
| [references/troubleshooting.md](./references/troubleshooting.md) | 路径、浏览器、CORS、MIME、体积问题排查 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本历史 |

## Contributing / 贡献

1. Fork 仓库并创建特性分支。
2. 改动前先运行 `python tests/smoke_test.py` 确认基线通过。
3. 新功能需补充对应的冒烟测试用例。
4. 提交信息遵循现有风格：`feat:` / `fix:` / `docs:` 前缀。
5. 确保不引入敏感信息（API key、凭证、绝对路径）——见 `.gitignore` 的防御规则。

## License / 许可证

[MIT](./LICENSE)

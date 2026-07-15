# 参数参考

## inline_assets.py — 转成单文件 HTML

### 默认输出规则

普通源 HTML：

```text
输入 HTML 所在目录 / dist / <原文件名>.single.html
```

示例：

```bash
python scripts/inline_assets.py index.html
# 输出：dist/index.single.html

python scripts/inline_assets.py chapter01.html
# 输出：dist/chapter01.single.html
```

前端构建产物 HTML：

```text
dist/index.html  -> dist/index.single.html
build/index.html -> build/index.single.html
out/index.html   -> out/index.single.html
```

示例：

```bash
npm run build
python scripts/inline_assets.py dist/index.html --preset react-vue-build
# 输出：dist/index.single.html

python scripts/inline_assets.py build/index.html --preset create-react-app
# 输出：build/index.single.html
```

显式指定输出：

```bash
python scripts/inline_assets.py index.html --out dist/index.single.html
```

> 相对 `--out`、`--out-dir`、`--manifest`、`--assets-root`、`--root-dir` 会按输入 HTML 所在目录解析。这样即使脚本不在项目目录里，资源和输出也会围绕被处理项目，而不是围绕 Skill 目录。

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `input_html` | 必填 | 输入 HTML 文件；不必须叫 `index.html` |
| `--out` | 自动 | 输出 HTML 路径；相对路径按输入 HTML 所在目录解析 |
| `--out-dir` | 自动 | 不使用 `--out` 时的输出目录；相对路径按输入 HTML 所在目录解析 |
| `--single-name` | `<stem>.single.html` | 不使用 `--out` 时的输出文件名，例如 `index.single.html` |
| `--assets-root` | 空 | 额外资源根目录；用于 HTML 相对路径找不到时补充查找；相对路径按输入 HTML 所在目录解析 |
| `--root-dir` | 输入 HTML 所在目录 | 浏览器根路径 `/assets/app.js` 的解析根目录；React/Vue/Vite 构建产物通常不用手动指定 |
| `--preset` | `generic` | 构建场景标记：`generic`、`react-vue-build`、`vite`、`create-react-app`、`vue-cli`、`nextjs`；主要写入 manifest，便于 Agent 判断。Next.js 的 `_next/` 路径回退由目录检测自动驱动，不限 preset |
| `--manifest` | `{out}.manifest.json` | 嵌入结果清单；相对路径按输入 HTML 所在目录解析 |
| `--include-ext` | 空 | 只嵌入指定扩展名，如 `.png,.jpg,.mp3,.glb,.css,.js` |
| `--exclude-ext` | 空 | 排除指定扩展名 |
| `--max-asset-mb` | `0` | 单个资源最大 MB；0 表示不限制 |
| `--max-total-mb` | `0` | 总嵌入资源最大 MB；0 表示不限制 |
| `--dry-run` | `False` | 预演，不写文件 |
| `--strict` | `False` | 本地资源缺失或超限时返回失败码 |
| `--image-mode` | `raw` | `raw` 原样嵌入；`webp` 尝试转 WebP |
| `--max-width` | `1800` | WebP 模式下最大宽度 |
| `--max-height` | `1800` | WebP 模式下最大高度 |
| `--webp-quality` | `82` | WebP 质量 |
| `--svg-mode` | `base64` | `base64` 或 `utf8`；需要可逆提取时优先用 `base64` |
| `--process-external-css` | `True` | 嵌入外部 CSS 前，递归处理 CSS 内的 `@import` 和 `url(...)` |
| `--no-process-external-css` | - | 关闭外部 CSS 内部资源处理 |
| `--process-external-js` | `True` | 嵌入外部 JS 前，处理 JS 中本地资源字符串；支持 `"..."`、`'...'` 和静态反引号模板字符串 `` `...` `` |
| `--no-process-external-js` | - | 关闭外部 JS 资源字符串处理 |
| `--remove-integrity` | `True` | 移除 `integrity=` 属性；CSS/JS 改成 Data URL 后原 SRI 哈希会失效 |
| `--no-remove-integrity` | - | 保留 `integrity=` 属性，不推荐用于单文件打包 |
| `--css-js-mode` | `data-url` | CSS/JS 嵌入方式：`data-url`（默认，保持 href/src 为 Data URL）或 `tag`（替换为 `<style>`/`<script>` 标签，CSP/CORS 兼容性更好） |
| `--no-css` | `False` | 跳过 CSS 内联（tag 模式 `<link stylesheet>` 和 CSS `@import`）；内部等价于追加 `--exclude-ext .css`，与 `--include-ext` 组合生效 |
| `--no-js` | `False` | 跳过 JS 内联（tag 模式 `<script src>` 和 JS 资源字符串）；内部等价于追加 `--exclude-ext .js,.mjs` |
| `--css-prepend` | 空 | 在每个被内联的 CSS 块开头注入的文本；data-url 和 tag 模式都生效；适合注入 CSS reset 或全局覆盖规则 |
| `--fetch-cdn` | `off` | 打包前下载 CDN-only 资源到构建目录：`off`（默认）/`draco`（Three.js Draco 解码器，从 gstatic.com 下载到 `<root-dir>/draco/`）。需要联网；下载失败降级为提示不中断 |

## estimate_size.py — 预估最终体积（不写文件）

```bash
python scripts/estimate_size.py index.html
python scripts/estimate_size.py dist/index.html --json
```

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `input_html` | 必填 | 输入 HTML 文件 |
| `--assets-root` | 空 | 额外资源根目录；相对路径按输入 HTML 所在目录解析 |
| `--root-dir` | 输入 HTML 所在目录 | 浏览器根路径解析目录 |
| `--include-ext` | 空 | 只统计指定扩展名 |
| `--exclude-ext` | 空 | 排除指定扩展名 |
| `--max-asset-mb` | `0` | 单个资源最大 MB；超限标记为 over_limit |
| `--max-total-mb` | `0` | 预估嵌入总量上限（仅用于超限警告，不中止） |
| `--json` | `False` | 输出 JSON 报告 |

预估逻辑：扫描所有资源引用，按 Base64 膨胀系数（×1.33）估算嵌入后体积，加上 HTML 基础体积得到最终 HTML 预估大小。

## serve_preview.py — 本地预览服务器

```bash
python scripts/serve_preview.py dist/index.single.html --open
python scripts/serve_preview.py dist/ --port 3000
```

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `target` | 必填 | HTML 文件或目录 |
| `--port` | `8000` | 起始端口；被占用时自动递增查找下一个可用端口 |
| `--host` | `127.0.0.1` | 绑定地址；`0.0.0.0` 允许局域网访问 |
| `--open` | `False` | 自动打开系统浏览器 |
| `--no-browser` | `False` | 确保不打开浏览器（覆盖 `--open`，适合 CI/Agent） |

### 路径规则

- HTML 中的相对路径优先按 HTML 所在目录解析。
- CSS 文件内部的 `url(...)` 和 `@import` 优先按 CSS 文件所在目录解析。
- JS 文件内部的本地资源字符串优先按 JS 文件所在目录解析；Vite/esbuild 生成的静态模板字符串路径也会处理。
- `/assets/...`、`/static/...`、`/css/...`、`/js/...` 这类浏览器根路径按 `--root-dir` 解析，默认是输入 HTML 所在目录。
- 已经是 `data:`、`http:`、`https:`、`//`、`mailto:`、`tel:`、`#`、`javascript:` 的资源不会被嵌入。
- 包含 `${...}` 或 `{{...}}` 的动态模板路径不会被嵌入，因为无法在打包时确定真实文件名。

### React/Vue 推荐参数

Vite / Vue CLI：

```bash
npm run build
python scripts/inline_assets.py dist/index.html --preset vite
```

Create React App：

```bash
npm run build
python scripts/inline_assets.py build/index.html --preset create-react-app
```

如果构建工具把静态资源放在非标准目录，可以补充 `--root-dir` 或 `--assets-root`：

```bash
python scripts/inline_assets.py dist/sub/index.html --root-dir dist
python scripts/inline_assets.py dist/index.html --assets-root dist/assets
```

## validate_single_html.py — 验证单文件 HTML

```bash
python scripts/validate_single_html.py dist/index.single.html
```

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `input_html` | 必填 | 待验证的单文件 HTML |
| `--json` | `False` | 输出 JSON 报告 |
| `--max-html-mb` | `50` | HTML 文件体积警戒线 |
| `--max-asset-mb` | `25` | 单个资源体积警戒线 |
| `--fail-on-warning` | `False` | 有 warning 时返回失败码 |

验证内容：

- Base64 Data URL 数量。
- 按 MIME 类型统计嵌入资源体积。
- 剩余本地 `src/href/poster/data` 引用。
- 剩余 CSS `url(...)` 引用。
- 剩余 JS 本地资源字符串，包括 `"..."`、`'...'` 和静态反引号模板字符串。
- 解码嵌入后的 text/css、text/javascript Data URL，并扫描内部残留本地路径。
- HTML 总体积和单资源大文件风险。
- 内联 `<script>`/`<style>` 内容含未转义的 `</script>`/`</style>`：报告为 **error**（硬性错误，无论是否 `--strict` 都会导致返回失败码）。检测用状态机模拟 HTML 解析器的 raw-text 状态，跳过转义的 `<\/tag`，识别真实闭标签，覆盖 React/Vue 产物里成对 `<script>...</script>` 字面量的场景。
- Three.js Draco 解码器引用：报告为可恢复的专用 warning（`draco_warnings` 字段），`--strict` 下不致命；联网环境功能正常。

## extract_assets.py — 提取内嵌资源

```bash
python scripts/extract_assets.py dist/index.single.html --output-dir extracted-assets --replace
```

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `input_html` | 必填 | 输入 HTML 文件 |
| `--output-dir` | `{stem}_assets/` | 资源输出目录 |
| `--manifest` | `{output-dir}/manifest.json` | 提取清单 |
| `--replace` | `False` | 同时生成外链版 HTML |
| `--out-html` | `{input}.externalized.html` | 外链版 HTML 输出路径 |
| `--prefix` | `asset` | 文件名前缀 |
| `--min-bytes` | `1` | 小于该大小的资源不提取 |

说明：`extract_assets.py` 当前主要提取 Base64 Data URL。若希望后续可逆提取 SVG，建议打包时使用 `--svg-mode base64`，不要使用 `--svg-mode utf8`。

## extract_style_script.py — 提取内联 <style>/<script> 块

```bash
python scripts/extract_style_script.py index.html
python scripts/extract_style_script.py dist/index.html --dry-run --json
```

把内联 `<style>...</style>` 拆成外部 `.css`（替换为 `<link>`），把无 `src` 的内联 `<script>...</script>` 拆成外部 `.js`（替换为 `<script src>`）。已有 `src` 的外部 `<script>` 不动。与 `extract_assets.py`（仅处理 Base64 Data URL）互补。

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `input_html` | 必填 | 输入 HTML 文件 |
| `--output-dir` | `{stem}_assets/` | 资源输出目录（与 `extract_assets.py` 一致，可合并存放） |
| `--out-html` | `{stem}.externalized.html` | 外链版 HTML 输出路径 |
| `--prefix` | `asset` | 文件名前缀，生成 `asset_style_001_<hash>.css` / `asset_script_001_<hash>.js` |
| `--manifest` | `{output-dir}/manifest.style-script.json` | 提取清单；刻意用独立名字，避免覆盖同目录下 `extract_assets.py` 的 `manifest.json` |
| `--dry-run` | `False` | 只统计，不写文件 |
| `--json` | `False` | 输出 JSON 报告到 stdout |

manifest 字段：`{input, output_dir, out_html, style_count, script_count, style_bytes, script_bytes, assets: [{kind, filename, bytes, hash}]}`。

## rename_extracted_assets.py — 智能重命名

```bash
python scripts/rename_extracted_assets.py extracted-assets --name-from auto
python scripts/rename_extracted_assets.py extracted-assets --update-html page.externalized.html
python scripts/rename_extracted_assets.py extracted-assets --separator _ --no-near-text
```

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `asset_dir` | 必填 | 资源目录 |
| `--manifest` | 自动寻找 `manifest.json` | 提取清单 |
| `--name-from` | `auto` | `auto`/`alt`/`title`/`heading`/`id`/`class`/`tag`/`mime`/`index` |
| `--topic-map` | 空 | 手动映射，JSON 或 `asset_001:名称,...` |
| `--separator` | `-` | 替换空白/下划线/连字符运行所用的分隔符；v4.0.0 起默认 `-`（旧值 `_` 可用 `--separator _` 恢复） |
| `--no-near-text` | `False`（即默认开启 near_text） | 关闭 `near_text_before` 标签挖掘，仅用标准字段命名 |
| `--update-html` | 空 | 指定 HTML 文件，重命名时同步替换其中的引用，避免链接失效 |
| `--dry-run` | `False` | 只预览，不重命名（配合 `--update-html` 时也会统计将替换的引用数） |
| `--max-stem-length` | `80` | 文件名主干最大长度 |

`auto` 模式命名优先级：topic_map → alt → title → heading → id → class → tag → **near_text（v4.0.0 新增）** → mime_group fallback。near_text 步骤会从 `context.near_text_before` 中正则匹配最近的 `name:"..."/alt="..."` 等键值标签，适合 HTML/JS 里嵌套的结构化数据（物种树、商品目录、分类表）。

## package_frontend_build.py

Build and package a React/Vue/static frontend project in one command.

```bash
python scripts/package_frontend_build.py .
```

| Option | Meaning |
|---|---|
| `project_dir` | React/Vue/Vite/CRA project directory. Defaults to current directory. |
| `--skip-build` | Use an existing `dist/`, `build/`, or `out/` directory without running the build command. |
| `--entry` | Explicit built HTML entry, such as `dist/index.html`. |
| `--package-manager auto|npm|pnpm|yarn|bun` | Package manager for build command detection. |
| `--build-command "npm run build"` | Custom build command string. |
| `--preset auto|react-vue-build|vite|vue-cli|create-react-app|generic` | Packaging preset passed to `inline_assets.py`. |
| `--out` | Output path. Relative paths resolve beside the build entry. |
| `--root-dir` | Static root for `/assets/...` URLs. |
| `--assets-root` | Additional lookup root. |
| `--include-ext` | Only embed listed extensions. |
| `--exclude-ext` | Never embed listed extensions. |
| `--max-asset-mb` | Per-asset embedding limit. |
| `--max-total-mb` | Total decoded embedding limit. |
| `--image-mode raw|webp` | Optional image conversion mode. |
| `--css-js-mode data-url|tag` | CSS/JS embedding mode. Defaults to `data-url`. `tag` produces inline `<style>`/`<script>` blocks. |
| `--estimate` | Run `estimate_size.py` first. Abort if projected size exceeds `--max-total-mb`. |
| `--no-validate` | Skip validation after packaging. |
| `--strict` | Make inline/validate checks stricter. |
| `--dry-run` | Print actions without writing output. |

Examples:

```bash
python scripts/package_frontend_build.py .
python scripts/package_frontend_build.py . --skip-build
python scripts/package_frontend_build.py . --entry dist/index.html --skip-build
python scripts/package_frontend_build.py . --build-command "npm run build" --max-total-mb 80
```


## Wrapper validation options

| Option | Default | Meaning |
|---|---:|---|
| `--strict` | `False` | Wrapper strict mode. Passes `--strict` to `inline_assets.py` and treats validator warnings as failures. |
| `--fail-on-warning` | `False` | Wrapper validation mode. Fails when `validate_single_html.py` reports warnings, without enabling inline strict checks. |
| `--root-dir` | build entry directory | In `package_frontend_build.py`, relative values resolve from the frontend project root. |
| `--assets-root` | none | In `package_frontend_build.py`, relative values resolve from the frontend project root. |

`public/index.html` is not a default wrapper entry candidate. It must be passed explicitly with `--entry public/index.html` when the user really wants to process it.

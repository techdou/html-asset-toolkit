---
name: html-asset-toolkit
description: Package HTML and static frontend builds into one portable single-file HTML by embedding local assets (images, CSS, JS, fonts, audio, video, GLB, STL, WASM) as Base64/Data URLs or inline tags. Also extracts embedded assets back into editable files and renames them using surrounding context. Use whenever the user wants a self-contained, offline, no-assets-folder HTML artifact — course demos, 课件, 百宝箱 HTML, 离线演示, 交互式学习页面, React/Vue/Vite/CRA/webpack build packaging — or asks to extract/inline/rename assets, estimate size, preview locally, or split inline style/script blocks. Even if they don't say "single-file", trigger when the goal is an HTML that opens anywhere with no external files.
compatibility: Requires Python 3.10+. Optional Pillow for WebP image conversion. Frontend wrapper requires the project package manager when running npm/pnpm/yarn/bun build.
---

# HTML Asset Toolkit

Use this skill when the user needs a **portable single-file HTML artifact** for course demos, offline teaching pages, interactive rich-text HTML, 百宝箱 HTML, or static React/Vue build outputs.

Do **not** use it for normal production Web projects unless the user explicitly asks for single-file, offline, Base64/Data URL, or no-assets-folder packaging.

## Agent routing

Trigger this skill when the user asks to:

- Convert `index.html + assets/` or any `.html + local assets` into one HTML file.
- Package a React, Vue, Vite, Vue CLI, Create React App, webpack, or similar static frontend after `npm run build`.
- Inline `dist/index.html` or `build/index.html` with its `assets/`, `static/`, `css/`, `js/`, `img/`, fonts, media, GLB, STL, or WASM files.
- Embed images, SVG, audio, video, MP3, MP4, WebM, GLB, STL, fonts, PDFs, CSS, JS, or WASM into HTML.
- Replace local file dependencies with Base64/Data URLs for offline opening.
- Extract embedded Base64/Data URL assets back into editable files.
- Extract inline `<style>` or `<script>` blocks from an HTML file into external `.css`/`.js` files (reverse of tag-mode inlining).

Avoid this skill for SEO, deployment, CDN, caching, general frontend refactoring, normal React/Vue development, or formal Web deployment unless the user explicitly requests a self-contained/offline artifact.

## Core decision rule

| User intent | Correct action |
|---|---|
| Formal online Web app | Keep assets external. Do not inline by default. |
| Course/demo/offline handoff | Inline local assets and validate the generated single HTML. |
| React/Vue source project | Run the build first, then package the generated static build entry. |
| Existing `dist/index.html` or `build/index.html` | Package that build entry directly; do not rebuild unless needed. |
| Very large MP4/GLB/STL/PDF | Warn about size; inline only if the user accepts heavy single-file output. |
| Inline `<style>`/`<script>` blocks need extraction | Use `extract_style_script.py`; it complements `extract_assets.py` (which only handles Base64 Data URLs). |
| Renamed assets should keep HTML links working | Pass `--update-html <path>` to `rename_extracted_assets.py` so references are rewritten in lockstep. |

## Output convention

The tool supports any `.html` filename.

### Plain source HTML

For a normal source file, create a `dist/` folder beside the input HTML:

```text
course-demo/index.html       -> course-demo/dist/index.single.html
course-demo/chapter01.html   -> course-demo/dist/chapter01.single.html
course-demo/demo.html        -> course-demo/dist/demo.single.html
```

### React/Vue/static build output

For a production build entry already inside `dist/`, `build/`, or `out/`, write the single file beside that entry to avoid nested `dist/dist/`:

```text
my-app/dist/index.html    -> my-app/dist/index.single.html
my-app/build/index.html   -> my-app/build/index.single.html
my-app/out/index.html     -> my-app/out/index.single.html
```

`public/index.html` is not treated as a build entry by default because it is often a source template. If explicitly passed, treat it as source/generic HTML and validate the result.

`dist/` in this skill means the current user project/build directory, not the skill directory.

## Preferred workflows

> **Recommended**: use `--css-js-mode tag` by default. It produces `<style>`/`<script>` blocks instead of Data URL attributes, which is more reliable for ES modules, CSP-restricted platforms (LMS/enterprise wiki/公众号), and `file://` offline opening. Only keep the default `data-url` when you need `extract_assets.py` reversible extraction. See `references/inline-modes.md`.

### A. Plain course HTML

Run from the course project root when possible:

```bash
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html --css-js-mode tag
python /path/to/html-asset-toolkit/scripts/validate_single_html.py dist/index.single.html
```

### B. React/Vue/Vite project: one-command wrapper

Use the wrapper when the user wants the Agent to build and package a frontend project:

```bash
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --css-js-mode tag
```

The wrapper will:

1. Detect the package manager from lockfiles when possible.
2. Run the build command, defaulting to `npm run build` when no lockfile implies another manager.
3. Locate `dist/index.html`, `build/index.html`, or `out/index.html`.
4. Inline the build assets into `index.single.html` beside the build entry.
5. Validate the generated file.

### C. React/Vue/Vite project: explicit manual workflow

```bash
npm run build
python /path/to/html-asset-toolkit/scripts/inline_assets.py dist/index.html --preset react-vue-build --css-js-mode tag
python /path/to/html-asset-toolkit/scripts/validate_single_html.py dist/index.single.html
```

Create React App:

```bash
npm run build
python /path/to/html-asset-toolkit/scripts/inline_assets.py build/index.html --preset create-react-app --css-js-mode tag
python /path/to/html-asset-toolkit/scripts/validate_single_html.py build/index.single.html
```

Existing build directory without rebuilding:

```bash
python /path/to/html-asset-toolkit/scripts/package_frontend_build.py . --skip-build --css-js-mode tag
```

## Agent execution contract

1. Identify whether the target is plain source HTML or a frontend build project.
2. **Default to `--css-js-mode tag`** unless the user explicitly needs `extract_assets.py` reversible extraction. Tag mode is more reliable for ES modules, CSP-restricted platforms, and `file://` offline opening.
3. For React/Vue packaging, prefer `scripts/package_frontend_build.py` unless the user gives a specific built HTML entry.
4. If using the manual workflow, run `npm run build` first unless the user says the build output already exists.
5. Locate the HTML entry in this order: user-specified `.html`, `dist/index.html`, `build/index.html`, `out/index.html`, then source `index.html`.
6. Run scripts from the user project root when possible; use absolute paths to this skill's scripts.
7. Let the default output convention work unless the user specifies `--out`.
8. Always run `validate_single_html.py` after packaging unless the user explicitly asks to skip validation.
9. Open or inspect the result when a browser/runtime is available.
10. Report the generated path, manifest path, warnings, and any remaining local references.
11. Never paste long Base64 strings into chat; use scripts for deterministic conversion.
12. When running `rename_extracted_assets.py`, pass `--update-html <externalized.html>` so the renamed files keep their HTML references valid. Do not rename files without also updating references unless the user explicitly accepts broken links.

## Scripts

### Build/package React/Vue output

```bash
python scripts/package_frontend_build.py .
python scripts/package_frontend_build.py . --skip-build
python scripts/package_frontend_build.py . --build-command "npm run build"
python scripts/package_frontend_build.py . --entry dist/index.html
```

### Inline a specific HTML file

```bash
python scripts/inline_assets.py index.html
python scripts/inline_assets.py dist/index.html --preset react-vue-build
python scripts/inline_assets.py build/index.html --preset create-react-app
```

Useful options:

```bash
python scripts/inline_assets.py index.html --out dist/index.single.html
python scripts/inline_assets.py dist/index.html --root-dir dist
python scripts/inline_assets.py index.html --include-ext .png,.jpg,.svg,.mp3,.mp4,.glb,.stl,.css,.js
python scripts/inline_assets.py index.html --max-asset-mb 25 --max-total-mb 80
python scripts/inline_assets.py index.html --image-mode webp --max-width 1800 --max-height 1800
python scripts/inline_assets.py index.html --dry-run
```

### Validate output

```bash
python scripts/validate_single_html.py dist/index.single.html
```

### Extract embedded assets

```bash
python scripts/extract_assets.py dist/index.single.html --output-dir extracted-assets --replace
```

Extracts Base64 Data URL assets (images, audio, models, fonts, ...) back into editable files. Writes `<stem>.externalized.html` with relative references when `--replace` is passed.

### Rename extracted assets

```bash
python scripts/rename_extracted_assets.py extracted-assets --name-from auto
python scripts/rename_extracted_assets.py extracted-assets --update-html page.externalized.html
python scripts/rename_extracted_assets.py extracted-assets --separator _ --no-near-text
```

Renames extracted files using manifest context. By default the `auto` mode tries `alt` → `title` → `heading` → `id` → `class` → `tag`, then mines `near_text_before` for the closest `name:"..."/alt="..."` label (useful for HTML/JS data blobs that embed structured records like species or product names), then falls back to the mime group. `--update-html` rewrites references in an HTML file in lockstep with the renames so links do not break. Default separator changed to `-` in v4.0.0 (was `_`); pass `--separator _` to restore the old style.

### Extract inline `<style>`/`<script>` blocks

```bash
python scripts/extract_style_script.py index.html
python scripts/extract_style_script.py dist/index.html --dry-run --json
```

Splits inline `<style>...</style>` into external `.css` files (referenced via `<link>`) and inline `<script>...</script>` (no `src`) into `.js` files (referenced via `<script src>`). Complements `extract_assets.py`, which only handles Base64 Data URL assets. External scripts with an existing `src` are left untouched. Default output dir is `<stem>_assets/`; default externalized HTML is `<stem>.externalized.html`.

### Estimate final size (no files written)

```bash
python scripts/estimate_size.py index.html
python scripts/estimate_size.py dist/index.html --json
```

Estimates the final single-file HTML size by applying the Base64 expansion factor to every resolved asset. Use before a heavy run to decide whether single-file packaging is practical.

### Preview locally with a static server

```bash
python scripts/serve_preview.py dist/index.single.html --open
python scripts/serve_preview.py dist/ --port 3000 --open
```

Auto-detects the first available port and optionally opens the browser. Press Ctrl+C to stop.

### Tag-inline mode (--css-js-mode tag)

```bash
python scripts/inline_assets.py index.html --css-js-mode tag
```

Replaces `<link rel="stylesheet" href="style.css">` with `<style>...</style>` and `<script src="app.js">` with `<script>...</script>` instead of Data URL attributes. Better for CSP/CORS/module-script compatibility. CSS/JS internal resources are still recursively inlined as Data URLs.

## Frontend build handling

The inliner handles common static build references:

```html
<script type="module" src="/assets/index-xxxxx.js"></script>
<link rel="stylesheet" href="/assets/index-xxxxx.css">
<link rel="icon" href="/favicon.ico">
```

It also processes resources inside external CSS and JS:

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

It also handles static template literals emitted by Vite/esbuild minification:

```js
var BUILDING_IMAGES=[`/buildings/buildingA.jpg`,`/buildings/buildingB.jpg`];
```

Dynamic template literals cannot be resolved deterministically and should be refactored into a static lookup table or bundler imports before packaging:

```js
const img = `/buildings/${buildingName}.jpg`;
```

The validator decodes embedded JavaScript/CSS Data URLs and scans inside them for remaining local references, so runtime-only missing-image bugs are easier to catch before handoff.

The tool removes `integrity` attributes by default because SRI hashes no longer match after CSS/JS URLs become Data URLs.

## Read when needed

- `references/react-vue-build-packaging.md` — React/Vue/Vite/CRA/webpack static build packaging workflow.
- `references/inline-modes.md` — data-url vs tag mode selection guide, CSP/CORS compatibility matrix.
- `references/js-asset-detection.md` — Vite/esbuild JavaScript string/template-literal asset detection and validation.
- `references/parameters.md` — full CLI parameter reference.
- `references/mime-data-url-matrix.md` — MIME types and Base64 prefixes for common assets.
- `references/threejs-model-recipes.md` — GLB/STL Data URL and Blob loading recipes.
- `references/single-html-strategy.md` — size thresholds and course-demo packaging strategy.
- `references/quality-gate.md` — final handoff checklist.
- `references/troubleshooting.md` — path, browser, CORS, MIME, and size fixes.

## Quality gate

Before handing off a single-file HTML:

1. Confirm the input entry is correct.
2. For React/Vue projects, confirm a build was run or an existing build was intentionally reused.
3. Confirm output path follows the right convention.
4. Inspect the generated `.manifest.json`.
5. Run `validate_single_html.py`.
6. Open the output locally when possible.
7. Check images, CSS, JS interactions, state-driven image switching, audio/video controls, and GLB/STL viewers.
8. Prefer final HTML under 50 MB; treat above 100 MB as a heavy artifact requiring user confirmation.

## Robustness rules for agents

- For React/Vue/Vite/CRA projects, use `package_frontend_build.py` first unless the user explicitly asks to run only `inline_assets.py`.
- Auto-detect production build entries only from `dist/index.html`, `build/index.html`, or `out/index.html`.
- Do not auto-select `public/index.html`; it is often a source template. Use it only when the user explicitly passes it as `--entry`.
- When calling the wrapper, interpret `--root-dir` and `--assets-root` relative to the frontend project root.
- Use `--strict` for final Agent delivery whenever practical. It makes missing/oversized assets fail and makes validator warnings fail.
- If the wrapper summary contains `validation_warning_count > 0`, report the warnings and do not claim the package is clean.

## Feature reference

| Feature | Script | When to use |
|---|---|---|
| Extract `<style>`/`<script>` blocks | `extract_style_script.py` | Split inline CSS/JS back into external `.css`/`.js` files; complements `extract_assets.py` (Base64 only) |
| HTML-aware rename | `rename_extracted_assets.py --update-html` | Rewrite references in an HTML file in lockstep with file renames so links do not break |
| near_text smart naming | `rename_extracted_assets.py` (auto, default) | Mine `near_text_before` for the closest `name:"..."/alt="..."` label when `alt`/`title`/`heading` are empty |
| Tag-inline mode | `inline_assets.py --css-js-mode tag` | CSP/CORS/module-script compatibility; produces `<style>`/`<script>` instead of Data URL attributes |
| Size estimation | `estimate_size.py` | Preview the final HTML size before committing to a full run; abort via wrapper `--estimate` if over `--max-total-mb` |
| Local preview | `serve_preview.py` | Verify the packaged HTML in a browser via local HTTP with auto port detection |
| Framework guides | `examples/frameworks/` | Vite React/Vue, CRA, Vue CLI, webpack config tips and common pitfalls |


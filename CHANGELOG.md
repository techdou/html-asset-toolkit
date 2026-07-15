# Changelog

## v4.3.0 - React/Next.js production reliability

### Fixed

- **P0 — `</script>` injection in tag mode** (`inline_assets.py`): when `--css-js-mode tag` placed raw JS/CSS inside `<script>`/`<style>`, any literal `</script>` / `</style>` in the content (React/Vue minified runtimes almost always contain one) made the HTML parser close the tag early, leaking the rest of the JS as visible text and breaking the page. Tag mode now escapes `</script>` → `<\/script>` and `</style>` → `<\/style>` before inlining. The escape is semantically transparent (`\/` evaluates to `/` in JS; `\` is a valid CSS escape). Data-url mode is unaffected.
- **Validator error for unescaped `</script>`** (`validate_single_html.py`): uses a state-machine scanner that mimics the HTML parser's raw-text state to detect an unescaped `</script>`/`</style>` inside inline tag content. It skips the escaped form `<\/tag>` and catches leaks even when the content contains paired `<script>...</script>` literals (common in React/Vue minified runtimes). Reported as an **error** via a new top-level `errors` list; errors always cause a non-zero exit code, independent of `--strict`.

### Added

- **P1 — Next.js `_next/` path fallback** (`inline_assets.py`): `dynamic(() => import(...), { ssr: false })` emits bare `static/chunks/x.js` references, but the files live under `_next/static/`. When a `_next/` subdirectory is detected under any candidate root, `resolve_asset` now retries unresolved references under `_next/` automatically — no manual symlink. The fallback is directory-driven and fires for every preset; `--preset nextjs` is added as a manifest marker.
- **P2 — Draco decoder detection** (`validate_single_html.py`): when inline JS (tag-mode `<script>` blocks or decoded `text/javascript` Data URLs) references `draco_decoder` / `DRACOLoader`, the validator emits a dedicated warning in a new `draco_warnings` field, listing the required files and the `gstatic.com` CDN URL. Under `--strict` this is a recoverable warning, not a fatal error (the page works online).
- **P2 — `--fetch-cdn draco`** (`inline_assets.py`): downloads `draco_decoder.js`, `draco_wasm_wrapper.js`, and `draco_decoder.wasm` from the CDN (version extracted from JS, default 1.5.5) into `<root-dir>/draco/` before packaging. Network failures degrade to a note and never abort the run. The tool does not rewrite runtime `DRACOLoader.setDecoderPath`; users must point the loader at the local `draco/` path for full offline support. Default is `off`; existing offline behavior is unchanged.

### Changed

- `validate_single_html.py` console output now prints an `Errors:` section (above warnings) and a `Draco decoder notice:` section. `errors` and `draco_warnings` fields are added to the JSON report. The "No warnings." message became "No errors or warnings.".
- `SKILL.md`, `references/inline-modes.md`, `references/react-vue-build-packaging.md`, `references/threejs-model-recipes.md`, `references/parameters.md`, `references/troubleshooting.md` document the three fixes.

### Notes

- All changes are backward-compatible. P0 is a bug fix; P1/P2 additions default to off/directory-detected. `--fetch-cdn` defaults to `off` and only loads `urllib.request` when enabled, so the tool remains offline-by-default.
- Smoke test extended with three cases: `test_p0_script_escape`, `test_nextjs_fallback`, `test_draco_warning` (13 total, all passing). `--fetch-cdn` is network-dependent and not exercised by the offline smoke test.

## v4.2.0 - Merge inline-html-assets, add CSS/JS-only inlining flags

### Added

- **`--no-css` / `--no-js` flags** (`inline_assets.py`): skip CSS or JS inlining selectively. Internally mapped to `--exclude-ext .css` (resp. `.js,.mjs`) so they work uniformly in both `data-url` and `tag` mode and compose with `--include-ext`. Replaces the standalone `inline-html-assets` skill's `--no-css`/`--no-js` switches.
- **`--css-prepend` flag** (`inline_assets.py`): text prepended to every inlined CSS block before embedding, in both `data-url` and `tag` mode. Useful for injecting CSS resets or global overrides at the top of each inlined stylesheet. Ported from the retired `inline-html-assets` skill.

### Changed

- **Retired `inline-html-assets` skill**: its CSS/JS-only inlining capability is now fully covered by this toolkit. The standalone skill's `SKILL.md` description and trigger phrases ("内联CSS", "内联JS", "把CSS嵌入HTML", "单文件HTML", "inline styles", "inline scripts") have been absorbed into `SKILL.md` routing so existing user phrasing still routes here.
- **`SKILL.md`**: added CSS/JS-only inlining to the Agent routing list and a dedicated command block. The description now explicitly states it supersedes the legacy skill.
- **`README.md`**: bumped version to v4.2.0, added "CSS/JS-only inlining" row to both the English and Chinese capability tables, added Quick-start Scenario E in both languages, and added a merge notice.
- **`references/parameters.md`**: documented `--no-css`, `--no-js`, `--css-prepend`.
- **`.gitignore`**: hardened with defensive rules for secrets/keys/credentials (`.env`, `*.pem`, `*.key`, `*_api_key*`, `*_token*`, etc.), IDE/editor config dirs (`.vscode/`, `.idea/`), and OS junk files. No previously-tracked files are affected.

### Notes

- All new flags default to off / empty, so existing invocations are unchanged.
- Smoke test (19 cases) still passes without modification.

## v4.1.0 - Hardening and v4 doc alignment

### Fixed

- `rename_extracted_assets.py --update-html`: reference rewriting is now scoped to HTML attribute values (`src=`/`href=`/`data=`/etc.) instead of a bare `str.replace`. Previously, a filename appearing in body text, comments, or unrelated JS/CSS strings would also be rewritten.
- `package_frontend_build.py --dry-run`: the wrapper now skips the inline subprocess entirely in dry-run mode (`run_command(..., dry_run=args.dry_run)`). Previously the wrapper always launched the subprocess with `dry_run=False` hardcoded, relying on the child's `--dry-run` flag for safety — semantically inconsistent.
- `rename_extracted_assets.py --name-from <explicit>` (alt/title/heading/id/class/tag/mime): when the requested field is empty, the tool now drops to the mime/index fallback instead of silently falling through to the full auto field order. `--name-from alt` no longer behaves like `--name-from auto` when `alt` is missing. The shared fallback logic was extracted into `fallback_name()` to avoid duplication.

### Documentation

- `references/parameters.md`: corrected `extract_style_script.py` manifest default to `{output-dir}/manifest.style-script.json` (was wrongly documented as `manifest.json`, which is `extract_assets.py`'s manifest name). Added a note explaining why the names differ.
- `README.md`: added `extract_style_script.py` to the core capability table and to the extract/rename command block; added `--update-html` example. Removed stale "v3.0.0 新增" framing (tag mode is now baseline) and the false "默认行为 = v2.6.0" claim (invalidated by the v4 separator default change). Reordered install paths to put `.agents/skills/` first.
- `SKILL.md`: collapsed the versioned section headers ("v2.6.0 robustness rules", "v3.0.0 features", "v4.0.0 features") into a single unversioned "Feature reference" table and a "Robustness rules for agents" section. The rules and features are unchanged; only the stale version framing was removed.
- `references/parameters.md`: renamed the "v2.6.0 wrapper validation options" section to "Wrapper validation options" (these are live defaults, not version-specific).
- Unified placeholder style to `{source-name}`/`{build-dir}` across docs and `inline_assets.py` manifest field (the historical CHANGELOG entry at v2.2.0 is preserved verbatim as a factual record).

### Notes

- All fixes are backward-compatible. No defaults, output paths, or CLI signatures changed.
- All scripts still use only the Python standard library.

## v4.0.0 - Extract inline blocks, HTML-aware rename, near_text smart naming

### Added

- **Extract inline `<style>`/`<script>` blocks** (`extract_style_script.py`): splits inline CSS/JS back into external `.css`/`.js` files, replacing the blocks with `<link>`/`<script src>`. Complements `extract_assets.py`, which only handles Base64 Data URL assets. External scripts with an existing `src` are preserved. Supports `--dry-run`, `--json`, and writes a manifest with the same shape as `extract_assets.py`. The manifest is named `manifest.style-script.json` (not `manifest.json`) so it does not clobber `extract_assets.py`'s manifest when both extractors share the same output directory.
- **HTML-aware rename** (`rename_extracted_assets.py --update-html <path>`): rewrites references in an HTML file in lockstep with file renames, so links do not break. Dry-run mode reports how many references would change without touching the file.
- **near_text smart naming** (`rename_extracted_assets.py` auto mode): when `alt`/`title`/`heading`/`id`/`class`/`tag` are all empty, mines `context.near_text_before` for the closest `name:"..."/alt="..."` label. Works well on HTML/JS data blobs that embed structured records (species trees, product catalogs, taxonomy tables). Disable with `--no-near-text`.

### Improved

- `rename_extracted_assets.py` default separator changed from `_` to `-` (e.g. `001-七鳃鳗.png` instead of `001_image.png`). Pass `--separator _` to restore the pre-v4 style.
- `rename_extracted_assets.py` now has its own `### Rename extracted assets` section in `SKILL.md` (was previously a one-liner inside `### Extract embedded assets`).
- Smoke test extended with three new cases: `test_extract_style_script`, `test_rename_with_near_text`, `test_rename_update_html`.

### Notes

- **Breaking**: the rename separator default change is the only behavioral break. Existing invocations that relied on `_` should pass `--separator _`. All other defaults are unchanged.
- All new and modified scripts use only the Python standard library. No new dependencies.
- A new example, `examples/chapter02.html`, contains inline `<style>` and `<script>` blocks for `extract_style_script.py` testing.

## v3.0.0 - Tag-inline mode, size estimation, preview server, framework guides

### Added

- **Tag-inline mode** (`--css-js-mode tag`): inlines CSS as `<style>` blocks and JS as `<script>` blocks instead of Data URL attributes. Improves CSP, CORS, and ES module compatibility. CSS/JS internal resources are still recursively inlined as Data URLs. Supported in `inline_assets.py` and transparently forwarded by `package_frontend_build.py`.
- **Size estimation** (`estimate_size.py`): projects the final single-file HTML size by applying the Base64 expansion factor to every resolved asset. No files are written. Supports `--json` for programmatic use. The wrapper accepts `--estimate` to abort early if the projected size exceeds `--max-total-mb`.
- **Local preview server** (`serve_preview.py`): a zero-dependency HTTP server based on `http.server`. Auto-detects the first available port starting from `--port`. Optionally opens the system browser (`--open`). Serves a single file or a directory.
- **Framework-specific guides** under `examples/frameworks/`: Vite React, Vite Vue, Create React App, Vue CLI, and webpack — each with minimal config files (`base: './'` / `publicPath: './'`), build+package commands, and common pitfalls (code splitting, hash routing, service workers).
- **Inline modes reference** (`references/inline-modes.md`): data-url vs tag mode decision guide with a CSP/CORS compatibility matrix.

### Improved

- `validate_single_html.py` now scans inline `<style>` and `<script>` blocks (tag-mode output) for residual local references, reporting them under `tag_inline_refs` in the JSON output.
- `inline_assets.py` manifest report includes `css_js_mode`.
- `package_frontend_build.py` summary includes an `estimated` block when `--estimate` is used.

### Notes

- Default behavior is unchanged: `--css-js-mode` defaults to `data-url`, preserving full backward compatibility with v2.6.0.
- All new scripts use only the Python standard library. No new hard dependencies.
- The smoke test now covers tag-inline mode, size estimation, tag-mode validation, and the preview server.

## v2.6.0 - Wrapper strictness and build-entry robustness

- Fixed `package_frontend_build.py --strict` calling `validate_single_html.py --strict` when validator only accepted `--fail-on-warning`.
- Added `--strict` alias to `validate_single_html.py` for compatibility.
- Added wrapper-level `--fail-on-warning`.
- Changed wrapper validation to run `validate_single_html.py --json`, parse warnings, and print them in `Package summary`.
- Fixed wrapper `--root-dir` and `--assets-root` relative-path behavior: paths now resolve from the frontend project root.
- Removed `public/index.html` from automatic build entry detection; it is only used when explicitly passed through `--entry`.
- Added smoke tests for wrapper strict mode and `--root-dir dist`.

## v2.5.0

### Fixed

- Fixed Vite/esbuild build output where static asset paths in JavaScript are rewritten from quotes to backtick template literals, e.g. `` `/buildings/buildingA.jpg` ``.
- Updated `JS_STRING_RE` in both inliner and validator to recognize `"`, `'`, and `` ` `` string delimiters while avoiding whole HTML template snippets.
- Escapes replacement Data URLs for JavaScript string/template literal safety.

### Improved

- `validate_single_html.py` now decodes embedded text assets such as `data:text/javascript;base64,...` and `data:text/css;base64,...`, then scans inside them for remaining local references.
- Added a Vite-style backtick-path smoke test with click/state-driven image paths under `/buildings/`.
- Added `references/js-asset-detection.md` for this class of runtime missing-image issue.

### Boundary

- Static template literals are inlined; dynamic template literals containing `${...}` are intentionally not resolved and should be refactored into static lookup tables or bundler imports.

## v2.4.0

### Added

- Added `scripts/package_frontend_build.py`, a wrapper for React/Vue/Vite/CRA/static frontend projects.
- Wrapper can run the build command, detect `dist/index.html`, `build/index.html`, or `out/index.html`, inline assets, and validate the generated HTML.
- Added package manager detection for `npm`, `pnpm`, `yarn`, and `bun` based on lockfiles.
- Expanded React/Vue packaging documentation and troubleshooting guidance.

### Improved

- Reworked `SKILL.md` around Agent routing, output conventions, and an explicit execution contract.
- Clarified user-facing difference between source HTML packaging and frontend build packaging.
- Made React/Vue/npm build use case a first-class workflow rather than a note under generic HTML inlining.
- Strengthened quality gate for CSS/JS interactions, build entries, manifests, and remaining references.

### Notes

- The tool remains optimized for offline demos and course handoff artifacts, not production Web deployment.

## v2.3.0

- Added React/Vue/Vite/CRA build-output packaging guidance.
- Added `--preset react-vue-build`, `vite`, `vue-cli`, and `create-react-app`.
- Added frontend build output convention for `dist/index.html` and `build/index.html`.
- Improved root-relative `/assets/...` resolution.

## v2.2.0

- Clarified Agent routing and Chinese trigger keywords.
- Fixed output rule to `dist/<source-name>.single.html` for source HTML.
- Clarified that `dist/` belongs to the user project, not the skill directory.

## v2.1.0

- Added stable `dist/index.single.html` delivery convention for source `index.html`.
- Added validation and quality references.

## v2.0.0

- Expanded from image-only embedding to multi-asset HTML packaging.
- Added inline, extract, rename, and validate scripts.

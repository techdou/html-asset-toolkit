# Troubleshooting

## Output went to the wrong folder

Run the script from the user project root and pass an absolute path to the skill script:

```bash
cd course-demo
python /path/to/html-asset-toolkit/scripts/inline_assets.py index.html
```

Relative `--out`, `--out-dir`, `--root-dir`, and `--assets-root` are resolved relative to the input HTML directory.

## React/Vue build created `dist/dist/`

Use the current build convention. For `dist/index.html`, output should be beside the input:

```text
dist/index.html -> dist/index.single.html
```

Use:

```bash
python scripts/inline_assets.py dist/index.html --preset react-vue-build
```

or the wrapper:

```bash
python scripts/package_frontend_build.py . --skip-build
```

## `/assets/...` files are missing

For build outputs, browser-root-relative URLs should resolve under the build directory. If the HTML entry is not inside the static root, pass `--root-dir`:

```bash
python scripts/inline_assets.py custom/index.html --root-dir dist
```

## CSS or JS still points to local files

Run validation and inspect the manifest:

```bash
python scripts/validate_single_html.py dist/index.single.html
python scripts/validate_single_html.py dist/index.single.html --json
```

The JSON report includes `decoded_text_remaining_refs`, which catches unresolved paths hidden inside embedded Base64 JavaScript/CSS.

If the remaining reference uses an unsupported extension, add it with `--include-ext` only after confirming it is safe to embed.

## Click-triggered images are missing after Vite build

Vite/esbuild may turn ordinary strings into static template literals:

```js
var Kg=[`/buildings/buildingA.jpg`,`/buildings/buildingB.jpg`];
```

v2.5.0+ handles these static backtick-wrapped paths. If validation still reports a path like this, rerun with the current `inline_assets.py`.

If the path is dynamic, the tool cannot infer every possible file:

```js
const img = `/buildings/${buildingName}.jpg`;
```

Refactor to a static lookup table or import map before packaging.

## Script or stylesheet does not load

Check for stale SRI hashes. The inliner removes `integrity` by default. If you disabled that behavior, re-run without `--no-remove-integrity`.

## Dynamic imports fail

Some frontend apps rely on complex runtime chunk loading. The tool rewrites common quoted asset paths and import strings, but production apps with custom loaders may need a bundler configuration that emits fewer chunks.

For demos, consider disabling aggressive code splitting or building a single route/single view artifact.

## App opens but routing is broken

Single-file packaging does not emulate a production server. For teaching demos, prefer hash routing or open the app at its main route.

## The file is too large

Use:

```bash
python scripts/inline_assets.py index.html --max-asset-mb 25 --max-total-mb 80
```

Then compress large media or models before embedding.

## SVG extraction is incomplete

`extract_assets.py` primarily targets Base64 Data URLs. For reversible extraction of SVG resources, prefer Base64 SVG mode when creating the single HTML.


## wrapper --root-dir dist resolves incorrectly

Fixed in v2.6.0. In `package_frontend_build.py`, relative `--root-dir` and `--assets-root` values now resolve from the frontend project root, not beside the build entry. This means:

```bash
cd my-app
python /path/to/scripts/package_frontend_build.py . --skip-build --entry dist/index.html --root-dir dist
```

resolves to `my-app/dist`, not `my-app/dist/dist`.

## public/index.html was selected accidentally

Fixed in v2.6.0. The wrapper no longer auto-selects `public/index.html` because React/Vue/Vite projects often use it as a source template rather than a production artifact. Run `npm run build` and package `dist/index.html`, `build/index.html`, or `out/index.html`. Use `--entry public/index.html` only when explicitly required.

## CSP blocks data: URLs in style-src or script-src

If the target page has a Content-Security-Policy that disallows `data:` in `style-src` or `script-src`, use tag-inline mode:

```bash
python scripts/inline_assets.py index.html --css-js-mode tag
```

This replaces `<link rel="stylesheet" href="data:...">` with `<style>...</style>` and `<script src="data:...">` with `<script>...</script>`. Internal assets (images, fonts in CSS) remain as Data URLs — adjust `img-src`/`font-src` accordingly, or see `references/inline-modes.md`.

## ES module script does not load as data: URL

Some browsers have inconsistent support for `<script type="module" src="data:text/javascript;base64,...">`. Use tag mode:

```bash
python scripts/inline_assets.py dist/index.html --css-js-mode tag
```

The module script becomes `<script type="module">/* code */</script>`, which is reliably supported.

## Tag mode produces visible JS text or broken page (React/Vue)

If the inline `<script>` block contains a literal `</script>` (common in React/Vue minified runtimes), the HTML parser closes the tag early and the rest of the JS leaks as visible text. Since v4.3.0 the inliner escapes these automatically (`</script>` → `<\/script>`), so this should not happen. If you still see it:

- Ensure you are running the current `inline_assets.py`.
- `validate_single_html.py` reports an unescaped `</script>` as an **error**; fix the inliner output before handoff.

## Next.js dynamic import chunks are missing

Next.js `dynamic(() => import(...), { ssr: false })` emits bare `static/chunks/x.js` references, but the files live under `_next/static/chunks/`. Since v4.3.0 the inliner retries these under `_next/` automatically when a `_next/` directory exists — no manual symlink needed. If chunks are still reported `missing_or_external`:

- Confirm the build output really has `_next/` under the build root (not a flattened export).
- You can use `--preset nextjs` to mark the manifest, but the fallback is directory-driven and works with any preset.

## 3D model does not load offline (Draco compression)

GLB models with `KHR_draco_mesh_compression` need decoder files that Three.js fetches from the Google CDN at runtime. `validate_single_html.py` emits a dedicated Draco warning listing the required files and CDN URL. To embed them:

```bash
python scripts/inline_assets.py out/index.html --css-js-mode tag --fetch-cdn draco
```

This downloads `draco_decoder.js`, `draco_wasm_wrapper.js`, and `draco_decoder.wasm` into `<root-dir>/draco/`. Then ensure the app's `DRACOLoader.setDecoderPath` points at the local `draco/` path. The warning is non-fatal under `--strict` because the page works online.

## Estimated size exceeds the limit

Run `estimate_size.py` before committing to a full packaging run:

```bash
python scripts/estimate_size.py dist/index.html --json
```

Or use the wrapper's `--estimate` flag to abort automatically if the projected size exceeds `--max-total-mb`:

```bash
python scripts/package_frontend_build.py . --estimate --max-total-mb 50
```

If the estimate is too large, compress large media (MP4, GLB) before embedding, or exclude large extensions:

```bash
python scripts/inline_assets.py index.html --exclude-ext .mp4,.glb --max-asset-mb 25
```

## Preview server port is in use

`serve_preview.py` auto-detects the first available port starting from `--port`. If you see "Port 8000 in use, using 8001 instead", that is expected. To start from a specific port:

```bash
python scripts/serve_preview.py dist/index.single.html --port 3000 --open
```

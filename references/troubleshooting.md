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

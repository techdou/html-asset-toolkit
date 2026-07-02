# Changelog

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

# Quality Gate

Use this checklist before handing off a single-file HTML artifact.

## Required checks

1. Confirm the input entry:
   - Plain course HTML: `index.html`, `chapter01.html`, or user-specified source file.
   - Frontend build: `dist/index.html`, `build/index.html`, or `out/index.html`.
2. For React/Vue projects, confirm whether `npm run build` or another build command was run.
3. Confirm the output path:
   - Source HTML: `dist/{source-name}.single.html`.
   - Build entry: `{build-dir}/index.single.html`.
4. Inspect the generated `.manifest.json`.
5. Run `validate_single_html.py`; for React/Vue builds, inspect `--json` output if runtime images are missing.
6. Open the generated HTML locally when possible.
7. Check visible resources:
   - CSS layout and fonts.
   - Images and SVG icons.
   - Audio/video controls.
   - JS interactions, including click/state-driven image switching.
   - GLB/STL/Three.js viewer behavior.
8. Report any remaining local references, including `decoded_text_remaining_refs`, or skipped resources.

## Size thresholds

| Final HTML size | Meaning |
|---|---|
| Under 10 MB | Excellent for course handoff |
| 10-50 MB | Acceptable |
| 50-100 MB | Heavy; warn the user |
| Above 100 MB | Very heavy; ask whether to keep single-file packaging |

## Common warnings

- Large MP4 files should be compressed before embedding.
- Large GLB/STL files should be simplified or compressed when possible.
- External CDN scripts remain external unless the user supplies local copies.
- Browser APIs, API calls, login flows, and service workers are not made offline merely by embedding assets.
- Stale `integrity` attributes can break scripts/styles and should be removed after inlining.
- Vite/esbuild static backtick paths are supported; dynamic template paths with `${...}` require source refactoring or bundler imports.

## Handoff message

Include:

```text
Output: path/to/index.single.html
Manifest: path/to/index.single.html.manifest.json
Validation: passed / warnings listed
Notes: remaining external resources or size risks
```

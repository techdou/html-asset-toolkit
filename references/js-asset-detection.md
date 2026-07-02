# JavaScript Asset Detection Robustness

Use this reference when React/Vue/Vite build output still shows missing images or media after packaging.

## Problem pattern

Source code may use normal quoted strings:

```js
const BUILDING_IMAGES = [
  "/buildings/buildingA.jpg",
  "/buildings/buildingB.jpg",
];
```

After Vite/esbuild minification, the same static strings may become template literals:

```js
var Kg=[`/buildings/buildingA.jpg`,`/buildings/buildingB.jpg`];
o&&(o.src=Kg[e]||Kg[0]);
```

If an inliner only scans `"..."` and `'...'`, these backtick paths remain inside the embedded JavaScript. At runtime, the single HTML tries to load `/buildings/buildingB.jpg`, but the external folder no longer exists.

## v2.5.0 behavior

`inline_assets.py` now detects local asset path literals wrapped in all three JavaScript delimiters:

```text
"/assets/logo.png"
'/assets/logo.png'
`/assets/logo.png`
```

The matcher is intentionally conservative:

- It only treats the whole string literal content as an asset URL.
- It excludes whitespace and angle brackets so complete HTML template snippets are not misread as one path.
- It preserves the original quote style after replacement.
- It escapes the replacement for JavaScript string/template literal safety.

## Static vs dynamic template literals

Static template literals can be inlined:

```js
const img = `/buildings/buildingA.jpg`;
```

Dynamic template literals cannot be resolved deterministically:

```js
const img = `/buildings/${buildingName}.jpg`;
```

For dynamic patterns, prefer one of these approaches:

1. Use a static lookup table that lists every possible file path.
2. Import the files through the bundler so they become hashed build assets.
3. Keep the external assets folder and do not claim the output is a fully self-contained single file.

## Validation improvement

`validate_single_html.py` now checks two layers:

1. Surface HTML references such as `src=`, `href=`, `url(...)`, and JS strings still present in the HTML text.
2. Decoded embedded text assets, especially `data:text/javascript;base64,...` and `data:text/css;base64,...`.

This matters because unresolved JS paths may be hidden inside Base64-encoded JavaScript and would not appear as plain text in the final HTML.

## Agent checklist for this bug

When a generated single HTML has missing images after clicking or switching state:

1. Inspect the manifest for `js_file_string` entries.
2. Run `validate_single_html.py` and check `decoded_text_remaining_refs` in JSON output.
3. Search decoded JavaScript for root-relative paths such as `/buildings/`, `/assets/`, `/images/`, `/img/`, or `/static/`.
4. If paths are static backtick literals, rerun with v2.5.0+.
5. If paths contain `${...}`, refactor the app to expose a static path map or import the assets before packaging.

# Inline Modes — data-url vs tag

`inline_assets.py` supports two CSS/JS embedding strategies via `--css-js-mode`:

| Mode | CSS becomes | JS becomes | Default |
|---|---|---|---|
| `data-url` | `<link rel="stylesheet" href="data:text/css;base64,...">` | `<script src="data:text/javascript;base64,...">` | ✅ Yes |
| `tag` | `<style>/* raw CSS */</style>` | `<script>/* raw JS */</script>` | No |

Both modes recursively inline CSS-internal `url()` / `@import` and JS-internal asset strings as Data URLs. The only difference is how the **top-level** CSS/JS file is placed into the HTML.

## When to use data-url (default)

- Maximum compatibility with the existing extract workflow (`extract_assets.py` targets Data URLs).
- Smaller HTML text for simple cases (no extra `<style>`/`<script>` tag overhead).
- You do not have CSP restrictions.

## When to use tag mode

- **Content Security Policy (CSP)**: many production pages disallow `data:` in `style-src` or `script-src`. Tag-inline CSS/JS avoids `data:` URLs for the main stylesheet and entry script, reducing CSP friction.
- **ES modules**: `<script type="module" src="data:...">` has inconsistent browser support. `<script type="module>/* code */</script>` is more reliable.
- **Cross-origin / file:// access**: some browsers block `data:` URLs from certain contexts. Inline tags are treated as same-origin document content.
- **Debugging**: inline `<style>`/`<script>` content is readable in DevTools, unlike opaque Base64 Data URLs.

## Trade-offs

| Aspect | data-url | tag |
|---|---|---|
| CSP friendly | ❌ May need `data:` in policy | ✅ No `data:` for main CSS/JS |
| DevTools readability | ❌ Opaque Base64 | ✅ Readable source |
| Re-extractable via `extract_assets.py` | ✅ Yes | ❌ Tag content is not extracted |
| Internal assets (url() in CSS) | data-url | Still data-url (recursively) |
| Module script support | ⚠️ Browser-dependent | ✅ Reliable |
| HTML size | Slightly larger (Base64 overhead on CSS/JS) | Slightly smaller (raw text) |

## How tag mode handles nested resources

In tag mode, the top-level CSS/JS is placed as raw text inside `<style>`/`<script>`. However, any `url(...)` inside the CSS or asset strings inside the JS are still replaced with Data URLs, because those are binary assets (images, fonts, models) that cannot live as plain text in HTML.

Example transformation (`--css-js-mode tag`):

```html
<!-- Input -->
<link rel="stylesheet" href="style.css">
<script src="app.js"></script>

<!-- Output -->
<style>
.hero { background-image: url('data:image/png;base64,iVBOR...'); }
</style>
<script>
var logo = "data:image/svg+xml;base64,PHN2...";
</script>
```

## Validation in tag mode

`validate_single_html.py` detects inline `<style>` and `<script>` blocks and scans their content for residual local references, reporting them under `tag_inline_refs` in the JSON output. This catches the same class of bugs as `decoded_text_remaining_refs` but for tag-mode output.

# Skill Review — html-asset-toolkit v3.0.0

## Overall score

| Dimension | Score | Notes |
|---|---:|---|
| User usability | 9.5/10 | Clear workflows; wrapper reduces complexity; new estimate/preview scripts close the verify loop. |
| Agent trigger quality | 9.5/10 | Frontmatter includes English and Chinese triggers, tag-inline/estimate/preview terms, concrete file names, build terms, and boundaries. |
| Anthropic format fit | 9.5/10 | Root `SKILL.md`, required frontmatter, scripts, references, progressive disclosure. |
| Script determinism | 9.5/10 | Deterministic Python scripts handle inline (data-url + tag), estimate, wrapper, serve, extract, rename, validate. |
| React/Vue packaging fit | 9.5/10 | Static build artifacts, CSS/JS recursion, Vite/esbuild backtick paths, tag-inline for CSP/module compat, framework-specific guides. |
| Roadmap completion | 10/10 | All four v2.6.0 roadmap items shipped: browser verification helper, tag-inline, report-only estimate, framework examples. |

## User perspective

The user now has two simple mental models:

```text
Course HTML:
index.html + assets/ -> dist/index.single.html
```

```text
React/Vue build:
npm run build -> dist/index.html/build/index.html -> index.single.html
```

The wrapper script improves real usage because the user or Agent can run one command for frontend projects:

```bash
python scripts/package_frontend_build.py .
```

This is easier than remembering the full sequence of `npm run build`, entry detection, inlining, and validation.

## Agent matching perspective

The description now includes practical trigger terms:

- 单文件HTML
- Base64内嵌
- 资源内嵌
- 离线课程演示
- 交互式学习HTML
- 百宝箱HTML
- React/Vue/Vite/CRA/Vue CLI/webpack
- npm run build
- dist/index.html
- build/index.html
- assets/CSS/JS

This should improve matching for both Chinese user prompts and English technical prompts.

## Agent execution improvements

The `SKILL.md` now contains an explicit execution contract:

1. Identify source HTML vs frontend build.
2. Prefer the frontend wrapper for React/Vue packaging.
3. Build first unless existing build output is intentionally reused.
4. Locate the HTML entry.
5. Use deterministic scripts.
6. Validate output.
7. Report output, manifest, warnings, and remaining references.

## v2.6.0 robustness review

The main quality improvement is runtime-path robustness. Vite/esbuild may rewrite ordinary asset strings into static template literals, which previously allowed paths such as `` `/buildings/buildingA.jpg` `` to survive inside Base64-embedded JavaScript. v2.6.0 addresses this in three ways:

1. The inliner recognizes JavaScript asset strings wrapped with `"`, `'`, or `` ` ``.
2. Replacement values are escaped for JavaScript string/template literal contexts.
3. The validator decodes embedded text assets and scans inside `data:text/javascript;base64,...` and `data:text/css;base64,...` for remaining local references.

Dynamic template literals such as `` `/buildings/${name}.jpg` `` remain a source-level design issue; an Agent should recommend a static map or bundler imports rather than pretending the path can be inferred.

## Remaining boundaries

This skill intentionally does not solve:

- API data offline caching.
- Authentication flows.
- Production deployment.
- Service worker/PWA cache correctness.
- CDN resource downloading unless local copies are provided.
- Full browser compatibility for every custom dynamic import/runtime loader.

Those limits are documented so the Agent does not overclaim.

## Recommended next version ideas

- ~~Add an optional browser verification helper using a local static server.~~ ✅ Done in v3.0.0 (`serve_preview.py`)
- ~~Add an option to inline CSS/JS as literal `<style>` and `<script>` rather than Data URL attributes.~~ ✅ Done in v3.0.0 (`--css-js-mode tag`)
- ~~Add a report-only command that estimates final size before embedding.~~ ✅ Done in v3.0.0 (`estimate_size.py`)
- ~~Add framework-specific examples for Vite React, Vite Vue, Vue CLI, CRA, and webpack.~~ ✅ Done in v3.0.0 (`examples/frameworks/`)
- Future: add recursive size estimation for CSS/JS-internal nested assets (currently estimates only direct references).
- Future: add a `--watch` mode to `serve_preview.py` that auto-repackages on file change.

## v2.6.0 review notes

The v2.5.0 review identified three Agent-stability issues: wrapper `--strict` failed, wrapper `--root-dir dist` could resolve as `dist/dist`, and `public/index.html` behavior was ambiguous. v2.6.0 fixes all three and adds smoke coverage.

Quality gate added:

```bash
python tests/smoke_test.py
```

The test now covers normal HTML packaging, React/Vue build packaging, wrapper strict mode, and wrapper `--root-dir dist` behavior.


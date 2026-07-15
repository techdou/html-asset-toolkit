#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test for HTML Asset Toolkit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "index.html"
OUTPUT = ROOT / "examples" / "dist" / "index.single.html"
ALT_EXAMPLE = ROOT / "examples" / "chapter01.html"
ALT_OUTPUT = ROOT / "examples" / "dist" / "chapter01.single.html"
BUILD_EXAMPLE = ROOT / "examples" / "react-vue-build" / "dist" / "index.html"
BUILD_OUTPUT = ROOT / "examples" / "react-vue-build" / "dist" / "index.single.html"
# Inline-blocks example for extract_style_script.py
INLINE_EXAMPLE = ROOT / "examples" / "chapter02.html"
INLINE_OUTPUT_HTML = ROOT / "examples" / "chapter02.externalized.html"
INLINE_ASSET_DIR = ROOT / "examples" / "chapter02_assets"
INLINE_MANIFEST = INLINE_ASSET_DIR / "manifest.style-script.json"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def remove_output(path: Path) -> None:
    if path.exists():
        path.unlink()
    manifest = path.with_suffix(path.suffix + ".manifest.json")
    if manifest.exists():
        manifest.unlink()


def test_plain_course_html() -> None:
    remove_output(OUTPUT)
    remove_output(ALT_OUTPUT)
    ALT_EXAMPLE.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    run([sys.executable, "scripts/inline_assets.py", str(EXAMPLE)])
    assert OUTPUT.exists(), "default output should be examples/dist/index.single.html"
    text = OUTPUT.read_text(encoding="utf-8")
    assert "data:image/png;base64," in text
    assert "data:audio/wav;base64," in text
    assert "data:model/stl;base64," in text
    assert "assets/images/demo.png" not in text
    assert "assets/styles/course.css" not in text
    assert "../models/cube.stl" not in text

    manifest = json.loads((OUTPUT.with_suffix(OUTPUT.suffix + ".manifest.json")).read_text(encoding="utf-8"))
    assert any(e["mime"] == "image/svg+xml" for e in manifest["entries"]), "nested CSS SVG should be inlined"
    assert any(e["context"] == "js_file_string" and e["mime"] == "model/stl" for e in manifest["entries"]), "external JS model string should be inlined"

    run([sys.executable, "scripts/validate_single_html.py", str(OUTPUT), "--max-html-mb", "5", "--strict"])

    run([sys.executable, "scripts/inline_assets.py", str(ALT_EXAMPLE)])
    assert ALT_OUTPUT.exists(), "non-index input should output examples/dist/chapter01.single.html"
    alt_manifest = ALT_OUTPUT.with_suffix(ALT_OUTPUT.suffix + ".manifest.json")
    assert alt_manifest.exists(), "non-index output manifest should exist"


def test_react_vue_build_output() -> None:
    remove_output(BUILD_OUTPUT)

    run([sys.executable, "scripts/inline_assets.py", str(BUILD_EXAMPLE), "--preset", "react-vue-build"])
    assert BUILD_OUTPUT.exists(), "dist/index.html should output dist/index.single.html, not dist/dist/index.single.html"
    assert not (BUILD_EXAMPLE.parent / "dist" / "index.single.html").exists(), "should not create nested dist/dist output for build entry"

    text = BUILD_OUTPUT.read_text(encoding="utf-8")
    assert "/assets/index-a1b2c3.js" not in text
    assert "/assets/index-a1b2c3.css" not in text
    assert "/assets/bg-a1b2c3.png" not in text
    assert "/assets/chunk-d4e5f6.js" not in text
    assert "/buildings/buildingA.jpg" not in text
    assert "/buildings/buildingB.jpg" not in text
    assert "integrity=" not in text
    assert "data:text/javascript;base64," in text
    assert "data:text/css;base64," in text

    manifest_path = BUILD_OUTPUT.with_suffix(BUILD_OUTPUT.suffix + ".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["frontend_build_entry"] is True
    assert manifest["preset"] == "react-vue-build"
    assert any(e["source"] == "/assets/index-a1b2c3.js" and e["action"] == "inlined" for e in manifest["entries"])
    assert any(e["source"] == "/assets/index-a1b2c3.css" and e["action"] == "inlined" for e in manifest["entries"])
    assert any(e["context"] == "css_file_import" for e in manifest["entries"]), "CSS @import should be processed"
    assert any(e["source"] == "/buildings/buildingA.jpg" and e["context"] == "js_file_string" and e["action"] == "inlined" for e in manifest["entries"]), "Vite/esbuild backtick template literal asset paths should be processed"

    run([sys.executable, "scripts/validate_single_html.py", str(BUILD_OUTPUT), "--max-html-mb", "5", "--strict"])

    remove_output(BUILD_OUTPUT)
    run([sys.executable, "scripts/package_frontend_build.py", str(BUILD_EXAMPLE.parents[1]), "--skip-build", "--entry", "dist/index.html"])
    assert BUILD_OUTPUT.exists(), "frontend wrapper should package existing dist/index.html"

    remove_output(BUILD_OUTPUT)
    run([sys.executable, "scripts/package_frontend_build.py", str(BUILD_EXAMPLE.parents[1]), "--skip-build", "--entry", "dist/index.html", "--strict"])
    assert BUILD_OUTPUT.exists(), "frontend wrapper strict mode should validate without passing unsupported validator args"

    remove_output(BUILD_OUTPUT)
    run([sys.executable, "scripts/package_frontend_build.py", str(BUILD_EXAMPLE.parents[1]), "--skip-build", "--entry", "dist/index.html", "--root-dir", "dist", "--strict"])
    assert BUILD_OUTPUT.exists(), "frontend wrapper should resolve --root-dir dist from the project root"
    rooted_text = BUILD_OUTPUT.read_text(encoding="utf-8")
    assert "/assets/index-a1b2c3.js" not in rooted_text
    assert "/buildings/buildingA.jpg" not in rooted_text


def test_estimate_size() -> None:
    """estimate_size.py should report projected sizes without writing files."""
    est_cmd = [sys.executable, "scripts/estimate_size.py", str(EXAMPLE), "--json"]
    print("$", " ".join(est_cmd))
    completed = subprocess.run(est_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    import json
    report = json.loads(completed.stdout)
    assert report["input_html"] == str(EXAMPLE)
    assert report["estimated_final_html_bytes"] > 0
    assert len(report["assets"]) > 0
    found = [a for a in report["assets"] if a["status"] == "found"]
    assert found, "estimate should find at least one asset"
    # Ensure estimate_size did not create any new manifest files.
    # (examples/dist/ may already exist from test_plain_course_html, so we check
    # that estimate_size itself produces no side effects by verifying it does
    # not have an "output" or "manifest" field.)
    assert "output" not in report, "estimate_size should not report an output path"
    assert "manifest" not in report, "estimate_size should not report a manifest path"


def test_tag_inline_mode() -> None:
    """--css-js-mode tag should produce <style>/<script> blocks, not data URLs."""
    remove_output(OUTPUT)
    run([sys.executable, "scripts/inline_assets.py", str(EXAMPLE), "--css-js-mode", "tag"])
    text = OUTPUT.read_text(encoding="utf-8")
    assert "<style" in text, "tag mode should produce a <style> block"
    assert "<script>" in text or '<script type=' in text, "tag mode should produce an inline <script>"
    # The top-level CSS/JS should NOT be data URLs anymore.
    assert "data:text/css;base64," not in text, "tag mode should not use CSS data URLs for the main stylesheet"
    assert "data:text/javascript;base64," not in text, "tag mode should not use JS data URLs for the main script"
    # Internal assets should still be inlined as data URLs.
    assert "data:image/png;base64," in text, "internal PNG should still be a data URL"

    manifest_path = OUTPUT.with_suffix(OUTPUT.suffix + ".manifest.json")
    import json
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["css_js_mode"] == "tag"

    run([sys.executable, "scripts/validate_single_html.py", str(OUTPUT), "--max-html-mb", "5", "--strict"])


def test_validate_tag_mode() -> None:
    """Validator should scan inline <style>/<script> blocks and report tag_inline_refs."""
    remove_output(OUTPUT)
    run([sys.executable, "scripts/inline_assets.py", str(EXAMPLE), "--css-js-mode", "tag"])
    val_cmd = [sys.executable, "scripts/validate_single_html.py", str(OUTPUT), "--json"]
    print("$", " ".join(val_cmd))
    completed = subprocess.run(val_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    import json
    report = json.loads(completed.stdout)
    assert "tag_inline_refs" in report, "validator should include tag_inline_refs field"


def test_serve_preview() -> None:
    """serve_preview.py should start, respond to HTTP, and shut down cleanly."""
    import socket
    import threading
    import time
    import urllib.request

    # Find a free port to avoid conflicts.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    free_port = sock.getsockname()[1]
    sock.close()

    proc = subprocess.Popen(
        [sys.executable, "scripts/serve_preview.py", str(EXAMPLE), "--port", str(free_port), "--no-browser"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(1.5)
        url = f"http://127.0.0.1:{free_port}/{EXAMPLE.name}"
        response = urllib.request.urlopen(url, timeout=5)
        assert response.status == 200, "preview server should return 200"
        body = response.read().decode("utf-8", errors="replace")
        assert "课程演示" in body or "<html" in body.lower(), "preview server should serve the HTML content"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_extract_style_script() -> None:
    """extract_style_script.py splits <style>/<script> blocks into external files."""
    import shutil
    if INLINE_OUTPUT_HTML.exists():
        INLINE_OUTPUT_HTML.unlink()
    if INLINE_ASSET_DIR.exists():
        shutil.rmtree(INLINE_ASSET_DIR)

    run([sys.executable, "scripts/extract_style_script.py", str(INLINE_EXAMPLE)])
    assert INLINE_OUTPUT_HTML.exists(), "externalized HTML should be written"
    assert INLINE_ASSET_DIR.exists(), "asset dir should be created"
    assert INLINE_MANIFEST.exists(), "manifest should be written"

    text = INLINE_OUTPUT_HTML.read_text(encoding="utf-8")
    assert "<style" not in text, "inline <style> block should be replaced"
    assert '<link rel="stylesheet" href="chapter02_assets/' in text, "style should be referenced via <link>"
    # External script with src must be preserved as-is.
    assert 'src="assets/scripts/viewer.js"' in text, "external <script src> must be untouched"
    # Inline <script> bootstrap must be replaced by a <script src> pointing at the asset dir.
    assert 'src="chapter02_assets/' in text, "inline <script> should be replaced by <script src>"

    manifest = json.loads(INLINE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["style_count"] == 1, "exactly one <style> block expected"
    assert manifest["script_count"] == 1, "exactly one inline <script> block expected"
    assert manifest["style_bytes"] > 0
    assert manifest["script_bytes"] > 0
    kinds = {a["kind"] for a in manifest["assets"]}
    assert kinds == {"style", "script"}, f"asset kinds mismatch: {kinds}"

    # Files actually exist on disk.
    for entry in manifest["assets"]:
        assert (INLINE_ASSET_DIR / entry["filename"]).exists(), f"missing extracted file: {entry['filename']}"

    # JSON mode should emit a valid JSON report.
    json_cmd = [sys.executable, "scripts/extract_style_script.py", str(INLINE_EXAMPLE), "--dry-run", "--json"]
    completed = subprocess.run(json_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    report = json.loads(completed.stdout)
    assert report["style_count"] == 1 and report["script_count"] == 1


def test_rename_with_near_text() -> None:
    """rename_extracted_assets.py should mine near_text_before for a label."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        asset_dir = td_path / "assets"
        asset_dir.mkdir()
        # fake extracted asset file
        (asset_dir / "asset_001_abc123.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        manifest = td_path / "manifest.json"
        manifest.write_text(json.dumps({
            "assets": [{
                "index": 1,
                "filename": "asset_001_abc123.png",
                "mime": "image/png",
                "context": {
                    "alt": "", "title": "", "heading": "", "id": "", "class": "", "tag": "", "mime_group": "image",
                    "near_text_before": 'name:"七鳃鳗",era:"泥盆纪",image:"data:image/png;base64,',
                },
            }],
        }), encoding="utf-8")

        run([sys.executable, "scripts/rename_extracted_assets.py", str(asset_dir), "--manifest", str(manifest)])
        names = [p.name for p in asset_dir.iterdir()]
        assert any("七鳃鳗" in n for n in names), f"near_text label not used: {names}"
        # default separator is now '-'
        assert any(n.startswith("001-") for n in names), f"separator should be '-': {names}"


def test_rename_update_html() -> None:
    """rename_extracted_assets.py --update-html should rewrite references in lockstep."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        asset_dir = td_path / "assets"
        asset_dir.mkdir()
        (asset_dir / "asset_001_abc.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        manifest = td_path / "manifest.json"
        manifest.write_text(json.dumps({
            "assets": [{
                "index": 1,
                "filename": "asset_001_abc.png",
                "mime": "image/png",
                "context": {"alt": "demo image", "mime_group": "image"},
            }],
        }), encoding="utf-8")
        html = td_path / "page.html"
        html.write_text('<img src="assets/asset_001_abc.png">', encoding="utf-8")

        run([sys.executable, "scripts/rename_extracted_assets.py", str(asset_dir),
             "--manifest", str(manifest), "--update-html", str(html)])
        # file renamed
        assert not (asset_dir / "asset_001_abc.png").exists(), "old file should be renamed away"
        new_files = list(asset_dir.iterdir())
        assert len(new_files) == 1
        new_name = new_files[0].name
        # HTML reference rewritten
        body = html.read_text(encoding="utf-8")
        assert new_name in body, f"new name {new_name} not in HTML body"
        assert "asset_001_abc.png" not in body, "old reference should be gone"


def test_rename_update_html_scoped() -> None:
    """--update-html must only rewrite attribute values, not body text or comments.

    Regression guard for v4.1.0: a bare str.replace would also rewrite the
    filename when it appears in prose/comments/JS, corrupting unrelated content.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        asset_dir = td_path / "assets"
        asset_dir.mkdir()
        old_name = "asset_001_abc.png"
        (asset_dir / old_name).write_bytes(b"\x89PNG\r\n\x1a\n")
        manifest = td_path / "manifest.json"
        manifest.write_text(json.dumps({
            "assets": [{
                "index": 1,
                "filename": old_name,
                "mime": "image/png",
                "context": {"alt": "demo image", "mime_group": "image"},
            }],
        }), encoding="utf-8")
        # The HTML references the asset in an attribute (should rewrite) AND
        # mentions the same filename in body text + a comment (should NOT touch).
        html = td_path / "page.html"
        html.write_text(
            f'<img src="assets/{old_name}">\n'
            f'<!-- see {old_name} for reference -->\n'
            f'<p>The file {old_name} is mentioned here in prose.</p>\n',
            encoding="utf-8",
        )

        run([sys.executable, "scripts/rename_extracted_assets.py", str(asset_dir),
             "--manifest", str(manifest), "--update-html", str(html)])

        new_files = [p.name for p in asset_dir.iterdir()]
        assert len(new_files) == 1
        new_name = new_files[0]
        assert new_name != old_name

        body = html.read_text(encoding="utf-8")
        # Attribute reference was rewritten.
        assert new_name in body, "attribute reference should be rewritten"
        assert f'src="assets/{old_name}"' not in body, "old attribute ref should be gone"
        # Body text and comment survived untouched.
        assert body.count(old_name) == 2, (
            f"expected old name preserved exactly twice (comment + prose), "
            f"got {body.count(old_name)}: {body!r}"
        )


def test_p0_script_escape() -> None:
    """tag mode must escape </script> inside inlined JS so the HTML parser does
    not close the tag early. React/Vue minified runtimes almost always contain
    the literal "</script>".
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # JS source contains the exact string that breaks naive tag inlining.
        js_with_close = (
            'var fragment = "<script>doStuff()</script>";\n'
            'var upper = "</SCRIPT>";\n'
            'console.log(fragment, upper);\n'
        )
        (td_path / "app.js").write_text(js_with_close, encoding="utf-8")
        # CSS source contains </style> as well.
        css_with_close = 'body::after{content:"</style>";}\n'
        (td_path / "style.css").write_text(css_with_close, encoding="utf-8")
        html_src = (
            '<!doctype html><html><head>\n'
            '<link rel="stylesheet" href="style.css">\n'
            '</head><body>\n'
            '<script src="app.js"></script>\n'
            '</body></html>\n'
        )
        entry = td_path / "index.html"
        entry.write_text(html_src, encoding="utf-8")

        run([sys.executable, "scripts/inline_assets.py", str(entry), "--css-js-mode", "tag", "--out", str(td_path / "out.html")])
        out = (td_path / "out.html")
        text = out.read_text(encoding="utf-8")
        # The escaped form must be present...
        assert r"<\/script>" in text, "tag mode should escape </script> as <\\/script>"
        assert r"<\/style>" in text, "tag mode should escape </style> as <\\/style>"
        # ...and no unescaped closing tag should appear inside the inline blocks.
        # We check by extracting the inline script block the same way the
        # validator does, then asserting no raw </script> remains.
        import re
        script_blocks = re.findall(
            r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", text, re.IGNORECASE | re.DOTALL,
        )
        assert script_blocks, "tag mode should produce an inline <script> block"
        for block in script_blocks:
            # Look for </script not preceded by a backslash.
            assert not re.search(r"(?<!\\)</script", block, re.IGNORECASE), (
                f"unescaped </script> remains inside inline script block: {block!r}"
            )

        # Validator must not report the unescaped-</script> error for this output.
        val_cmd = [sys.executable, "scripts/validate_single_html.py", str(out), "--json"]
        print("$", " ".join(val_cmd))
        completed = subprocess.run(val_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
        report = json.loads(completed.stdout)
        assert report["errors"] == [], f"validator should report no errors, got: {report['errors']}"

        # Reverse test: a deliberately broken HTML (unescaped </script> inside
        # an inline script, the React/Vue paired-literal form) MUST be caught.
        broken = (
            '<html><body>\n'
            '<script>document.write("<script>hydration</script>")</script>\n'
            '</body></html>\n'
        )
        broken_path = td_path / "broken.html"
        broken_path.write_text(broken, encoding="utf-8")
        bad_cmd = [sys.executable, "scripts/validate_single_html.py", str(broken_path), "--json"]
        print("$", " ".join(bad_cmd))
        bad_completed = subprocess.run(bad_cmd, cwd=ROOT, capture_output=True, text=True)
        bad_report = json.loads(bad_completed.stdout)
        assert bad_report["errors"], "validator must report an error for unescaped </script> in inline script"
        assert bad_completed.returncode == 1, "broken HTML must cause non-zero exit code"


def test_nextjs_fallback() -> None:
    """Next.js dynamic import emits relative `static/chunks/x.js` refs but the
    files live under `_next/static/chunks/`. The inliner should fall back to the
    `_next/` directory automatically when it exists — no manual symlink needed.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # Mirror real Next.js export layout: out/_next/static/chunks/...
        chunks_dir = td_path / "_next" / "static" / "chunks"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "model-a1b2.js").write_text(
            'window.__loaded=true;console.log("chunk loaded");', encoding="utf-8",
        )
        media_dir = td_path / "_next" / "static" / "media"
        media_dir.mkdir(parents=True)
        (media_dir / "texture-a1b2.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        # HTML references the chunks via the bare `static/...` form that
        # Next.js dynamic() emits inside its runtime JS, AND a root-relative
        # `/static/...` form. The entry script itself is referenced via /_next/
        # which already resolves.
        entry_js = td_path / "_next" / "static" / "chunks" / "app-entry.js"
        entry_js.write_text(
            'import("/static/chunks/model-a1b2.js");\n'
            'var tex="/static/media/texture-a1b2.png";\n',
            encoding="utf-8",
        )
        html_src = (
            '<!doctype html><html><head></head><body>\n'
            '<script src="/_next/static/chunks/app-entry.js"></script>\n'
            '</body></html>\n'
        )
        entry = td_path / "index.html"
        entry.write_text(html_src, encoding="utf-8")

        run([sys.executable, "scripts/inline_assets.py", str(entry), "--css-js-mode", "tag", "--out", str(td_path / "out.html")])
        out = td_path / "out.html"
        manifest = json.loads(
            (out.with_suffix(out.suffix + ".manifest.json")).read_text(encoding="utf-8")
        )
        inlined_sources = [e["source"] for e in manifest["entries"] if e["action"] == "inlined"]
        assert "/static/chunks/model-a1b2.js" in inlined_sources, (
            f"Next.js dynamic chunk should be inlined via _next fallback; "
            f"inlined sources: {inlined_sources}"
        )
        assert "/static/media/texture-a1b2.png" in inlined_sources, (
            f"Next.js media asset should be inlined via _next fallback; "
            f"inlined sources: {inlined_sources}"
        )
        missing = [e for e in manifest["entries"] if e["action"] == "missing_or_external"
                   and not e["source"].startswith(("http", "//", "data:"))]
        assert not missing, f"no local refs should be missing, but got: {missing}"

        text = out.read_text(encoding="utf-8")
        assert "static/chunks/model-a1b2.js" not in text, "chunk path should be gone after inlining"


def test_draco_warning() -> None:
    """Validator should emit a dedicated Draco decoder warning when inline JS
    references draco_decoder, and --strict must NOT fail because of it (works
    online when the CDN is reachable).
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        draco_js = (
            'var decoderPath = "https://www.gstatic.com/draco/versioned/decoders/1.5.5/";\n'
            'loader.setDecoderPath(decoderPath);\n'
            '// loads draco_decoder.js / draco_wasm_wrapper.js / draco_decoder.wasm\n'
        )
        (td_path / "app.js").write_text(draco_js, encoding="utf-8")
        html_src = (
            '<!doctype html><html><head></head><body>\n'
            '<script src="app.js"></script>\n'
            '</body></html>\n'
        )
        entry = td_path / "index.html"
        entry.write_text(html_src, encoding="utf-8")

        run([sys.executable, "scripts/inline_assets.py", str(entry), "--css-js-mode", "tag", "--out", str(td_path / "out.html")])
        out = td_path / "out.html"

        val_cmd = [sys.executable, "scripts/validate_single_html.py", str(out), "--json"]
        print("$", " ".join(val_cmd))
        completed = subprocess.run(val_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
        report = json.loads(completed.stdout)
        assert report["draco_warnings"], "validator should report a Draco decoder warning"
        draco_text = " ".join(report["draco_warnings"]).lower()
        assert "draco" in draco_text
        assert "gstatic" in draco_text, "Draco warning should point at the gstatic CDN URL"
        assert report["errors"] == [], "Draco absence must not be an error"

        # Under --strict, Draco-only warnings must not cause failure.
        strict_cmd = [sys.executable, "scripts/validate_single_html.py", str(out), "--strict", "--json"]
        print("$", " ".join(strict_cmd))
        strict_completed = subprocess.run(strict_cmd, cwd=ROOT, capture_output=True, text=True)
        assert strict_completed.returncode == 0, (
            f"--strict should not fail on Draco-only warning; rc={strict_completed.returncode}, "
            f"stderr={strict_completed.stderr[:300]}"
        )


def main() -> int:
    test_plain_course_html()
    test_react_vue_build_output()
    test_estimate_size()
    test_tag_inline_mode()
    test_validate_tag_mode()
    test_p0_script_escape()
    test_nextjs_fallback()
    test_draco_warning()
    test_serve_preview()
    test_extract_style_script()
    test_rename_with_near_text()
    test_rename_update_html()
    test_rename_update_html_scoped()
    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

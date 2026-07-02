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


def main() -> int:
    test_plain_course_html()
    test_react_vue_build_output()
    test_estimate_size()
    test_tag_inline_mode()
    test_validate_tag_mode()
    test_serve_preview()
    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

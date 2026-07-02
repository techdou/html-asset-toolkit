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


def main() -> int:
    test_plain_course_html()
    test_react_vue_build_output()
    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

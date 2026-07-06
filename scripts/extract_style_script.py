#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract inline <style> and <script> blocks from HTML into external files.

This is the reverse of inline_assets.py's tag mode for the top-level CSS/JS
blocks: it splits <style>...</style> into .css files (referenced via <link>)
and inline <script>...</script> (no src) into .js files (referenced via
<script src>). It complements extract_assets.py, which only handles Base64
Data URL assets (images, audio, models, ...).

Output convention mirrors extract_assets.py:
  - default output dir : <input_stem>_assets/
  - default output HTML: <input_stem>.externalized.html
  - manifest           : <output_dir>/manifest.json
  - filenames          : asset_style_NNN_<hash>.css / asset_script_NNN_<hash>.js

Only prints summary stats to stdout — never dumps HTML content — to protect
the agent's context window.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Match <style ...> BODY </style>. BODY may contain anything (DOTALL).
STYLE_RE = re.compile(r"<style\b([^>]*)>(.*?)</style>", re.I | re.S)
# Match <script ...> BODY </script>. We later decide inline vs external by attrs.
SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.I | re.S)

# script attributes worth preserving when rewriting to <script src=...>.
KEEP_SCRIPT_ATTRS = ("type", "defer", "async", "crossorigin", "nonce", "referrerpolicy")


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def parse_attrs(attr_str: str) -> dict[str, str]:
    """Parse a tag's attribute string into {name: value}; boolean attrs -> ''."""
    attrs: dict[str, str] = {}
    for m in re.finditer(r'([a-zA-Z_:][\w:.-]*)\s*=\s*(["\'])(.*?)\2', attr_str, re.S):
        attrs[m.group(1).lower()] = m.group(3)
    for m in re.finditer(r'\s([a-zA-Z_:][\w:.-]+)(?=\s|$|/?>)', attr_str):
        name = m.group(1).lower()
        if name not in attrs:
            attrs[name] = ""
    return attrs


def attrs_to_str(attrs: dict[str, str]) -> str:
    parts = []
    for k, v in attrs.items():
        parts.append(k if v == "" else f'{k}="{v}"')
    return " ".join(parts)


def relpath(target: Path, base_dir: Path) -> str:
    try:
        return target.relative_to(base_dir).as_posix()
    except ValueError:
        return target.resolve().as_posix()


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract inline <style>/<script> blocks into external files.")
    ap.add_argument("input_html", type=Path)
    ap.add_argument("--output-dir", type=Path, default=None)
    ap.add_argument("--out-html", type=Path, default=None)
    ap.add_argument("--prefix", default="asset")
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", dest="as_json", action="store_true", help="emit JSON report to stdout")
    args = ap.parse_args()

    if not args.input_html.exists():
        print(f"ERROR: input HTML not found: {args.input_html}", file=sys.stderr)
        return 1

    input_parent = args.input_html.parent
    out_dir = args.output_dir or input_parent / f"{args.input_html.stem}_assets"
    out_html = args.out_html or args.input_html.with_name(args.input_html.stem + ".externalized.html")
    # Use a distinct manifest name so we do not clobber extract_assets.py's
    # manifest.json when both write to the same _assets/ directory.
    manifest_path = args.manifest or out_dir / "manifest.style-script.json"

    html = args.input_html.read_text(encoding="utf-8")

    style_n = script_n = 0
    style_bytes = script_bytes = 0
    assets: list[dict] = []

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    def make_path(kind: str, idx: int, body: str) -> Path:
        ext = ".css" if kind == "style" else ".js"
        return out_dir / f"{args.prefix}_{kind}_{idx:03d}_{short_hash(body)}{ext}"

    # --- <style> blocks ---
    def replace_style(m: re.Match) -> str:
        nonlocal style_n, style_bytes
        body = m.group(2).strip()
        if not body:
            return m.group(0)
        style_n += 1
        style_bytes += len(body.encode("utf-8"))
        fpath = make_path("style", style_n, body)
        assets.append({"kind": "style", "filename": fpath.name, "bytes": len(body.encode("utf-8")), "hash": short_hash(body)})
        if not args.dry_run:
            fpath.write_text(body, encoding="utf-8")
            print(f"[style {style_n:03d}] {len(body):>7} bytes -> {fpath.name}")
        rel = relpath(fpath, input_parent)
        return f'<link rel="stylesheet" href="{rel}">'

    html = STYLE_RE.sub(replace_style, html)

    # --- inline <script> blocks (those without src) ---
    def replace_script(m: re.Match) -> str:
        nonlocal script_n, script_bytes
        attr_str = m.group(1)
        body = m.group(2).strip()
        attrs = parse_attrs(attr_str)
        if "src" in attrs:
            return m.group(0)  # already external
        if not body:
            return m.group(0)  # empty inline, leave as-is
        script_n += 1
        script_bytes += len(body.encode("utf-8"))
        fpath = make_path("script", script_n, body)
        assets.append({"kind": "script", "filename": fpath.name, "bytes": len(body.encode("utf-8")), "hash": short_hash(body)})
        if not args.dry_run:
            fpath.write_text(body, encoding="utf-8")
            print(f"[script {script_n:03d}] {len(body):>7} bytes -> {fpath.name}")
        rel = relpath(fpath, input_parent)
        keep = {k: v for k, v in attrs.items() if k in KEEP_SCRIPT_ATTRS}
        keep_str = attrs_to_str(keep)
        return f'<script src="{rel}"{(" " + keep_str) if keep_str else ""}></script>'

    html = SCRIPT_RE.sub(replace_script, html)

    if not args.dry_run:
        out_html.write_text(html, encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "input": str(args.input_html),
                    "output_dir": str(out_dir),
                    "out_html": str(out_html),
                    "style_count": style_n,
                    "script_count": script_n,
                    "style_bytes": style_bytes,
                    "script_bytes": script_bytes,
                    "assets": assets,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    report = {
        "input": str(args.input_html),
        "output_dir": str(out_dir),
        "out_html": str(out_html),
        "style_count": style_n,
        "script_count": script_n,
        "style_bytes": style_bytes,
        "script_bytes": script_bytes,
        "total": style_n + script_n,
    }
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        suffix = " (dry-run)" if args.dry_run else ""
        print(f"<style> blocks extracted : {style_n}  ({style_bytes:,} bytes){suffix}")
        print(f"<script> blocks extracted: {script_n}  ({script_bytes:,} bytes){suffix}")
        if not args.dry_run:
            print(f"output dir : {out_dir}")
            print(f"output html: {out_html}")
            print(f"manifest   : {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

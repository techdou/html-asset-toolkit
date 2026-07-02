#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract Base64 Data URL assets from an HTML file."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA_URL_RE = re.compile(
    r"data:(?P<mime>[a-zA-Z0-9.+\-]+/[a-zA-Z0-9.+\-]+)(?P<params>(?:;[^,;]+)*);base64,(?P<data>[A-Za-z0-9+/=\s]+)",
    re.IGNORECASE,
)

MIME_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
    "image/bmp": ".bmp",
    "image/avif": ".avif",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "model/gltf-binary": ".glb",
    "model/gltf+json": ".gltf",
    "model/stl": ".stl",
    "model/obj": ".obj",
    "model/vnd.usdz+zip": ".usdz",
    "application/pdf": ".pdf",
    "application/json": ".json",
    "application/wasm": ".wasm",
    "text/css": ".css",
    "text/javascript": ".js",
    "application/javascript": ".js",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/xml": ".xml",
    "font/woff": ".woff",
    "font/woff2": ".woff2",
    "font/ttf": ".ttf",
    "font/otf": ".otf",
    "application/vnd.ms-fontobject": ".eot",
    "application/octet-stream": ".bin",
}


@dataclass
class ExtractedAsset:
    index: int
    filename: str
    mime: str
    bytes: int
    hash: str
    start: int
    end: int
    context: dict


def ext_for_mime(mime: str) -> str:
    return MIME_EXT.get(mime.lower(), ".bin")


def decode_data(match: re.Match) -> bytes:
    clean = re.sub(r"\s+", "", match.group("data"))
    return base64.b64decode(clean)


def strip_tags(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_attr(tag: str, name: str) -> str:
    m = re.search(rf"\b{name}\s*=\s*([\"'])(.*?)\1", tag, flags=re.I | re.S)
    return re.sub(r"\s+", " ", m.group(2)).strip() if m else ""


def nearest_tag_before(html: str, pos: int) -> str:
    start = html.rfind("<", 0, pos)
    end = html.find(">", start, pos + 500) if start >= 0 else -1
    if start >= 0 and end >= pos:
        return html[start:end + 1]
    # data URL may be inside a long tag; find the tag that starts before pos and ends after pos
    tag_start = html.rfind("<", 0, pos)
    tag_end = html.find(">", pos)
    if tag_start >= 0 and tag_end >= pos:
        return html[tag_start:tag_end + 1]
    return ""


def preceding_heading(html: str, pos: int) -> str:
    heads = list(re.finditer(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]>", html[:pos], flags=re.I | re.S))
    if not heads:
        return ""
    return strip_tags(heads[-1].group(1))


def capture_context(html: str, start: int, end: int, mime: str) -> dict:
    tag = nearest_tag_before(html, start)
    tag_name = ""
    m = re.match(r"<\s*([a-zA-Z0-9:-]+)", tag)
    if m:
        tag_name = m.group(1).lower()
    window_before = html[max(0, start - 1200):start]
    window_after = html[end:min(len(html), end + 400)]
    return {
        "tag": tag_name,
        "alt": extract_attr(tag, "alt"),
        "title": extract_attr(tag, "title"),
        "id": extract_attr(tag, "id"),
        "class": extract_attr(tag, "class"),
        "heading": preceding_heading(html, start),
        "near_text_before": strip_tags(window_before)[-180:],
        "near_text_after": strip_tags(window_after)[:120],
        "mime_group": mime.split("/", 1)[0] if "/" in mime else mime,
    }


def default_output_dir(input_html: Path) -> Path:
    return input_html.parent / f"{input_html.stem}_assets"


def relpath_for_html(target: Path, html_path: Path) -> str:
    try:
        return target.relative_to(html_path.parent).as_posix()
    except ValueError:
        return target.resolve().as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Base64 Data URL assets from HTML.")
    parser.add_argument("input_html", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--out-html", type=Path, default=None)
    parser.add_argument("--prefix", default="asset")
    parser.add_argument("--min-bytes", type=int, default=1)
    args = parser.parse_args()

    if not args.input_html.exists():
        print(f"ERROR: input HTML not found: {args.input_html}", file=sys.stderr)
        return 1

    out_dir = args.output_dir or default_output_dir(args.input_html)
    manifest_path = args.manifest or out_dir / "manifest.json"
    out_html = args.out_html or args.input_html.with_suffix(args.input_html.suffix + ".externalized.html")
    out_dir.mkdir(parents=True, exist_ok=True)

    html = args.input_html.read_text(encoding="utf-8")
    replacements: list[tuple[int, int, str]] = []
    assets: list[ExtractedAsset] = []

    counter = 0
    for match in DATA_URL_RE.finditer(html):
        mime = match.group("mime").lower()
        try:
            raw = decode_data(match)
        except Exception as exc:
            print(f"WARN: failed to decode data URL at {match.start()}: {exc}")
            continue
        if len(raw) < args.min_bytes:
            continue
        counter += 1
        short_hash = hashlib.sha256(raw).hexdigest()[:10]
        ext = ext_for_mime(mime)
        filename = f"{args.prefix}_{counter:03d}_{short_hash}{ext}"
        file_path = out_dir / filename
        file_path.write_bytes(raw)
        context = capture_context(html, match.start(), match.end(), mime)
        assets.append(ExtractedAsset(counter, filename, mime, len(raw), short_hash, match.start(), match.end(), context))
        if args.replace:
            replacements.append((match.start(), match.end(), relpath_for_html(file_path, args.input_html)))
        print(f"[{counter:03d}] {mime} -> {filename} ({len(raw)} bytes)")

    if args.replace:
        externalized = html
        for start, end, repl in reversed(replacements):
            externalized = externalized[:start] + repl + externalized[end:]
        out_html.write_text(externalized, encoding="utf-8")

    report = {
        "input": str(args.input_html),
        "output_dir": str(out_dir),
        "externalized_html": str(out_html) if args.replace else None,
        "total": len(assets),
        "assets": [asdict(a) for a in assets],
    }
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted: {len(assets)} asset(s)")
    print(f"Manifest: {manifest_path}")
    if args.replace:
        print(f"Externalized HTML: {out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

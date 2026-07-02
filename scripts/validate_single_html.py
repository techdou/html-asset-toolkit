#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate embedded Data URLs and remaining local references in a single HTML file."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA_URL_BASE64_RE = re.compile(
    r"data:(?P<mime>[a-zA-Z0-9.+\-]+/[a-zA-Z0-9.+\-]+)(?P<params>(?:;[^,;]+)*);base64,(?P<data>[A-Za-z0-9+/=\s]+)",
    re.IGNORECASE,
)

DATA_URL_ANY_RE = re.compile(r"data:(?P<mime>[a-zA-Z0-9.+\-]+/[a-zA-Z0-9.+\-]+)[^\"'\s)>]*", re.IGNORECASE)

LOCAL_REF_RE = re.compile(
    r"\b(?:src|href|poster|data)\s*=\s*([\"'])(?!data:)(?P<url>[^\"']+?)\1",
    re.IGNORECASE,
)

CSS_URL_RE = re.compile(r"url\(\s*([\"']?)(?!data:)(?P<url>[^)\"']+)\1\s*\)", re.IGNORECASE)

ASSET_EXT_RE = r"png|jpe?g|webp|gif|svg|ico|bmp|avif|mp3|wav|ogg|m4a|aac|flac|mp4|m4v|webm|mov|glb|gltf|stl|obj|usdz|pdf|json|wasm|css|js|mjs|txt|csv|xml|woff2?|ttf|otf|eot"
JS_STRING_RE = re.compile(
    r"(?P<quote>[\"'`])"
    r"(?P<url>(?!data:)(?!https?://)(?!//)[^\"'`\s<>]+?\.(?:" + ASSET_EXT_RE + r")"
    r"(?:(?:\?[^\"'`\s<>]*)|(?:#[^\"'`\s<>]*))?)"
    r"(?P=quote)",
    re.IGNORECASE,
)

EXTERNAL_PREFIXES = ("http://", "https://", "//", "mailto:", "tel:", "#", "javascript:")
TEXT_ASSET_MIMES = {
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
    "text/css",
    "text/html",
    "application/json",
}


def decode_payload(match: re.Match) -> bytes:
    clean = re.sub(r"\s+", "", match.group("data"))
    return base64.b64decode(clean)


def decode_len(match: re.Match) -> int:
    try:
        return len(decode_payload(match))
    except Exception:
        return 0


def fmt(n: int) -> str:
    value = float(n)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{n} B"


def is_external(url: str) -> bool:
    return url.lower().startswith(EXTERNAL_PREFIXES) or "${" in url or "{{" in url


def collect_remaining_refs(html: str) -> dict:
    attr_refs = [m.group("url") for m in LOCAL_REF_RE.finditer(html) if not is_external(m.group("url"))]
    css_refs = [m.group("url") for m in CSS_URL_RE.finditer(html) if not is_external(m.group("url"))]
    js_refs = [m.group("url") for m in JS_STRING_RE.finditer(html) if not is_external(m.group("url"))]
    return {
        "attributes": sorted(set(attr_refs)),
        "css_urls": sorted(set(css_refs)),
        "js_strings": sorted(set(js_refs)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a single-file HTML with embedded Data URLs.")
    parser.add_argument("input_html", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-html-mb", type=float, default=50)
    parser.add_argument("--max-asset-mb", type=float, default=25)
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Alias for --fail-on-warning; useful for wrapper scripts and agents.")
    args = parser.parse_args()

    if not args.input_html.exists():
        print(f"ERROR: file not found: {args.input_html}", file=sys.stderr)
        return 1

    html = args.input_html.read_text(encoding="utf-8")
    html_bytes = len(html.encode("utf-8"))
    by_mime: Counter[str] = Counter()
    bytes_by_mime: defaultdict[str, int] = defaultdict(int)
    assets = []
    warnings = []
    decoded_text_refs: list[dict] = []

    base64_spans: list[tuple[int, int]] = []
    for i, match in enumerate(DATA_URL_BASE64_RE.finditer(html), 1):
        mime = match.group("mime").lower()
        decoded = decode_len(match)
        encoded_chars = match.end() - match.start()
        by_mime[mime] += 1
        bytes_by_mime[mime] += decoded
        base64_spans.append((match.start(), match.end()))
        item = {"index": i, "mime": mime, "decoded_bytes": decoded, "encoded_chars": encoded_chars}
        assets.append(item)
        if mime in TEXT_ASSET_MIMES and decoded > 0:
            try:
                decoded_text = decode_payload(match).decode("utf-8", errors="replace")
                nested_refs = collect_remaining_refs(decoded_text)
                if nested_refs["attributes"] or nested_refs["css_urls"] or nested_refs["js_strings"]:
                    decoded_text_refs.append({"asset_index": i, "mime": mime, "remaining_refs": nested_refs})
            except Exception:
                warnings.append(f"asset #{i} {mime} could not be decoded as UTF-8 text for nested reference validation")
        if decoded > args.max_asset_mb * 1024 * 1024:
            warnings.append(f"asset #{i} {mime} is large: {fmt(decoded)}")
        if decoded == 0:
            warnings.append(f"asset #{i} {mime} could not be decoded")

    non_base64_data_urls = 0
    for match in DATA_URL_ANY_RE.finditer(html):
        if any(start <= match.start() < end for start, end in base64_spans):
            continue
        non_base64_data_urls += 1

    if html_bytes > args.max_html_mb * 1024 * 1024:
        warnings.append(f"HTML file is large: {fmt(html_bytes)}")

    refs = collect_remaining_refs(html)
    if refs["attributes"] or refs["css_urls"] or refs["js_strings"]:
        warnings.append("remaining non-data local references exist")
    if decoded_text_refs:
        warnings.append("remaining non-data local references exist inside embedded text assets")

    total_decoded = sum(a["decoded_bytes"] for a in assets)
    report = {
        "input": str(args.input_html),
        "html_bytes": html_bytes,
        "html_size": fmt(html_bytes),
        "data_url_count": len(assets),
        "non_base64_data_url_count": non_base64_data_urls,
        "decoded_bytes_total": total_decoded,
        "decoded_size_total": fmt(total_decoded),
        "by_mime": {
            mime: {
                "count": by_mime[mime],
                "decoded_bytes": bytes_by_mime[mime],
                "decoded_size": fmt(bytes_by_mime[mime]),
            }
            for mime in sorted(by_mime)
        },
        "remaining_refs": refs,
        "decoded_text_remaining_refs": decoded_text_refs,
        "warnings": warnings,
        "assets": assets,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"File: {args.input_html}")
        print(f"HTML size: {fmt(html_bytes)}")
        print(f"Base64 Data URLs: {len(assets)}")
        if non_base64_data_urls:
            print(f"Non-base64 Data URLs: {non_base64_data_urls}")
        print(f"Decoded embedded total: {fmt(total_decoded)}")
        if by_mime:
            print("\nBy MIME:")
            for mime in sorted(by_mime):
                print(f"  {mime:<32} {by_mime[mime]:>4}  {fmt(bytes_by_mime[mime])}")
        if refs["attributes"] or refs["css_urls"] or refs["js_strings"]:
            print("\nRemaining local references:")
            for url in refs["attributes"][:30]:
                print(f"  attr: {url}")
            for url in refs["css_urls"][:30]:
                print(f"  css : {url}")
            for url in refs["js_strings"][:30]:
                print(f"  js  : {url}")
        if decoded_text_refs:
            print("\nRemaining local references inside embedded text assets:")
            shown = 0
            for item in decoded_text_refs:
                refs2 = item["remaining_refs"]
                for kind, label in (("attributes", "attr"), ("css_urls", "css"), ("js_strings", "js")):
                    for url in refs2[kind][:10]:
                        print(f"  asset #{item['asset_index']} {item['mime']} {label}: {url}")
                        shown += 1
                        if shown >= 30:
                            break
                    if shown >= 30:
                        break
                if shown >= 30:
                    break
        if warnings:
            print("\nWarnings:")
            for w in warnings:
                print(f"  - {w}")
        else:
            print("\nNo warnings.")

    return 1 if warnings and (args.fail_on_warning or args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())

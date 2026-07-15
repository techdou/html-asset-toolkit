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

# Match inline <style>...</style> and <script>...</script> blocks produced by
# tag-inline mode, so we can scan their content for residual local references.
STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(?P<content>.*?)</style>", re.IGNORECASE | re.DOTALL)
SCRIPT_BLOCK_RE = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(?P<content>.*?)</script>", re.IGNORECASE | re.DOTALL)

# Opening tags and closing-tag searcher for the inline-leak state machine.
SCRIPT_OPEN_RE = re.compile(r"<script\b", re.IGNORECASE)
STYLE_OPEN_RE = re.compile(r"<style\b", re.IGNORECASE)
# Any closing tag start (escaped <\/script is handled by the backslash check).
SCRIPT_CLOSE_SEARCH_RE = re.compile(r"</script", re.IGNORECASE)
STYLE_CLOSE_SEARCH_RE = re.compile(r"</style", re.IGNORECASE)
SRC_ATTR_RE = re.compile(r"\bsrc\s*=", re.IGNORECASE)
# Unescaped closing tag: not preceded by a backslash. Used to scan the leak
# region after a block's real closing tag.
UNESCAPED_SCRIPT_CLOSE_RE = re.compile(r"(?<!\\)</script", re.IGNORECASE)
UNESCAPED_STYLE_CLOSE_RE = re.compile(r"(?<!\\)</style", re.IGNORECASE)


def find_inline_tag_leaks(html: str, open_re: re.Pattern, close_search_re: re.Pattern,
                          unescaped_close_re: re.Pattern, tag_name: str) -> list[str]:
    """Detect unescaped closing tags inside inline <script>/<style> blocks.

    A naive regex like SCRIPT_BLOCK_RE uses non-greedy ``.*?</script>`` and
    truncates content at the first ``</script>``, so it cannot see an unescaped
    closing tag hiding inside the content. This scanner mimics the HTML parser's
    raw-text state: from each inline opening tag it skips escaped ``<\\/tag``
    forms (the parser does not treat them as closing tags) and treats the first
    unescaped ``</tag`` as the real closing tag. It then checks the region
    between that closing tag and the next opening tag — in a well-formed
    document this is just inter-tag text, so an unescaped ``</tag`` there means
    the previous block was truncated early and its content leaked.

    Known limitation: if the leaked content itself contains a ``<tag`` literal
    (e.g. ``var b="<script>"``), the scanner treats it as the next opening tag
    and may miss the leak. This is an adversarial construction that does not
    occur in real React/Vue minified output, where ``</script>`` appears inside
    string literals or hydration data but not as a bare ``<script>`` token.
    """
    errors: list[str] = []
    i = 0
    block_no = 0
    n = len(html)
    while i < n:
        m = open_re.search(html, i)
        if not m:
            break
        tag_start = m.start()
        gt = html.find(">", tag_start)
        if gt < 0:
            break
        # Skip external <script src=...>; only inline blocks are in scope.
        if tag_name == "script" and SRC_ATTR_RE.search(html, tag_start, gt):
            i = gt + 1
            continue
        block_no += 1
        j = gt + 1
        real_close = -1
        while j < n:
            cm = close_search_re.search(html, j)
            if not cm:
                break
            pos = cm.start()
            # Escaped form <\/tag: backslash before the slash. The HTML parser
            # does NOT see this as a closing tag, so skip and keep scanning.
            if pos > 0 and html[pos - 1] == "\\":
                j = cm.end()
                continue
            real_close = pos
            break
        if real_close < 0:
            # Unterminated block; leave it to other checks.
            break
        # Move past the closing tag's '>' so the leak scan excludes the tag itself.
        close_gt = html.find(">", real_close)
        after_close = close_gt + 1 if close_gt >= 0 else real_close + len("</") + len(tag_name)
        # Region between this block's closing tag and the next opening tag. In a
        # well-formed document this is inter-tag whitespace/text. An unescaped
        # </tag> here means the previous block was truncated early.
        next_open = open_re.search(html, after_close)
        region_end = next_open.start() if next_open else n
        region = html[after_close:region_end]
        if unescaped_close_re.search(region):
            errors.append(
                f"inline <{tag_name}> block #{block_no} contains an unescaped </{tag_name}>; "
                "the HTML parser closes the tag early and the rest of the content leaks as visible text"
            )
        i = region_end if next_open else n
    return errors

# Detect Three.js Draco decoder references. These runtimes fetch
# draco_decoder.js / draco_wasm_wrapper.js / draco_decoder.wasm from a CDN at
# load time, so an offline single-file artifact cannot render the model without
# extra steps. Warn (not error) because the page still works online.
DRACO_REF_RE = re.compile(r"draco_decoder|draco_wasm_wrapper|DRACOLoader", re.IGNORECASE)
DRACO_VERSION_RE = re.compile(r"gstatic\.com/draco/versioned/decoders/(\d+\.\d+\.\d+)", re.IGNORECASE)


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
    errors: list[str] = []
    draco_warnings: list[str] = []
    decoded_text_refs: list[dict] = []
    # Collect every JS text blob we encounter (data-url JS + inline <script>)
    # so the Draco check covers both embedding strategies with one pass.
    js_text_blobs: list[str] = []

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
                if mime in {"text/javascript", "application/javascript", "application/x-javascript"}:
                    js_text_blobs.append(decoded_text)
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

    # Scan inline <style>/<script> blocks (tag-inline mode output) for residual
    # local references that would break at runtime.
    tag_inline_refs: list[dict] = []
    for i, m in enumerate(STYLE_BLOCK_RE.finditer(html), 1):
        block_refs = collect_remaining_refs(m.group("content"))
        if block_refs["attributes"] or block_refs["css_urls"] or block_refs["js_strings"]:
            tag_inline_refs.append({"block": i, "type": "style", "remaining_refs": block_refs})
    for i, m in enumerate(SCRIPT_BLOCK_RE.finditer(html), 1):
        content = m.group("content")
        js_text_blobs.append(content)
        block_refs = collect_remaining_refs(content)
        if block_refs["attributes"] or block_refs["css_urls"] or block_refs["js_strings"]:
            tag_inline_refs.append({"block": i, "type": "script", "remaining_refs": block_refs})
    if tag_inline_refs:
        warnings.append("remaining non-data local references exist inside inline <style>/<script> blocks")

    # Unescaped </script>/<style> inside an inline tag breaks the page: the HTML
    # parser closes the tag early and the rest of the JS/CSS leaks as visible
    # text. This is a hard error. The state-machine scanner skips escaped
    # <\/tag forms so it catches leaks even when the content contains paired
    # <tag>...</tag> literals (common in React/Vue minified runtimes).
    errors.extend(find_inline_tag_leaks(
        html, SCRIPT_OPEN_RE, SCRIPT_CLOSE_SEARCH_RE, UNESCAPED_SCRIPT_CLOSE_RE, "script"))
    errors.extend(find_inline_tag_leaks(
        html, STYLE_OPEN_RE, STYLE_CLOSE_SEARCH_RE, UNESCAPED_STYLE_CLOSE_RE, "style"))

    # Three.js Draco decoder check. GLB models with KHR_draco_mesh_compression
    # fetch decoder files from a CDN at runtime; an offline artifact cannot load
    # them. This is a recoverable warning (works online), never an error.
    draco_hit = False
    draco_version = None
    for blob in js_text_blobs:
        if DRACO_REF_RE.search(blob):
            draco_hit = True
            vm = DRACO_VERSION_RE.search(blob)
            if vm and not draco_version:
                draco_version = vm.group(1)
    if draco_hit:
        ver = draco_version or "1.5.5"
        draco_warnings.append(
            "Three.js Draco decoder files referenced but not embedded.\n"
            "  The 3D model requires an internet connection to load decoders from Google CDN.\n"
            "  To embed them for offline use, download from:\n"
            f"    https://www.gstatic.com/draco/versioned/decoders/{ver}/\n"
            "  Place the files (draco_decoder.js, draco_wasm_wrapper.js, draco_decoder.wasm)\n"
            "  in the build output directory before packaging, and point DRACOLoader at them."
        )

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
        "tag_inline_refs": tag_inline_refs,
        "warnings": warnings,
        "errors": errors,
        "draco_warnings": draco_warnings,
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
        if tag_inline_refs:
            print("\nRemaining local references inside inline <style>/<script> blocks:")
            shown = 0
            for item in tag_inline_refs:
                refs2 = item["remaining_refs"]
                for kind, label in (("attributes", "attr"), ("css_urls", "css"), ("js_strings", "js")):
                    for url in refs2[kind][:10]:
                        print(f"  {item['type']} #{item['block']} {label}: {url}")
                        shown += 1
                        if shown >= 30:
                            break
                    if shown >= 30:
                        break
                if shown >= 30:
                    break
        if errors:
            print("\nErrors:")
            for e in errors:
                print(f"  - {e}")
        if draco_warnings:
            print("\nDraco decoder notice:")
            for w in draco_warnings:
                print(w)
        if warnings:
            print("\nWarnings:")
            for w in warnings:
                print(f"  - {w}")
        if not errors and not warnings and not draco_warnings:
            print("\nNo errors or warnings.")

    # Errors always fail. Warnings only fail under --fail-on-warning / --strict.
    return 1 if errors or (warnings and (args.fail_on_warning or args.strict)) else 0


if __name__ == "__main__":
    raise SystemExit(main())

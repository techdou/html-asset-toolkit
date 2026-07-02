#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inline local assets referenced by an HTML file as Base64/Data URLs.

Designed for course demos, offline single-file HTML handoff, and static React/Vue build packaging.

Default output:
- Source project HTML such as ./index.html -> ./dist/index.single.html
- Frontend build output such as ./dist/index.html -> ./dist/index.single.html
- CRA build output such as ./build/index.html -> ./build/index.single.html

Root-relative URLs such as /assets/index.js or /static/css/main.css are resolved
against the input HTML directory by default, which matches Vite, Vue CLI, and
Create React App production build folders.

Core dependency: Python standard library.
Optional dependency: Pillow for raster image WebP conversion.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import quote, unquote, urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SUPPORTED_EXT_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".bmp": "image/bmp",
    ".avif": "image/avif",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".stl": "model/stl",
    ".obj": "model/obj",
    ".mtl": "text/plain",
    ".usdz": "model/vnd.usdz+zip",
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".wasm": "application/wasm",
    ".css": "text/css",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".xml": "application/xml",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
}

ASSET_EXT_RE = "|".join(re.escape(k.lstrip(".")) for k in sorted(SUPPORTED_EXT_MIME, key=len, reverse=True))

ATTR_RE = re.compile(
    r"(?P<prefix>\b(?:src|href|poster|data)\s*=\s*)(?P<quote>[\"'])(?P<url>(?!data:)[^\"']+?\.(?:" + ASSET_EXT_RE + r")(?:(?:\?[^\"']*)|(?:#[^\"']*))?)(?P=quote)",
    re.IGNORECASE,
)

SRCSET_RE = re.compile(
    r"(?P<prefix>\bsrcset\s*=\s*)(?P<quote>[\"'])(?P<value>(?!data:)[^\"']+)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)

CSS_URL_RE = re.compile(
    r"url\(\s*(?P<quote>[\"']?)(?P<url>(?!data:)[^)\"']+?\.(?:" + ASSET_EXT_RE + r")(?:(?:\?[^)\"']*)|(?:#[^)\"']*))?)(?P=quote)\s*\)",
    re.IGNORECASE,
)

CSS_IMPORT_RE = re.compile(
    r"@import\s+(?:url\(\s*)?(?P<quote>[\"'])(?P<url>(?!data:)[^\"']+?\.css(?:(?:\?[^\"']*)|(?:#[^\"']*))?)(?P=quote)\s*\)?",
    re.IGNORECASE,
)

JS_STRING_RE = re.compile(
    # Match JavaScript string literals whose entire content is a local asset URL.
    # Include static template literals because Vite/esbuild may rewrite
    # "/assets/foo.png" or '/assets/foo.png' into `/assets/foo.png`.
    # Deliberately exclude whitespace and angle brackets so HTML snippets such as
    # `<img src="/assets/foo.png">` are not treated as one path literal.
    r"(?P<quote>[\"'`])"
    r"(?P<url>(?!data:)(?!https?://)(?!//)[^\"'`\s<>]+?\.(?:" + ASSET_EXT_RE + r")"
    r"(?:(?:\?[^\"'`\s<>]*)|(?:#[^\"'`\s<>]*))?)"
    r"(?P=quote)",
    re.IGNORECASE,
)

EXTERNAL_PREFIXES = ("data:", "http://", "https://", "//", "mailto:", "tel:", "#", "javascript:")
BUILD_OUTPUT_DIR_NAMES = {"dist", "build", "out"}


def escape_js_string_literal(value: str, quote: str) -> str:
    """Escape a replacement value for a JavaScript string/template literal.

    Data URLs are usually Base64 and quote-safe, but SVG UTF-8 data URLs,
    unusual filenames, or future MIME encoders may contain characters that break
    a JS string. Preserve the original quote style while escaping the delimiter,
    backslashes, JavaScript line terminators, and template-expression markers.
    """
    escaped = (
        value.replace("\\", "\\\\")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    if quote == "`":
        escaped = escaped.replace("`", "\\`").replace("${", "\\${")
    elif quote == '"':
        escaped = escaped.replace('"', '\\"')
    elif quote == "'":
        escaped = escaped.replace("'", "\\'")
    return escaped



@dataclass
class InlineResult:
    source: str
    resolved_path: str | None
    mime: str | None
    original_bytes: int | None
    embedded_chars: int | None
    context: str
    action: str
    note: str = ""


def parse_ext_list(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    values: set[str] = set()
    for item in raw.split(","):
        item = item.strip().lower()
        if item:
            values.add(item if item.startswith(".") else f".{item}")
    return values


def is_external_or_special(url: str) -> bool:
    value = url.strip()
    if not value:
        return True
    return value.lower().startswith(EXTERNAL_PREFIXES) or "${" in value or "{{" in value


def strip_query_fragment(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme != "file":
        return url
    return unquote(parsed.path)


def resolve_asset(url: str, base_dir: Path, assets_root: Path | None, root_dir: Path | None) -> Path | None:
    """Resolve an HTML/CSS/JS asset URL to a local file.

    Root-relative browser URLs such as `/assets/app.js` are common in Vite,
    Vue CLI, and Create React App production builds. They are not filesystem
    absolute paths for this tool; by default they are resolved under `root_dir`,
    which is the input HTML directory unless overridden with `--root-dir`.
    """
    if is_external_or_special(url):
        return None
    clean = strip_query_fragment(url).strip()
    if not clean:
        return None

    root_relative = clean.startswith("/") and not clean.startswith("//")
    roots: list[Path] = []

    if root_relative:
        # Browser-root-relative path, e.g. /assets/index.js. Resolve it against
        # the static site/build root, not against the host filesystem root.
        candidate = Path(clean.lstrip("/"))
        if root_dir:
            roots.append(root_dir)
        roots.append(base_dir)
        if assets_root:
            roots.append(assets_root)
    else:
        candidate = Path(clean)
        if candidate.is_absolute():
            roots.append(Path("/"))
        else:
            roots.append(base_dir)
            if root_dir and root_dir != base_dir:
                roots.append(root_dir)
            if assets_root:
                roots.append(assets_root)

    seen: set[str] = set()
    for root in roots:
        path = candidate if candidate.is_absolute() and not root_relative else root / candidate
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists() and path.is_file():
            return path.resolve()
    return None


def guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in SUPPORTED_EXT_MIME:
        return SUPPORTED_EXT_MIME[ext]
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def encode_data_url(payload: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"


def maybe_convert_image(path: Path, raw: bytes, args: argparse.Namespace) -> tuple[bytes, str, str]:
    ext = path.suffix.lower()
    if args.image_mode != "webp" or ext not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        return raw, guess_mime(path), "raw"
    try:
        from PIL import Image, ImageOps  # type: ignore
    except Exception:
        return raw, guess_mime(path), "raw: Pillow not installed"
    try:
        import io

        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
            img = img.convert("RGBA" if has_alpha else "RGB")
            width, height = img.size
            scale = min(args.max_width / width, args.max_height / height, 1.0)
            if scale < 1.0:
                img = img.resize((max(1, int(width * scale)), max(1, int(height * scale))))
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=args.webp_quality, method=6)
            converted = buf.getvalue()
            if len(converted) < len(raw):
                return converted, "image/webp", f"webp q={args.webp_quality}"
            return raw, guess_mime(path), "raw: webp was larger"
    except Exception as exc:
        return raw, guess_mime(path), f"raw: image conversion failed: {exc}"


def make_file_data_url(
    path: Path,
    args: argparse.Namespace,
    inline_url: Callable[[str, str, Path], str] | None = None,
) -> tuple[str, int, str, str]:
    raw = path.read_bytes()
    ext = path.suffix.lower()

    if ext == ".css" and args.process_external_css and inline_url:
        text = raw.decode("utf-8", errors="replace")

        def repl_css(match: re.Match) -> str:
            quote = match.group("quote") or ""
            new = inline_url(match.group("url"), "css_file_url", path.parent)
            return f"url({quote}{new}{quote})"

        def repl_import(match: re.Match) -> str:
            new = inline_url(match.group("url"), "css_file_import", path.parent)
            return f"@import {match.group('quote')}{new}{match.group('quote')}"

        processed = CSS_IMPORT_RE.sub(repl_import, text)
        processed = CSS_URL_RE.sub(repl_css, processed)
        payload = processed.encode("utf-8")
        return encode_data_url(payload, "text/css"), len(raw), "text/css", "css data-url; nested @import and url() processed"

    if ext in {".js", ".mjs"} and args.process_external_js and inline_url:
        text = raw.decode("utf-8", errors="replace")

        def repl_js(match: re.Match) -> str:
            quote = match.group("quote")
            new = inline_url(match.group("url"), "js_file_string", path.parent)
            return f"{quote}{escape_js_string_literal(new, quote)}{quote}"

        processed = JS_STRING_RE.sub(repl_js, text)
        payload = processed.encode("utf-8")
        return encode_data_url(payload, guess_mime(path)), len(raw), guess_mime(path), "js data-url; local asset strings processed"

    if ext == ".svg" and args.svg_mode == "utf8":
        text = raw.decode("utf-8", errors="replace")
        encoded = quote(text, safe="/:;=,#%[]{}()!$&'*+-.?@_~")
        return f"data:image/svg+xml,{encoded}", len(raw), "image/svg+xml", "svg utf8"

    payload, mime, note = maybe_convert_image(path, raw, args)
    return encode_data_url(payload, mime), len(raw), mime, note


def should_include(path: Path, include_ext: set[str] | None, exclude_ext: set[str] | None) -> bool:
    ext = path.suffix.lower()
    if include_ext is not None and ext not in include_ext:
        return False
    if exclude_ext is not None and ext in exclude_ext:
        return False
    return True


def make_inliner(args: argparse.Namespace, html_dir: Path, manifest: list[InlineResult]):
    include_ext = parse_ext_list(args.include_ext)
    exclude_ext = parse_ext_list(args.exclude_ext)
    max_asset = int(args.max_asset_mb * 1024 * 1024) if args.max_asset_mb else 0
    max_total = int(args.max_total_mb * 1024 * 1024) if args.max_total_mb else 0
    cache: dict[str, tuple[str, int, str, str]] = {}
    total = {"bytes": 0, "errors": 0}
    active: set[str] = set()

    def inline_url(url: str, context: str, base_dir: Path = html_dir) -> str:
        path = resolve_asset(url, base_dir, args.assets_root, args.root_dir)
        if path is None:
            manifest.append(InlineResult(url, None, None, None, None, context, "missing_or_external"))
            total["errors"] += 1 if args.strict and not is_external_or_special(url) else 0
            return url
        if not should_include(path, include_ext, exclude_ext):
            manifest.append(InlineResult(url, str(path), guess_mime(path), path.stat().st_size, None, context, "skipped", "extension filter"))
            return url

        original_size = path.stat().st_size
        if max_asset and original_size > max_asset:
            manifest.append(InlineResult(url, str(path), guess_mime(path), original_size, None, context, "skipped", f"over max asset {args.max_asset_mb} MB"))
            total["errors"] += 1 if args.strict else 0
            return url
        if max_total and total["bytes"] + original_size > max_total:
            manifest.append(InlineResult(url, str(path), guess_mime(path), original_size, None, context, "skipped", f"over max total {args.max_total_mb} MB"))
            total["errors"] += 1 if args.strict else 0
            return url

        key = str(path)
        if key in cache:
            data_url, original_bytes, mime, note = cache[key]
        else:
            if key in active:
                manifest.append(InlineResult(url, str(path), guess_mime(path), original_size, None, context, "skipped", "recursive reference"))
                return url
            try:
                active.add(key)
                data_url, original_bytes, mime, note = make_file_data_url(path, args, inline_url)
                cache[key] = (data_url, original_bytes, mime, note)
            except Exception as exc:
                manifest.append(InlineResult(url, str(path), None, original_size, None, context, "error", str(exc)))
                total["errors"] += 1
                return url
            finally:
                active.discard(key)

        total["bytes"] += original_size
        manifest.append(InlineResult(url, str(path), mime, original_bytes, len(data_url), context, "inlined", note))
        return data_url

    inline_url.total = total  # type: ignore[attr-defined]
    return inline_url


def replace_srcset(value: str, inline_url) -> str:
    parts = []
    for item in value.split(","):
        token = item.strip()
        if not token:
            continue
        bits = token.split()
        original_url = bits[0]
        new_url = inline_url(original_url, "srcset")
        parts.append(" ".join([new_url] + bits[1:]))
    return ", ".join(parts)


def inline_html(html: str, args: argparse.Namespace, html_dir: Path) -> tuple[str, list[InlineResult], int]:
    manifest: list[InlineResult] = []
    inline_url = make_inliner(args, html_dir, manifest)

    def repl_srcset(match: re.Match) -> str:
        return f"{match.group('prefix')}{match.group('quote')}{replace_srcset(match.group('value'), inline_url)}{match.group('quote')}"

    def repl_attr(match: re.Match) -> str:
        url = match.group("url")
        return f"{match.group('prefix')}{match.group('quote')}{inline_url(url, 'attribute')}{match.group('quote')}"

    def repl_css(match: re.Match) -> str:
        quote = match.group("quote") or ""
        new = inline_url(match.group("url"), "css_url")
        return f"url({quote}{new}{quote})"

    def repl_import(match: re.Match) -> str:
        new = inline_url(match.group("url"), "css_import")
        return f"@import {match.group('quote')}{new}{match.group('quote')}"

    def repl_js(match: re.Match) -> str:
        quote = match.group("quote")
        new = inline_url(match.group("url"), "js_string")
        return f"{quote}{escape_js_string_literal(new, quote)}{quote}"

    html = SRCSET_RE.sub(repl_srcset, html)
    html = ATTR_RE.sub(repl_attr, html)
    html = CSS_IMPORT_RE.sub(repl_import, html)
    html = CSS_URL_RE.sub(repl_css, html)
    html = JS_STRING_RE.sub(repl_js, html)
    return html, manifest, inline_url.total["errors"]  # type: ignore[attr-defined]


def is_frontend_build_entry(input_html: Path) -> bool:
    return input_html.name.lower() == "index.html" and input_html.parent.name.lower() in BUILD_OUTPUT_DIR_NAMES


def default_out(input_html: Path) -> Path:
    # Normal source HTML convention: <input dir>/dist/<source-name>.single.html.
    # Example: course/index.html -> course/dist/index.single.html.
    # Frontend build convention: if input is dist/index.html or build/index.html,
    # write beside it to avoid dist/dist/index.single.html.
    # Example: app/dist/index.html -> app/dist/index.single.html.
    if is_frontend_build_entry(input_html):
        return input_html.parent / f"{input_html.stem}.single{input_html.suffix}"
    return input_html.parent / "dist" / f"{input_html.stem}.single{input_html.suffix}"


def project_relative(path: Path, input_html: Path) -> Path:
    """Resolve user-facing relative output paths beside the input HTML.

    This keeps `dist/` inside the course/demo project even when the tool script
    is executed from another directory with an absolute input HTML path.
    """
    return path if path.is_absolute() else input_html.parent / path


def format_bytes(n: int | None) -> str:
    if n is None:
        return "-"
    value = float(n)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{n} B"


def resolve_output(args: argparse.Namespace) -> Path:
    if args.out:
        return project_relative(args.out, args.input_html)
    if args.out_dir or args.single_name:
        out_dir = project_relative(args.out_dir or Path("dist"), args.input_html)
        single_name = args.single_name or f"{args.input_html.stem}.single{args.input_html.suffix}"
        return out_dir / single_name
    return default_out(args.input_html)




def remove_integrity_attrs(html: str) -> str:
    # SRI hashes are invalid after CSS/JS URLs are replaced with Data URLs.
    # Remove them by default for static build packaging.
    return re.sub(r"\s+integrity=(['\"]).*?\1", "", html, flags=re.IGNORECASE | re.DOTALL)


def detect_build_context(input_html: Path) -> str:
    parent = input_html.parent.name.lower()
    if input_html.name.lower() == "index.html" and parent == "dist":
        return "dist static build output (Vite / Vue CLI / common React build)"
    if input_html.name.lower() == "index.html" and parent == "build":
        return "build static output (Create React App)"
    if input_html.name.lower() == "index.html" and parent == "out":
        return "out static export output"
    return "source html or generic html"

def main() -> int:
    parser = argparse.ArgumentParser(description="Inline local HTML assets as Base64 Data URLs.")
    parser.add_argument("input_html", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="Output HTML path. Relative paths are resolved beside the input HTML. Example: dist/index.single.html")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory when --out is not used. Relative paths are resolved beside the input HTML. Example: dist")
    parser.add_argument("--single-name", default=None, help="Output filename when --out is not used. Example: index.single.html")
    parser.add_argument("--assets-root", type=Path, default=None, help="Additional asset lookup root. Relative paths resolve beside the input HTML.")
    parser.add_argument("--root-dir", type=Path, default=None, help="Static site root for browser-root-relative URLs like /assets/app.js. Relative paths resolve beside the input HTML. Defaults to the input HTML directory.")
    parser.add_argument("--preset", choices=["generic", "react-vue-build", "vite", "create-react-app", "vue-cli"], default="generic", help="Documentation/manifest preset for static frontend build packaging.")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--include-ext", default=None)
    parser.add_argument("--exclude-ext", default=None)
    parser.add_argument("--max-asset-mb", type=float, default=0)
    parser.add_argument("--max-total-mb", type=float, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--image-mode", choices=["raw", "webp"], default="raw")
    parser.add_argument("--max-width", type=int, default=1800)
    parser.add_argument("--max-height", type=int, default=1800)
    parser.add_argument("--webp-quality", type=int, default=82)
    parser.add_argument("--svg-mode", choices=["base64", "utf8"], default="base64")
    parser.add_argument("--process-external-css", action=argparse.BooleanOptionalAction, default=True, help="Inline url(...) references inside external CSS before embedding CSS.")
    parser.add_argument("--process-external-js", action=argparse.BooleanOptionalAction, default=True, help="Inline local asset strings inside external JS before embedding JS.")
    parser.add_argument("--remove-integrity", action=argparse.BooleanOptionalAction, default=True, help="Remove integrity= attributes because SRI hashes no longer match after inlining CSS/JS.")
    args = parser.parse_args()

    if not args.input_html.exists():
        print(f"ERROR: input HTML not found: {args.input_html}", file=sys.stderr)
        return 1
    args.input_html = args.input_html.resolve()
    if args.assets_root:
        args.assets_root = project_relative(args.assets_root, args.input_html).resolve()
    args.root_dir = project_relative(args.root_dir, args.input_html).resolve() if args.root_dir else args.input_html.parent.resolve()

    out_path = resolve_output(args).resolve()
    manifest_path = project_relative(args.manifest, args.input_html).resolve() if args.manifest else out_path.with_suffix(out_path.suffix + ".manifest.json")

    html = args.input_html.read_text(encoding="utf-8")
    result_html, entries, errors = inline_html(html, args, args.input_html.parent.resolve())
    if args.remove_integrity:
        result_html = remove_integrity_attrs(result_html)

    inlined = [e for e in entries if e.action == "inlined"]
    skipped = [e for e in entries if e.action == "skipped"]
    missing = [e for e in entries if e.action == "missing_or_external"]
    total_decoded = sum(e.original_bytes or 0 for e in inlined)

    report = {
        "input": str(args.input_html),
        "output": str(out_path),
        "dry_run": args.dry_run,
        "default_delivery_pattern": "source HTML: dist/<source-name>.single.html; frontend build dist/index.html or build/index.html: <build-dir>/index.single.html",
        "common_index_delivery_path": "dist/index.single.html",
        "source_name": args.input_html.name,
        "preset": args.preset,
        "build_context": detect_build_context(args.input_html),
        "root_dir": str(args.root_dir),
        "frontend_build_entry": is_frontend_build_entry(args.input_html),
        "output_relative_to_input_dir": str(out_path.relative_to(args.input_html.parent)) if out_path.is_relative_to(args.input_html.parent) else str(out_path),
        "summary": {
            "references_seen": len(entries),
            "inlined": len(inlined),
            "skipped": len(skipped),
            "missing_or_external": len(missing),
            "decoded_bytes_inlined": total_decoded,
            "decoded_size_inlined": format_bytes(total_decoded),
        },
        "entries": [asdict(e) for e in entries],
    }

    if not args.dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result_html, encoding="utf-8")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Input:  {args.input_html}")
    print(f"Output: {out_path}{' (dry-run)' if args.dry_run else ''}")
    print(f"Root:   {args.root_dir}")
    print(f"Mode:   {detect_build_context(args.input_html)}")
    print(f"Inlined: {len(inlined)} asset reference(s), decoded total {format_bytes(total_decoded)}")
    if skipped:
        print(f"Skipped: {len(skipped)}")
    if missing:
        local_missing = [e for e in missing if not is_external_or_special(e.source)]
        if local_missing:
            print(f"Missing local references: {len(local_missing)}")
    if not args.dry_run:
        print(f"Manifest: {manifest_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

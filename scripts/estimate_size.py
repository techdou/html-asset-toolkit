#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estimate the final single-file HTML size without writing any output.

Scans an HTML file (and recursively, its referenced CSS/JS) for local asset
references, sums their original sizes, and applies the Base64 expansion factor
(~1.37x) to project the embedded size. Supports the same path-resolution
options as inline_assets.py so the estimate matches what a real run would
produce.

No files are written. Designed for agents and users who want to decide whether
single-file packaging is practical before committing to a full run.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Reuse the inliner's regexes and resolver so the estimate never drifts from
# actual behavior.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Import from the sibling inline_assets module.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import inline_assets as ia  # noqa: E402


BASE64_EXPANSION = 4.0 / 3.0  # Base64 encodes 3 bytes into 4 characters.


@dataclass
class AssetEstimate:
    source: str
    resolved_path: str | None
    mime: str | None
    original_bytes: int | None
    estimated_bytes: int | None
    context: str
    status: str  # "found", "missing", "skipped_ext", "skipped_size"
    note: str = ""


@dataclass
class EstimateReport:
    input_html: str
    estimated_total_original_bytes: int = 0
    estimated_total_embedded_bytes: int = 0
    html_baseline_bytes: int = 0
    estimated_final_html_bytes: int = 0
    by_mime: dict = field(default_factory=dict)
    assets: list = field(default_factory=list)
    over_limit: list = field(default_factory=list)
    missing: list = field(default_factory=list)


def format_bytes(n: int | float | None) -> str:
    if n is None:
        return "-"
    value = float(n)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{n} B"


def collect_estimates(
    html: str,
    args: argparse.Namespace,
    html_dir: Path,
) -> tuple[list[AssetEstimate], int]:
    """Walk every asset reference, resolve it, and project its embedded size.

    Returns the list of per-asset estimates and a running count of references
    that could not be resolved.
    """
    include_ext = ia.parse_ext_list(args.include_ext)
    exclude_ext = ia.parse_ext_list(args.exclude_ext)
    max_asset = int(args.max_asset_mb * 1024 * 1024) if args.max_asset_mb else 0
    seen_paths: set[str] = set()
    estimates: list[AssetEstimate] = []
    missing_count = 0

    def visit(url: str, context: str, base_dir: Path) -> str:
        nonlocal missing_count
        path = ia.resolve_asset(url, base_dir, args.assets_root, args.root_dir)
        if path is None:
            status = "missing" if not ia.is_external_or_special(url) else "external"
            if status == "missing":
                missing_count += 1
            estimates.append(AssetEstimate(url, None, None, None, None, context, status))
            return url

        if not ia.should_include(path, include_ext, exclude_ext):
            estimates.append(AssetEstimate(url, str(path), ia.guess_mime(path), path.stat().st_size, None, context, "skipped_ext"))
            return url

        original = path.stat().st_size
        key = str(path)
        if key in seen_paths:
            return url
        seen_paths.add(key)

        mime = ia.guess_mime(path)
        if max_asset and original > max_asset:
            estimates.append(AssetEstimate(url, str(path), mime, original, None, context, "skipped_size", f"over {args.max_asset_mb} MB"))
            return url

        # Estimate embedded bytes. For CSS/JS we would need to read and recurse
        # to be perfectly accurate, but the dominant cost is almost always the
        # binary assets. We use the raw size × Base64 expansion for a tight,
        # dependency-free estimate.
        embedded = int(original * BASE64_EXPANSION)
        estimates.append(AssetEstimate(url, str(path), mime, original, embedded, context, "found"))
        return url

    # Drive the same regexes the inliner uses, so every reference type is covered.
    def repl_srcset(match: argparse.Namespace) -> str:
        value = match.group("value")
        parts = []
        for item in value.split(","):
            token = item.strip()
            if not token:
                continue
            bits = token.split()
            visit(bits[0], "srcset", html_dir)
            parts.append(token)
        return match.group(0)

    def repl_attr(match: argparse.Namespace) -> str:
        visit(match.group("url"), "attribute", html_dir)
        return match.group(0)

    def repl_css(match: argparse.Namespace) -> str:
        visit(match.group("url"), "css_url", html_dir)
        return match.group(0)

    def repl_import(match: argparse.Namespace) -> str:
        visit(match.group("url"), "css_import", html_dir)
        return match.group(0)

    def repl_js(match: argparse.Namespace) -> str:
        visit(match.group("url"), "js_string", html_dir)
        return match.group(0)

    html = ia.SRCSET_RE.sub(repl_srcset, html)
    html = ia.ATTR_RE.sub(repl_attr, html)
    html = ia.CSS_IMPORT_RE.sub(repl_import, html)
    html = ia.CSS_URL_RE.sub(repl_css, html)
    html = ia.JS_STRING_RE.sub(repl_js, html)
    return estimates, missing_count


def build_report(
    input_html: Path,
    html: str,
    estimates: list[AssetEstimate],
    missing_count: int,
    args: argparse.Namespace,
) -> EstimateReport:
    report = EstimateReport(input_html=str(input_html))
    report.html_baseline_bytes = len(html.encode("utf-8"))

    by_mime: dict[str, dict] = {}
    for est in estimates:
        if est.status != "found" or est.original_bytes is None:
            if est.status == "missing":
                report.missing.append(est.source)
            elif est.status == "skipped_size":
                report.over_limit.append({"source": est.source, "bytes": est.original_bytes})
            continue
        report.estimated_total_original_bytes += est.original_bytes
        report.estimated_total_embedded_bytes += est.estimated_bytes or 0
        mime = est.mime or "application/octet-stream"
        bucket = by_mime.setdefault(mime, {"count": 0, "original_bytes": 0, "estimated_bytes": 0})
        bucket["count"] += 1
        bucket["original_bytes"] += est.original_bytes
        bucket["estimated_bytes"] += est.estimated_bytes or 0

    for mime, bucket in by_mime.items():
        bucket["original_size"] = format_bytes(bucket["original_bytes"])
        bucket["estimated_size"] = format_bytes(bucket["estimated_bytes"])
        report.by_mime[mime] = bucket

    report.estimated_final_html_bytes = report.html_baseline_bytes + report.estimated_total_embedded_bytes
    report.assets = [asdict(e) for e in estimates]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate the final single-file HTML size without writing any output."
    )
    parser.add_argument("input_html", type=Path)
    parser.add_argument("--assets-root", type=Path, default=None)
    parser.add_argument("--root-dir", type=Path, default=None)
    parser.add_argument("--include-ext", default=None)
    parser.add_argument("--exclude-ext", default=None)
    parser.add_argument("--max-asset-mb", type=float, default=0)
    parser.add_argument("--max-total-mb", type=float, default=0)
    parser.add_argument("--json", action="store_true", help="Output a machine-readable JSON report.")
    args = parser.parse_args()

    if not args.input_html.exists():
        print(f"ERROR: input HTML not found: {args.input_html}", file=sys.stderr)
        return 1

    args.input_html = args.input_html.resolve()
    if args.assets_root:
        args.assets_root = ia.project_relative(args.assets_root, args.input_html).resolve()
    args.root_dir = (
        ia.project_relative(args.root_dir, args.input_html).resolve()
        if args.root_dir
        else args.input_html.parent.resolve()
    )

    html = args.input_html.read_text(encoding="utf-8")
    estimates, missing_count = collect_estimates(html, args, args.input_html.parent.resolve())
    report = build_report(args.input_html, html, estimates, missing_count, args)

    if args.json:
        print(json.dumps({k: v for k, v in asdict(report).items()}, ensure_ascii=False, indent=2))
    else:
        print(f"Input:      {args.input_html}")
        print(f"HTML base:  {format_bytes(report.html_baseline_bytes)}")
        print(f"Assets:     {len([e for e in estimates if e.status == 'found'])} found, "
              f"{missing_count} missing, "
              f"{len([e for e in estimates if e.status == 'skipped_ext'])} skipped (ext), "
              f"{len([e for e in estimates if e.status == 'skipped_size'])} over limit")
        print(f"Original:   {format_bytes(report.estimated_total_original_bytes)}")
        print(f"Embedded:   {format_bytes(report.estimated_total_embedded_bytes)} (Base64 ×{BASE64_EXPANSION:.2f})")
        print(f"Final HTML: ~{format_bytes(report.estimated_final_html_bytes)}")
        if report.by_mime:
            print("\nBy MIME:")
            for mime in sorted(report.by_mime):
                b = report.by_mime[mime]
                print(f"  {mime:<32} {b['count']:>4}  {b['original_size']:>10} -> {b['estimated_size']:>10}")
        if report.over_limit:
            print(f"\nOver per-asset limit ({args.max_asset_mb} MB):")
            for item in report.over_limit:
                print(f"  {item['source']}  ({format_bytes(item['bytes'])})")
        if report.missing:
            print(f"\nMissing local references: {len(report.missing)}")
            for src in report.missing[:20]:
                print(f"  {src}")
        if args.max_total_mb and report.estimated_total_embedded_bytes > args.max_total_mb * 1024 * 1024:
            print(f"\n⚠ Estimated embedded total {format_bytes(report.estimated_total_embedded_bytes)} "
                  f"exceeds --max-total-mb {args.max_total_mb} MB")
        size = report.estimated_final_html_bytes
        if size > 100 * 1024 * 1024:
            print("\n⚠ Estimated final HTML exceeds 100 MB — single-file packaging may be impractical.")
        elif size > 50 * 1024 * 1024:
            print("\n⚠ Estimated final HTML exceeds 50 MB — heavy artifact, confirm with user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

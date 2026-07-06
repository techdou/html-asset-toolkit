#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rename extracted assets using manifest context.

v4.0.0 changes:
  - Default separator is now "-" (was "_"). Pass --separator _ to restore.
  - pick_name "auto" mode now also mines context.near_text_before for the
    nearest "key:value" label (e.g. name:"七鳃鳗") before falling back to
    mime_group. Use --no-near-text to disable.
  - New --update-html <path> rewrites references in an HTML file in lockstep
    with the file renames, so links do not break.
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

ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# runs of whitespace / underscore / hyphen -> compressed to a single separator
SEPARATOR_RUN = re.compile(r"[\s_\-]+")

# Extracts a label from JSON-ish `key:"value"` / HTML-ish `key="value"`.
# Used to mine near_text_before for the closest preceding name/alt/title.
# Supports double or single quotes; value cannot contain the delimiting quote.
LABEL_RE = re.compile(r'(?:name|alt|title|id)\s*[:=]\s*(["\'])([^"\']+)\1', re.IGNORECASE)

# Matches an HTML attribute value: `attr="..."` or `attr='...'`. Used by
# --update-html so reference rewriting stays scoped to attribute values and
# does not touch the same filename appearing in body text, comments, or
# unrelated JS string literals.
ATTR_VALUE_RE = re.compile(r'(\w+\s*=\s*)(["\'])([^"\']*)\2')


def replace_ref_in_html(html_text: str, old_name: str, new_name: str) -> str:
    """Rewrite old_name -> new_name, but only inside HTML attribute values.

    A bare str.replace would also rewrite the filename when it appears in body
    text, comments, or unrelated JS/CSS strings. Scoping to `attr="..."` keeps
    the rewrite surgical: it covers src/href/data/poster/etc. while leaving
    prose and code untouched.
    """
    def repl(match: re.Match[str]) -> str:
        prefix, quote, content = match.group(1), match.group(2), match.group(3)
        if old_name not in content:
            return match.group(0)
        return f"{prefix}{quote}{content.replace(old_name, new_name)}{quote}"

    return ATTR_VALUE_RE.sub(repl, html_text)


def sanitize(name: str, max_len: int, separator: str = "-") -> str:
    name = ILLEGAL_CHARS.sub("", name)
    name = SEPARATOR_RUN.sub(separator, name)
    name = name.strip(f"{separator}. ")
    if len(name) > max_len:
        name = name[:max_len].rstrip(separator)
    return name


def parse_topic_map(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    raw = raw.strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        return json.loads(raw)
    result: dict[str, str] = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def load_manifest(asset_dir: Path, manifest_arg: Path | None) -> dict:
    candidates = []
    if manifest_arg:
        candidates.append(manifest_arg)
    candidates.extend([asset_dir / "manifest.json", asset_dir.with_suffix(".manifest.json")])
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {"assets": []}


def mine_near_text(before: str) -> str:
    """Return the closest label value found in near_text_before, or ''.

    Looks for the LAST occurrence of name:/alt:/title:/id: with a quoted value,
    which is the label nearest to the `image:"..."` token that precedes the
    extracted asset. This is heuristic but works well for HTML/JS data blobs
    that embed structured records (e.g. species trees, product catalogs).
    """
    if not before:
        return ""
    matches = LABEL_RE.findall(before)
    if matches:
        return matches[-1][1]  # (quote, value) tuples; take last value
    return ""


def fallback_name(entry: dict, index: int, max_len: int, separator: str) -> str:
    """Build the mime/index fallback name shared by all naming paths."""
    context = entry.get("context", {}) or {}
    mime_val = context.get("mime_group") or entry.get("mime_group") or entry.get("mime", "asset")
    if isinstance(mime_val, str) and "/" in mime_val:
        mime_val = mime_val.split("/", 1)[0]
    clean = sanitize(str(mime_val), max_len, separator)
    return f"{index:03d}{separator}{clean}"


def pick_name(
    entry: dict,
    name_from: str,
    topic_map: dict[str, str],
    max_len: int,
    separator: str,
    use_near_text: bool,
) -> tuple[str, str]:
    filename = entry.get("filename", "")
    stem = Path(filename).stem
    index = entry.get("index", 0)
    context = entry.get("context", {}) or {}

    for key in (filename, stem, f"asset_{index:03d}", str(index)):
        if key in topic_map:
            val = sanitize(topic_map[key], max_len, separator)
            if val:
                return val, "topic_map"

    if name_from == "index":
        return f"{index:03d}", "index"

    field_map = {
        "alt": ["alt"],
        "title": ["title"],
        "heading": ["heading"],
        "id": ["id"],
        "class": ["class"],
        "tag": ["tag", "id", "class"],
        "mime": ["mime_group"],
    }

    if name_from != "auto":
        for field in field_map.get(name_from, []):
            val = context.get(field) or entry.get(field)
            if val:
                clean = sanitize(str(val), max_len, separator)
                if clean:
                    return f"{index:03d}{separator}{clean}", field
        # Explicit mode found nothing for the requested field. Do NOT fall
        # through to the auto field order — that would silently turn
        # `--name-from alt` into auto mode. Drop to the mime/index fallback
        # instead, which is the documented behavior for "no match".
        return fallback_name(entry, index, max_len, separator), "fallback"

    auto_fields = ["alt", "title", "heading", "id", "class", "tag"]
    for field in auto_fields:
        val = context.get(field) or entry.get(field)
        if val:
            clean = sanitize(str(val), max_len, separator)
            if clean:
                return f"{index:03d}{separator}{clean}", field

    if use_near_text:
        mined = mine_near_text(context.get("near_text_before", "") or "")
        if mined:
            clean = sanitize(mined, max_len, separator)
            if clean:
                return f"{index:03d}{separator}{clean}", "near_text"

    return fallback_name(entry, index, max_len, separator), "fallback"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Rename extracted assets using manifest context.")
    parser.add_argument("asset_dir", type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(
        "--name-from",
        choices=["auto", "alt", "title", "heading", "id", "class", "tag", "mime", "index"],
        default="auto",
    )
    parser.add_argument("--topic-map", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-stem-length", "--max-length", dest="max_stem_length", type=int, default=80)
    parser.add_argument(
        "--separator",
        default="-",
        help="separator used to replace whitespace/underscore runs (default: '-'; was '_' before v4.0.0)",
    )
    parser.add_argument(
        "--no-near-text",
        dest="use_near_text",
        action="store_false",
        default=True,
        help="do not mine context.near_text_before for a label; use standard fields only",
    )
    parser.add_argument(
        "--update-html",
        type=Path,
        default=None,
        help="HTML file whose references should be rewritten in lockstep with renames",
    )
    args = parser.parse_args()

    if not args.asset_dir.exists():
        print(f"ERROR: asset dir not found: {args.asset_dir}", file=sys.stderr)
        return 1

    manifest = load_manifest(args.asset_dir, args.manifest)
    entries = manifest.get("assets") or manifest.get("files") or []
    topic_map = parse_topic_map(args.topic_map)

    if not entries:
        print("No manifest entries found. Nothing to rename.")
        return 0

    # Pre-read HTML once if we will rewrite it.
    html_text: str | None = None
    if args.update_html and not args.dry_run:
        if not args.update_html.exists():
            print(f"ERROR: --update-html target not found: {args.update_html}", file=sys.stderr)
            return 1
        html_text = args.update_html.read_text(encoding="utf-8")

    operations = []
    rename_map: list[tuple[str, str]] = []  # (old_basename, new_basename)
    for entry in entries:
        # Skip entries without context (e.g. from extract_style_script.py's
        # manifest, which describes CSS/JS blocks, not named assets). Renaming
        # those would produce meaningless fallback names and risk collisions.
        if not entry.get("context"):
            continue
        old = args.asset_dir / entry.get("filename", "")
        if not old.exists():
            continue
        new_stem, source = pick_name(
            entry,
            args.name_from,
            topic_map,
            args.max_stem_length,
            args.separator,
            args.use_near_text,
        )
        new_path = unique_path(args.asset_dir / f"{new_stem}{old.suffix.lower()}")
        if old.name == new_path.name:
            continue
        operations.append((old, new_path, source))
        rename_map.append((old.name, new_path.name))

    for old, new, source in operations:
        print(f"{old.name} -> {new.name}  [{source}]")
        if not args.dry_run:
            old.rename(new)

    if args.dry_run and args.update_html:
        # Report which references would change, without touching the file.
        if args.update_html.exists():
            sample = args.update_html.read_text(encoding="utf-8")
            would_change = [old for old, _ in rename_map if old in sample]
            print(f"[dry-run] references that would update in {args.update_html}: {len(would_change)}")
        print(f"Planned: {len(operations)} rename(s) (dry-run)")
        return 0

    if args.update_html and html_text is not None:
        for old_name, new_name in rename_map:
            html_text = replace_ref_in_html(html_text, old_name, new_name)
        args.update_html.write_text(html_text, encoding="utf-8")
        print(f"Updated references in: {args.update_html}")

    print(f"Planned: {len(operations)} rename(s){' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

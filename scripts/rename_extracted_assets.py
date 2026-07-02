#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rename extracted assets using manifest context."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WS_COMPRESS = re.compile(r"[\s_\-]+")


def sanitize(name: str, max_len: int) -> str:
    name = ILLEGAL_CHARS.sub("", name)
    name = WS_COMPRESS.sub("_", name)
    name = name.strip("_. ")
    return name[:max_len].rstrip("_") if len(name) > max_len else name


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


def pick_name(entry: dict, name_from: str, topic_map: dict[str, str], max_len: int) -> tuple[str, str]:
    filename = entry.get("filename", "")
    stem = Path(filename).stem
    index = entry.get("index", 0)
    context = entry.get("context", {}) or {}

    for key in (filename, stem, f"asset_{index:03d}", str(index)):
        if key in topic_map:
            val = sanitize(topic_map[key], max_len)
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
                clean = sanitize(str(val), max_len)
                if clean:
                    return f"{index:03d}_{clean}", field

    auto_fields = ["alt", "title", "heading", "id", "class", "tag", "mime_group"]
    for field in auto_fields:
        val = context.get(field) or entry.get(field)
        if val:
            clean = sanitize(str(val), max_len)
            if clean:
                return f"{index:03d}_{clean}", field

    mime = entry.get("mime", "asset").replace("/", "_").replace("+", "_")
    return f"{index:03d}_{sanitize(mime, max_len)}", "fallback"


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
    parser.add_argument("--name-from", choices=["auto", "alt", "title", "heading", "id", "class", "tag", "mime", "index"], default="auto")
    parser.add_argument("--topic-map", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-stem-length", "--max-length", dest="max_stem_length", type=int, default=80)
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

    operations = []
    for entry in entries:
        old = args.asset_dir / entry.get("filename", "")
        if not old.exists():
            continue
        new_stem, source = pick_name(entry, args.name_from, topic_map, args.max_stem_length)
        new_path = unique_path(args.asset_dir / f"{new_stem}{old.suffix.lower()}")
        if old.name == new_path.name:
            continue
        operations.append((old, new_path, source))

    for old, new, source in operations:
        print(f"{old.name} -> {new.name}  [{source}]")
        if not args.dry_run:
            old.rename(new)

    print(f"Planned: {len(operations)} rename(s){' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

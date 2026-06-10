#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 extract 步骤捕获的 HTML 语义上下文，智能重命名图片文件。

命名优先级链（从小到大，渐进向外查找）：
  alt → title → preceding_heading → parent_id → parent_class → {序号}

核心特点：
1. 自动从 manifest.json 中读取每张图片的 HTML 语义上下文。
2. 按优先级链选取最精确的描述作为文件名。
3. 无 manifest 时退化为纯序号命名。
4. 支持 --topic-map 手动覆盖（最高优先级）。
5. 支持 --name-from 指定优先使用的上下文字段。

使用示例：

python rename_images.py dist/images/                        # 智能命名（alt 优先）
python rename_images.py dist/images/ --name-from heading    # 标题优先
python rename_images.py dist/images/ --name-from index      # 纯序号：01.png, 02.png
python rename_images.py dist/images/ --dry-run              # 预览，不实际重命名
python rename_images.py dist/images/ --topic-map "img_01:自定义名"  # 手动覆盖

依赖：仅标准库，无需安装额外包。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Windows 控制台 UTF-8 兼容
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 文件名清理 ────────────────────────────────────────────────────────────────

# Windows / Unix 非法字符
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# 连续空白/下划线/横线压缩为单个下划线
_WS_COMPRESS = re.compile(r'[\s_\-]+')
# 文件名最大长度（不含扩展名）
MAX_STEM_LENGTH = 80


def sanitize_filename(name: str) -> str:
    """
    将任意文本清理为安全的文件名主干。
    - 移除非法字符
    - 空白/连字符统一为下划线
    - 去除首尾空白和下划线
    - 截断到合理长度
    """
    name = _ILLEGAL_CHARS.sub('', name)
    name = _WS_COMPRESS.sub('_', name)
    name = name.strip('_').strip()
    if len(name) > MAX_STEM_LENGTH:
        name = name[:MAX_STEM_LENGTH].rstrip('_')
    return name


# ── 上下文解析 ────────────────────────────────────────────────────────────────

# 优先级链定义：从小到大
PRIORITY_FIELDS = ["alt", "title", "preceding_heading", "parent_id", "parent_class"]

# 字段中文名（用于打印）
FIELD_LABELS = {
    "alt": "alt 属性",
    "title": "title 属性",
    "preceding_heading": "章节标题",
    "parent_id": "父容器 ID",
    "parent_class": "父容器 class",
    "index": "序号",
}


def resolve_name_from_context(
    context: dict | None,
    index: int,
    prefer_field: str | None = None,
    topic_map: dict | None = None,
    filename_prefix: str | None = None,
) -> tuple[str, str]:
    """
    从上下文中解析出最合适的文件名。

    参数:
        context:       extract 步骤捕获的语义上下文 dict
        index:         图片序号（从 1 开始）
        prefer_field:  优先使用的字段名（'alt','title','heading','index' 等）
        topic_map:     手动覆盖映射 {"img_01": "自定义名"}
        filename_prefix: 原始文件名前缀（如 "img_01"），用于 topic_map 匹配

    返回:
        (name_stem, source_field) — 文件名主干 和 来源字段名
    """
    # ── 最高优先级：手动 topic_map ──
    if topic_map and filename_prefix:
        if filename_prefix in topic_map:
            name = sanitize_filename(topic_map[filename_prefix])
            if name:
                return name, "topic_map"

    # ── 纯序号模式 ──
    if prefer_field == "index":
        return f"{index:02d}", "index"

    # ── 无上下文，退化为序号 ──
    if not context:
        return f"{index:02d}", "index"

    # ── 指定优先字段 ──
    if prefer_field and prefer_field != "auto":
        # heading 是 preceding_heading 的简写
        field_key = "preceding_heading" if prefer_field == "heading" else prefer_field
        val = context.get(field_key)
        if val:
            name = sanitize_filename(val)
            if name:
                return name, prefer_field

    # ── 自动模式：按优先级链查找 ──
    for field in PRIORITY_FIELDS:
        val = context.get(field)
        if val:
            name = sanitize_filename(val)
            if name:
                display_field = "heading" if field == "preceding_heading" else field
                return name, display_field

    # ── 兜底：序号 ──
    return f"{index:02d}", "index"


# ── manifest 加载 ────────────────────────────────────────────────────────────

def load_manifest(image_dir: Path) -> dict | None:
    """
    在图片目录同级查找 manifest 文件。
    尝试：
      1. {image_dir}.manifest.json
      2. {image_dir}/manifest.json
      3. {image_dir}/../{image_dir.name}.manifest.json
    """
    candidates = [
        image_dir.with_suffix(".manifest.json"),   # dist/images.manifest.json
        image_dir / "manifest.json",                # dist/images/manifest.json
        image_dir.parent / f"{image_dir.name}.manifest.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def build_context_map(manifest: dict | None) -> tuple[dict[str, dict], dict[str, int]]:
    """Build filename -> context and filename -> index maps from manifest."""
    if not manifest or "files" not in manifest:
        return {}, {}
    ctx_map: dict[str, dict] = {}
    idx_map: dict[str, int] = {}
    for entry in manifest["files"]:
        fname = entry.get("filename", "")
        ctx = entry.get("context")
        ctx_map[fname] = ctx or {}
        if "index" in entry:
            idx_map[fname] = entry["index"]
    return ctx_map, idx_map


# ── 解析自定义映射 ───────────────────────────────────────────────────────────

def parse_topic_map(raw: str) -> dict:
    """解析 --topic-map 参数，支持 JSON 格式或 'k1:v1,k2:v2' 格式"""
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    result = {}
    for item in raw.split(","):
        if ":" not in item:
            continue
        k, v = item.strip().split(":", 1)
        result[k.strip()] = v.strip()
    return result


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="根据 HTML 语义上下文智能重命名图片文件。"
    )
    parser.add_argument("image_dir", type=Path, default=Path("dist/images"),
                        nargs="?", help="图片目录，默认 dist/images/")
    parser.add_argument("--topic-map", type=str, default=None,
                        help="手动映射表，JSON 或 'img_01:名称,...' 格式（最高优先级）。")
    parser.add_argument("--name-from", type=str, default="auto",
                        choices=["auto", "alt", "title", "heading", "parent_id",
                                 "parent_class", "index"],
                        help="命名来源优先级（默认 auto 按优先级链）。")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅预览，不实际执行重命名")
    parser.add_argument("--pattern", type=str, default=r"^(img_\d{2})_",
                        help="文件名前缀匹配正则，默认 ^(img_\\d{2})_")

    args = parser.parse_args()

    if not args.image_dir.exists():
        print(f"错误：目录不存在：{args.image_dir}", file=sys.stderr)
        return 1

    # 加载 manifest 和上下文
    manifest = load_manifest(args.image_dir)
    ctx_map, idx_map = build_context_map(manifest)

    if manifest:
        print(f"已加载 manifest：{manifest.get('input', '?')} → {len(ctx_map)} 个上下文")
    else:
        print("未找到 manifest，将使用纯序号命名")

    # 解析手动映射
    topic_map = parse_topic_map(args.topic_map) if args.topic_map else None

    renamed = {}
    skipped = []

    # 优先按 manifest 的 files 列表顺序遍历（HTML 原始顺序），
    # 再补充目录中未被 manifest 覆盖的文件。
    if manifest and "files" in manifest:
        ordered_files = [entry["filename"] for entry in manifest["files"]
                         if entry.get("filename")]
        # 补充目录中未被 manifest 记录的文件
        manifest_set = set(ordered_files)
        for fname in sorted(os.listdir(args.image_dir)):
            fpath = args.image_dir / fname
            if not fpath.is_file():
                continue
            if fname == "manifest.json":
                continue
            if fname not in manifest_set:
                ordered_files.append(fname)
    else:
        # 无 manifest：按文件名字典序
        ordered_files = sorted(os.listdir(args.image_dir))

    for fname in ordered_files:
        fpath = args.image_dir / fname
        if not fpath.is_file():
            continue
        if fname == "manifest.json":
            continue

        # 提取文件名前缀（如 img_01）
        prefix_match = re.match(args.pattern, fname)
        prefix = prefix_match.group(1) if prefix_match else None

        # 获取扩展名
        ext = fname.rsplit(".", 1)[-1] if "." in fname else ""

        # 获取上下文
        context = ctx_map.get(fname)

        # 使用 manifest 中的原始序号（O(1) 查表），无则用累计值
        idx = idx_map.get(fname, len(renamed) + len(skipped) + 1)

        # 解析文件名
        name_stem, source = resolve_name_from_context(
            context=context,
            index=idx,
            prefer_field=args.name_from,
            topic_map=topic_map,
            filename_prefix=prefix,
        )

        if not name_stem:
            skipped.append(fname)
            continue

        # 组合新文件名
        new_name = f"{name_stem}.{ext}" if ext else name_stem
        new_path = args.image_dir / new_name

        # 目标名已存在且不是自己 → 加序号
        if new_path.exists() and new_path != fpath:
            counter = 1
            while new_path.exists():
                new_name = f"{name_stem}_{counter}.{ext}" if ext else f"{name_stem}_{counter}"
                new_path = args.image_dir / new_name
                counter += 1

        renamed[fname] = (new_name, source)

        if not args.dry_run:
            fpath.rename(new_path)

    # ── 输出结果 ──
    print(f"\n目录：{args.image_dir}")
    print(f"{'预览' if args.dry_run else '完成'}：{len(renamed)} 个重命名，{len(skipped)} 个跳过")

    if renamed:
        print(f"\n重命名：")
        for old, (new, source) in sorted(renamed.items()):
            label = FIELD_LABELS.get(source, source)
            print(f"  {old}")
            print(f"    → {new}  (来源: {label})")

    if skipped:
        print(f"\n跳过（无可用上下文）：")
        for f in skipped:
            print(f"  - {f}")

    if args.dry_run:
        print(f"\n（--dry-run 模式，未实际执行重命名）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

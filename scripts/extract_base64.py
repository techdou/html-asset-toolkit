#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 HTML 中提取 Base64 内嵌的图片，保存为独立文件，并捕获语义上下文。

核心特点：
1. 支持 <img src="data:...">、CSS url(data:...)、JS 字符串中的 Base64 图片。
2. 自动捕获每张图片的 HTML 语义上下文（alt、title、章节标题、父容器 id/class）。
3. 可选将 HTML 中的 Base64 替换为占位符（用于后续重新嵌入）。
4. 输出 JSON manifest 报告（含 context 字段，供 rename 脚本使用）。

使用示例：

python extract_base64.py dist/index.html                    # 提取到 dist/images/
python extract_base64.py in.html --output-dir ./imgs        # 指定输出目录
python extract_base64.py in.html --replace                   # 提取并替换为占位符
python extract_base64.py in.html --output-dir ./imgs --replace  # 全部参数

依赖：仅标准库，无需安装额外包。
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# Windows 控制台 UTF-8 兼容
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 正则 ───────────────────────────────────────────────────────────────────────

# 匹配 data:image/xxx;base64,YYYY 格式
DATA_URI_RE = re.compile(
    r'data:(image/[a-zA-Z0-9+-]+);base64,([A-Za-z0-9+/=\s]+)',
    re.IGNORECASE,
)

# 匹配标题标签内容
HEADING_RE = re.compile(
    r'<h[1-6][^>]*>(.*?)</h[1-6]>',
    re.IGNORECASE | re.DOTALL,
)

# 匹配 img 标签（可能跨行）
IMG_TAG_RE = re.compile(
    r'<img\b([^>]*)>',
    re.IGNORECASE | re.DOTALL,
)

# 匹配属性值
ATTR_ALT_RE = re.compile(r'\balt\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
ATTR_TITLE_RE = re.compile(r'\btitle\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
ATTR_CLASS_RE = re.compile(r'\bclass\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
ATTR_ID_RE = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

# 自闭合标签（不作为父容器）
VOID_ELEMENTS = frozenset([
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
])


# ── 上下文捕获 ─────────────────────────────────────────────────────────────────

def strip_html_tags(text: str) -> str:
    """移除 HTML 标签，返回纯文本。"""
    return re.sub(r'<[^>]+>', '', text).strip()


def capture_context(html: str, match_start: int, match_end: int) -> dict:
    """
    从 HTML 中捕获 data URI 周围的语义上下文。

    返回 dict:
        alt:              <img alt="..."> 的值
        title:            <img title="..."> 的值
        preceding_heading:  前面最近的 <h1>-<h6> 标签文本
        parent_id:        父容器元素的 id
        parent_class:     父容器元素的 class
    """
    context = {
        "alt": None,
        "title": None,
        "preceding_heading": None,
        "parent_id": None,
        "parent_class": None,
    }

    # ── 1. 检查是否在 <img> 标签内，提取 alt / title ──
    before = html[:match_start]
    # 从当前位置往回找最近的 <img
    img_start = before.rfind("<img")
    if img_start != -1:
        img_end = html.find(">", img_start)
        if img_end != -1 and img_end >= match_end - 1:
            # data URI 在这个 img 标签内
            img_attrs = html[img_start:img_end + 1]
            alt_m = ATTR_ALT_RE.search(img_attrs)
            if alt_m and alt_m.group(1).strip():
                context["alt"] = alt_m.group(1).strip()
            title_m = ATTR_TITLE_RE.search(img_attrs)
            if title_m and title_m.group(1).strip():
                context["title"] = title_m.group(1).strip()

    # ── 2. 查找前面最近的标题（h1-h6） ──
    last_heading = None
    for hm in HEADING_RE.finditer(html[:match_start]):
        text = strip_html_tags(hm.group(1))
        if text:
            last_heading = text
    context["preceding_heading"] = last_heading

    # ── 3. 查找父容器的 id / class ──
    # 从匹配位置往回扫描标签，找最近的有 id 或 class 的非 void 元素
    tag_pattern = re.compile(r'<(\w+)([^>]*)>', re.IGNORECASE)
    last_container = None

    for tm in tag_pattern.finditer(html[:match_start]):
        tag_name = tm.group(1).lower()
        attrs = tm.group(2)
        # 跳过自闭合和 void 元素
        if tag_name in VOID_ELEMENTS:
            continue
        if attrs.rstrip().endswith('/'):
            continue
        id_m = ATTR_ID_RE.search(attrs)
        cls_m = ATTR_CLASS_RE.search(attrs)
        if id_m or cls_m:
            last_container = {
                "id": id_m.group(1).strip() if id_m else None,
                "class": cls_m.group(1).strip() if cls_m else None,
            }

    if last_container:
        context["parent_id"] = last_container["id"]
        context["parent_class"] = last_container["class"]

    return context


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def decode_b64_ext(mime: str) -> str:
    ext = mime.split("/")[-1].replace("+xml", "").replace("jpeg", "jpg")
    if ext == "svg+xml":
        ext = "svg"
    return ext


def format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{num_bytes}B"


def extract_data_uris_with_context(html: str) -> list[tuple[str, str, str, int, int, int]]:
    """
    返回 [(full_match, mime, extension, byte_count, match_start, match_end)] 列表。
    带位置信息，用于后续上下文捕获。
    """
    results = []
    for m in DATA_URI_RE.finditer(html):
        mime = m.group(1)
        raw_b64 = m.group(2).replace("\n", "").replace("\r", "").replace(" ", "")
        try:
            img_bytes = base64.b64decode(raw_b64)
        except Exception:
            continue
        ext = decode_b64_ext(mime)
        results.append((m.group(0), mime, ext, len(img_bytes), m.start(), m.end()))
    return results


# ── 主入口 ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="从 HTML 中提取 Base64 内嵌图片到独立文件，并捕获语义上下文。"
    )
    parser.add_argument("input_html", type=Path, help="输入 HTML 文件路径")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="图片输出目录，默认 {input_html}/../dist/images/")
    parser.add_argument("--replace", action="store_true",
                        help="将 HTML 中的 Base64 替换为占位符（用于后续重新嵌入）")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="JSON 报告路径，默认与输出目录同名 .manifest.json")

    args = parser.parse_args()

    if not args.input_html.exists():
        print(f"错误：输入 HTML 不存在：{args.input_html}", file=sys.stderr)
        return 1

    # 默认输出到输入 HTML 同级的 dist/images/
    if args.output_dir is None:
        args.output_dir = args.input_html.parent / "dist" / "images"

    html = args.input_html.read_text(encoding="utf-8")
    items = extract_data_uris_with_context(html)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "input": str(args.input_html),
        "output_dir": str(args.output_dir),
        "total": len(items),
        "files": [],
    }

    replaced_html = html
    for i, (full_match, mime, ext, byte_count, m_start, m_end) in enumerate(items, 1):
        raw_b64 = re.search(r'base64,([A-Za-z0-9+/=\s]+)', full_match, re.IGNORECASE)
        if not raw_b64:
            continue
        b64_clean = raw_b64.group(1).replace("\n", "").replace("\r", "").replace(" ", "")
        img_bytes = base64.b64decode(b64_clean)
        short_hash = hashlib.md5(img_bytes).hexdigest()[:8]
        filename = f"img_{i:02d}_{short_hash}.{ext}"
        filepath = args.output_dir / filename
        filepath.write_bytes(img_bytes)

        # 捕获 HTML 语义上下文
        ctx = capture_context(html, m_start, m_end)

        manifest["files"].append({
            "index": i,
            "filename": filename,
            "mime": mime,
            "size": byte_count,
            "hash": short_hash,
            "context": ctx,
        })
        if args.replace:
            placeholder = f'data:image/{ext};base64,PLACEHOLDER_{i:02d}_{short_hash}'
            replaced_html = replaced_html.replace(full_match, placeholder, 1)

        # 打印上下文摘要
        size_str = format_size(byte_count)
        ctx_parts = []
        if ctx["alt"]:
            ctx_parts.append(f'alt="{ctx["alt"]}"')
        if ctx["title"]:
            ctx_parts.append(f'title="{ctx["title"]}"')
        if ctx["preceding_heading"]:
            ctx_parts.append(f'heading="{ctx["preceding_heading"]}"')
        ctx_summary = " ".join(ctx_parts) if ctx_parts else "(无语义上下文)"
        print(f"  [{i}] {mime} -> {filename} ({size_str})")
        print(f"       {ctx_summary}")

    # 写入替换后的 HTML（如果指定了 --replace）
    if args.replace:
        out_html = args.input_html.parent / f"{args.input_html.stem}.extracted{args.input_html.suffix}"
        out_html.write_text(replaced_html, encoding="utf-8")
        manifest["output_html"] = str(out_html)
        print(f"\n  HTML 已更新：{out_html}")

    # 写入 manifest
    manifest_path = args.manifest or args.output_dir.with_suffix(".manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    total_bytes = sum(f["size"] for f in manifest["files"])
    print(f"\n==============================================")
    print(f"提取完成：{len(items)} 张图片 → {args.output_dir}/")
    print(f"总大小：{format_size(total_bytes)}")
    print(f"报告：{manifest_path}")
    print(f"==============================================")

    if args.replace:
        print(f"原 HTML 已保留（未修改），替换版：{out_html}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

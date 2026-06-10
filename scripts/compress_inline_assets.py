#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压缩 HTML 中引用的本地图片，并将压缩后的图片以 Base64 形式内嵌到 HTML 中。

核心特点：
1. 保留原稿 HTML 不变，生成 embedding 版本。
2. 先压缩图片，再 Base64 内嵌。
3. 使用 Pillow 的 LANCZOS 高质量重采样。
4. 使用 WebP method=6 高努力压缩。
5. 使用 SSIM 感知质量搜索，在尽量保持视觉质量的同时减小体积。
6. 支持 <img src="...">、srcset="..."、CSS url(...) 和 JS 字符串中的本地图片。

使用示例：

python compress_inline_assets.py index.html                    # → dist/index.html
python compress_inline_assets.py in.html out.html            # 指定输入输出
python compress_inline_assets.py in.html out.html --ssim 0.99 # 高质量（截图/文字图）

依赖：pip install pillow numpy
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import mimetypes
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import unquote, urlparse

import numpy as np
from PIL import Image, ImageOps

# Windows 控制台 UTF-8 兼容
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 正则 ───────────────────────────────────────────────────────────────────────

IMG_SRC_RE = re.compile(
    r"(<img\b[^>]*?\bsrc\s*=\s*)([\"'])(?!data:)(.+?)(\2)",
    re.IGNORECASE | re.DOTALL,
)

SRCSET_RE = re.compile(
    r"((?:<img|<source)\b[^>]*?\bsrcset\s*=\s*)([\"'])(?!data:)(.*?)(\2)",
    re.IGNORECASE | re.DOTALL,
)

CSS_URL_RE = re.compile(
    r"url\(\s*([\"']?)(?!data:)([^)'\"]+)\1\s*\)",
    re.IGNORECASE,
)

# 匹配 JS 中的图片路径字符串，如 "images/xx.jpg" 或 'image.png'
# 排除已有 data:、外链、JS 模板变量（${...}）
JS_IMG_RE = re.compile(
    r'(["\'])([^"\']*?\.(?:jpg|jpeg|png|gif|webp|svg|bmp|ico))\1',
    re.IGNORECASE,
)


# ── 数据结构 ──────────────────────────────────────────────────────────────────

@dataclass
class AssetResult:
    source: str
    resolved_path: str
    output_mime: str
    original_bytes: int
    compressed_bytes: int
    embedded_bytes: int
    width: Optional[int]
    height: Optional[int]
    quality: Optional[int]
    ssim: Optional[float]
    action: str
    note: str = ""


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def is_external_or_data_url(src: str) -> bool:
    value = src.strip()
    if not value:
        return True
    lowered = value.lower()
    if lowered.startswith(("data:", "http://", "https://", "//", "mailto:", "tel:", "#")):
        return True
    return False


def remove_url_query_and_fragment(src: str) -> str:
    parsed = urlparse(src)
    path = parsed.path if parsed.scheme == "" else src
    return unquote(path)


def resolve_local_asset(src: str, html_dir: Path, assets_root: Optional[Path]) -> Optional[Path]:
    if is_external_or_data_url(src):
        return None

    cleaned = remove_url_query_and_fragment(src)
    candidate = Path(cleaned)

    search_roots = []
    if candidate.is_absolute():
        search_roots.append(Path("/"))
    else:
        search_roots.append(html_dir)
        if assets_root:
            search_roots.append(assets_root)

    for root in search_roots:
        path = candidate if candidate.is_absolute() else (root / candidate)
        if path.exists() and path.is_file():
            return path.resolve()
    return None


def is_svg(path: Path) -> bool:
    return path.suffix.lower() == ".svg"


def guess_mime(path: Path, fallback: str = "application/octet-stream") -> str:
    return mimetypes.guess_type(path.name)[0] or fallback


def file_to_data_url(raw: bytes, mime: str) -> str:
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def image_has_animation(image: Image.Image) -> bool:
    try:
        return getattr(image, "is_animated", False) and getattr(image, "n_frames", 1) > 1
    except Exception:
        return False


def normalize_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    image = ImageOps.exif_transpose(image)
    has_alpha = image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )
    image = image.convert("RGBA") if has_alpha else image.convert("RGB")
    width, height = image.size
    scale = min(max_width / width, max_height / height, 1.0)
    if scale < 1.0:
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    return image


def to_luminance_array(image: Image.Image, max_side: int = 512) -> np.ndarray:
    img = image.convert("L")
    w, h = img.size
    scale = min(max_side / w, max_side / h, 1.0)
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.BICUBIC)
    return np.asarray(img, dtype=np.float32)


def global_ssim(reference: Image.Image, candidate: Image.Image) -> float:
    x = to_luminance_array(reference)
    y = to_luminance_array(candidate)
    if x.shape != y.shape:
        candidate = candidate.resize(reference.size, Image.Resampling.BICUBIC)
        y = to_luminance_array(candidate)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    ux, uy = float(x.mean()), float(y.mean())
    vx, vy = float(x.var()), float(y.var())
    cov = float(((x - ux) * (y - uy)).mean())
    num = (2 * ux * uy + c1) * (2 * cov + c2)
    den = (ux**2 + uy**2 + c1) * (vx + vy + c2)
    return max(0.0, min(1.0, num / den)) if den != 0 else 1.0


def encode_webp(image: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    kwargs = {"format": "WEBP", "quality": int(quality), "method": 6, "exact": True}
    if image.mode == "RGBA":
        kwargs["alpha_quality"] = int(quality)
    image.save(buf, **kwargs)
    return buf.getvalue()


def decode_image(raw: bytes) -> Image.Image:
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def find_best_webp_by_ssim(
    image: Image.Image,
    min_quality: int,
    max_quality: int,
    target_ssim: float,
) -> Tuple[bytes, int, float]:
    low, high = min_quality, max_quality
    high_raw = encode_webp(image, max_quality)
    high_img = decode_image(high_raw)
    high_ssim = global_ssim(image, high_img)
    if high_ssim < target_ssim:
        return high_raw, max_quality, high_ssim

    best_raw, best_quality, best_ssim = None, max_quality, -1.0
    while low <= high:
        mid = (low + high) // 2
        raw = encode_webp(image, mid)
        score = global_ssim(image, decode_image(raw))
        if score >= target_ssim:
            best_raw, best_quality, best_ssim = raw, mid, score
            high = mid - 1
        else:
            low = mid + 1
    return (best_raw, best_quality, best_ssim) if best_raw else (high_raw, max_quality, high_ssim)


def compress_asset_to_data_url(
    path: Path, source: str,
    max_width: int, max_height: int,
    min_quality: int, max_quality: int,
    target_ssim: float, keep_animated: bool,
) -> Tuple[str, AssetResult]:
    original_raw = path.read_bytes()
    original_bytes = len(original_raw)

    if is_svg(path):
        mime = "image/svg+xml"
        data_url = file_to_data_url(original_raw, mime)
        result = AssetResult(source, str(path), mime, original_bytes, original_bytes,
                             len(data_url.encode("utf-8")), None, None, None, None,
                             "embedded-original-svg", "SVG 不压缩，直接 Base64 嵌入。")
        return data_url, result

    try:
        with Image.open(path) as im:
            if image_has_animation(im) and keep_animated:
                mime = guess_mime(path, "image/gif")
                data_url = file_to_data_url(original_raw, mime)
                result = AssetResult(source, str(path), mime, original_bytes, original_bytes,
                                     len(data_url.encode("utf-8")),
                                     getattr(im, "width", None), getattr(im, "height", None),
                                     None, None, "embedded-original-animation", "检测到动画，保持原文件。")
                return data_url, result
            normalized = normalize_image(im, max_width, max_height)
    except Exception as exc:
        mime = guess_mime(path)
        data_url = file_to_data_url(original_raw, mime)
        result = AssetResult(source, str(path), mime, original_bytes, original_bytes,
                             len(data_url.encode("utf-8")), None, None, None, None,
                             "embedded-original-error", f"图片读取失败，保持原文件：{exc}")
        return data_url, result

    compressed_raw, quality, ssim_score = find_best_webp_by_ssim(
        normalized, min_quality, max_quality, target_ssim)
    data_url = file_to_data_url(compressed_raw, "image/webp")
    w, h = normalized.size
    result = AssetResult(
        source, str(path), "image/webp", original_bytes, len(compressed_raw),
        len(data_url.encode("utf-8")), w, h, quality, round(float(ssim_score), 6),
        "compressed-webp-and-embedded", "LANCZOS 缩放 + WebP method=6 + SSIM 质量搜索。")
    return data_url, result


# ── 替换函数 ──────────────────────────────────────────────────────────────────

def _get_or_compress(path: Path, source: str, opts: argparse.Namespace,
                      cache: Dict, results: list) -> Tuple[str, AssetResult]:
    if path not in cache:
        data_url, result = compress_asset_to_data_url(
            path, source,
            opts.max_width, opts.max_height,
            opts.min_quality, opts.max_quality,
            opts.target_ssim,
            not opts.flatten_animation,
        )
        cache[path] = (data_url, result)
        results.append(result)
    else:
        data_url, result = cache[path]
        dup = AssetResult(**asdict(result))
        dup.source = source
        dup.action = "reused-cached-data-url"
        results.append(dup)
    return data_url, result


def replace_img_sources(html: str, html_dir: Path, assets_root: Optional[Path],
                        opts: argparse.Namespace,
                        cache: Dict, results: list, done: set) -> str:
    def repl(m: re.Match) -> str:
        prefix, quote, src, _ = m.groups()
        if "$" in src:
            return m.group(0)
        path = resolve_local_asset(src, html_dir, assets_root)
        if path is None:
            return m.group(0)
        data_url, result = _get_or_compress(path, src, opts, cache, results)
        done.add(src)
        return f"{prefix}{quote}{data_url}{quote}"
    return IMG_SRC_RE.sub(repl, html)


def replace_css_urls(html: str, html_dir: Path, assets_root: Optional[Path],
                     opts: argparse.Namespace,
                     cache: Dict, results: list, done: set) -> str:
    def repl(m: re.Match) -> str:
        quote, src = m.groups()
        path = resolve_local_asset(src, html_dir, assets_root)
        if path is None:
            return m.group(0)
        data_url, result = _get_or_compress(path, src, opts, cache, results)
        done.add(src)
        return f'url({quote}{data_url}{quote})'
    return CSS_URL_RE.sub(repl, html)


def split_srcset_candidate(candidate: str) -> Tuple[str, str]:
    """拆分 srcset 单个候选项，如 'img.jpg 2x' -> ('img.jpg', ' 2x')"""
    stripped = candidate.strip()
    if not stripped:
        return "", ""
    parts = stripped.split(maxsplit=1)
    url = parts[0]
    descriptor = f" {parts[1]}" if len(parts) == 2 else ""
    return url, descriptor


def replace_srcset_values(html: str, html_dir: Path, assets_root: Optional[Path],
                          opts: argparse.Namespace,
                          cache: Dict, results: list, done: set) -> str:
    """替换 <img>/<source> 的 srcset 中的本地图片。"""
    def repl(m: re.Match) -> str:
        prefix, quote, srcset, closing_quote = m.groups()
        candidates = []
        for raw in srcset.split(","):
            original = raw.strip()
            if not original:
                continue
            url, descriptor = split_srcset_candidate(original)
            if not url or "$" in url:
                candidates.append(original)
                continue
            if url in done:
                candidates.append(original)
                continue
            path = resolve_local_asset(url, html_dir, assets_root)
            if path is None:
                candidates.append(original)
                continue
            data_url, result = _get_or_compress(path, url, opts, cache, results)
            done.add(url)
            candidates.append(f"{data_url}{descriptor}")
        if not candidates:
            return m.group(0)
        return f"{prefix}{quote}{', '.join(candidates)}{closing_quote}"
    return SRCSET_RE.sub(repl, html)


def replace_js_img_strings(html: str, html_dir: Path, assets_root: Optional[Path],
                           opts: argparse.Namespace,
                           cache: Dict, results: list, done: set) -> str:
    def repl(m: re.Match) -> str:
        quote, src = m.group(1), m.group(2)
        if "data:" in src or src.startswith(("http://", "https://", "//")):
            return m.group(0)
        if "$" in src or "/" not in src:
            return m.group(0)
        if src in done:
            return m.group(0)
        path = resolve_local_asset(src, html_dir, assets_root)
        if path is None:
            return m.group(0)
        data_url, result = _get_or_compress(path, src, opts, cache, results)
        done.add(src)
        return f"{quote}{data_url}{quote}"
    return JS_IMG_RE.sub(repl, html)


# ── 工具 ──────────────────────────────────────────────────────────────────────

def format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{num_bytes}B"


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="压缩 HTML 本地图片并 Base64 内嵌，保留原稿。")
    parser.add_argument("input_html", type=Path, help="输入 HTML 文件路径")
    parser.add_argument("output_html", nargs="?", type=Path, default=None,
                        help="输出 HTML 文件路径（省略则自动生成 dist/{filename}）")
    parser.add_argument("--assets-root", type=Path, default=None,
                        help="图片资源根目录，默认按 HTML 所在目录解析相对路径。")
    parser.add_argument("--max-width", type=int, default=1800, help="最大宽度，默认 1800")
    parser.add_argument("--max-height", type=int, default=1800, help="最大高度，默认 1800")
    parser.add_argument("--min-quality", type=int, default=45, help="WebP 最低质量，默认 45")
    parser.add_argument("--max-quality", type=int, default=88, help="WebP 最高质量，默认 88")
    parser.add_argument("--target-ssim", type=float, default=0.985,
                        help="目标 SSIM，默认 0.985；截图/文字图可设 0.99。")
    parser.add_argument("--flatten-animation", action="store_true",
                        help="开启则将动图压成静态 WebP；默认保持原动画。")
    parser.add_argument("--manifest", type=Path, default=None,
                        help="JSON 处理报告路径，默认与输出 HTML 同名 .manifest.json。")

    args = parser.parse_args()

    if not args.input_html.exists():
        print(f"错误：输入 HTML 不存在：{args.input_html}", file=sys.stderr)
        return 1
    if not (0 < args.min_quality <= args.max_quality <= 100):
        print("错误：质量参数需满足 0 < min_quality <= max_quality <= 100", file=sys.stderr)
        return 1
    if not (0.0 < args.target_ssim <= 1.0):
        print("错误：target_ssim 需在 0 到 1 之间", file=sys.stderr)
        return 1

    # 自动生成输出路径：index.html → dist/index.html
    if args.output_html is None:
        args.output_html = args.input_html.parent / "dist" / args.input_html.name

    html = args.input_html.read_text(encoding="utf-8")
    html_dir = args.input_html.parent.resolve()
    assets_root = args.assets_root.resolve() if args.assets_root else None

    cache: Dict[Path, Tuple[str, AssetResult]] = {}
    results: list[AssetResult] = []
    done: set = set()  # 防止 JS 正则重复匹配已替换过的路径

    html = replace_img_sources(html, html_dir, assets_root, args, cache, results, done)
    html = replace_srcset_values(html, html_dir, assets_root, args, cache, results, done)
    html = replace_css_urls(html, html_dir, assets_root, args, cache, results, done)
    html = replace_js_img_strings(html, html_dir, assets_root, args, cache, results, done)

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(html, encoding="utf-8")

    manifest_path = args.manifest or args.output_html.with_suffix(".manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "input": str(args.input_html),
        "output": str(args.output_html),
        "assets_root": str(assets_root) if assets_root else None,
        "total": len(results),
        "assets": [asdict(r) for r in results],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    size_before = len(args.input_html.read_bytes())
    size_after = len(html.encode("utf-8"))

    print("=" * 56)
    print("处理完成")
    print(f"  输入（原稿）: {args.input_html}  ({format_size(size_before)})")
    print(f"  输出（内嵌版）: {args.output_html}  ({format_size(size_after)})")
    print(f"  报告: {manifest_path}")
    print("=" * 56)

    if not results:
        print("未发现可内嵌的本地图片。")
        return 0

    total_orig = sum(r.original_bytes for r in results)
    total_comp = sum(r.compressed_bytes for r in results)
    print(f"\n图片处理结果（共 {len(results)} 张）：")
    for r in results:
        ratio = r.compressed_bytes / r.original_bytes if r.original_bytes else 1
        qt = "-" if r.quality is None else str(r.quality)
        ss = "-" if r.ssim is None else f"{r.ssim:.4f}"
        print(f"  {r.source}")
        print(f"    {format_size(r.original_bytes)} → {format_size(r.compressed_bytes)} "
              f"({ratio:.1%}) | q={qt} ssim={ss} | {r.action}")
        if r.note:
            print(f"    {r.note}")

    print(f"\n  总计: {format_size(total_orig)} → {format_size(total_comp)} ({(total_comp/total_orig):.1%})")
    print(f"  HTML: {format_size(size_before)} → {format_size(size_after)} ({(size_after/size_before)*100:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
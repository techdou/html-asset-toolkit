---
name: html-asset-toolkit
description: "Complete toolkit for managing images in HTML files: compress and inline images as Base64, extract Base64 images to files with semantic context capture, and smart rename using HTML context. Use when: (1) Creating a self-contained single-file HTML with all images embedded, (2) Extracting embedded images from HTML for editing, (3) Renaming extracted images using alt/heading/context, (4) Converting between file-based and embedded HTML workflows. Covers the full embed-extract-rename cycle."
---

# HTML Asset Toolkit

Three scripts for the full HTML image management cycle: **embed**, **extract**, **rename**.

## Workflow

```
原稿 HTML（外部图片）
    ↓ 1. embed（WebP 压缩 + Base64 内嵌）
dist/index.html
    ↓ 2. extract（Base64 → 图片文件 + 捕获语义上下文）
dist/images/ + manifest（含 alt/title/heading 等上下文）
    ↓ 3. rename（按上下文智能命名：alt → title → heading → 序号）
01_葡萄接收区.png ...
    ↓ 1. embed（重新嵌入）
dist/index.html
```

## Scripts

### 1. compress_inline_assets.py — 嵌入

压缩本地图片并 Base64 内嵌到 HTML，**原稿不动**。

```bash
# 自动生成 dist/index.html
python scripts/compress_inline_assets.py index.html

# 高质量模式（截图/文字图）
python scripts/compress_inline_assets.py in.html --target-ssim 0.99

# 指定输出
python scripts/compress_inline_assets.py in.html out.html
```

- 支持 `<img src>`、`srcset`、CSS `url()`、JS 字符串四种图片来源
- WebP 压缩 + SSIM 二分搜索，自动找最低满足质量的质量值
- 输出 `.manifest.json` 报告

### 2. extract_base64.py — 提取

从 HTML 中提取 Base64 内嵌图片到独立文件，**同时捕获 HTML 语义上下文**。

```bash
# 提取到 dist/images/（自动捕获上下文）
python scripts/extract_base64.py dist/index.html

# 指定输出目录
python scripts/extract_base64.py in.html --output-dir ./imgs

# 提取并替换为占位符（用于后续重新嵌入）
python scripts/extract_base64.py in.html --replace
```

- 自动捕获每张图片的 **alt**、**title**、**章节标题**、**父容器 id/class**
- 上下文信息写入 manifest 的 `context` 字段，供 rename 使用
- `--replace` 时输出 `.extracted.html`（占位符版），原 HTML 不变

### 3. rename_images.py — 智能重命名

根据 extract 步骤捕获的 HTML 语义上下文，按**优先级链**自动生成语义化文件名。

```bash
# 智能命名（默认：alt → title → heading → id → class → 序号）
python scripts/rename_images.py dist/images/

# 指定优先使用章节标题
python scripts/rename_images.py dist/images/ --name-from heading

# 纯序号命名
python scripts/rename_images.py dist/images/ --name-from index

# 预览模式
python scripts/rename_images.py dist/images/ --dry-run

# 手动覆盖（最高优先级）
python scripts/rename_images.py dist/images/ --topic-map "img_01:自定义名,img_02:另一个名"
```

**命名优先级链（从小到大，渐进向外查找）：**

```
alt="葡萄接收区"        ← 图片自身的描述（最精准）
    ↓ 没有？
title="步骤一"          ← 图片的补充说明
    ↓ 没有？
<h2>葡萄接收区</h2>     ← 外层章节标题（语义范围更大）
    ↓ 没有？
id="step-01"           ← 父容器的 ID
    ↓ 没有？
class="section-intro"  ← 父容器的 class
    ↓ 都没有？
01.png                 ← 兜底：纯序号
```

- 自动文件名清理（非法字符过滤、长度截断、冲突加序号）
- 无 manifest 时自动退化为纯序号命名
- `--topic-map` 手动覆盖优先级最高

## Parameters

See [parameters.md](references/parameters.md) for complete parameter reference.

## Dependencies

```bash
# 嵌入（compress）需要
pip install pillow numpy

# 提取（extract）和重命名（rename）仅需标准库
```

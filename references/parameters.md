# 参数参考

## compress_inline_assets.py — 嵌入

| 参数 | 默认值 | 说明 |
|---|---|---|
| `input_html` | （必需） | 输入 HTML 原稿 |
| `output_html` | 自动 `dist/{filename}` | 输出路径 |
| `--assets-root` | HTML 所在目录 | 图片资源根目录 |
| `--max-width` | 1800 | 压缩前最大宽度 |
| `--max-height` | 1800 | 压缩前最大高度 |
| `--min-quality` | 45 | WebP 最低质量 |
| `--max-quality` | 88 | WebP 最高质量 |
| `--target-ssim` | 0.985 | 目标 SSIM；截图/文字图设 0.99 |
| `--flatten-animation` | False | 动图压成静态 WebP |
| `--manifest` | `{output}.manifest.json` | JSON 报告路径 |

## extract_base64.py — 提取

| 参数 | 默认值 | 说明 |
|---|---|---|
| `input_html` | （必需） | 输入 HTML 文件 |
| `--output-dir` | `dist/images/` | 图片输出目录（相对于输入 HTML） |
| `--replace` | False | 将 HTML 中 Base64 替换为占位符 |
| `--manifest` | `{output_dir}.manifest.json` | JSON 报告路径 |

**自动捕获的上下文字段**（写入 manifest 的 `context`）：

| 字段 | 来源 | 说明 |
|------|------|------|
| `alt` | `<img alt="...">` | 图片的替代文字描述 |
| `title` | `<img title="...">` | 图片的标题 |
| `preceding_heading` | 前面最近的 `<h1>`~`<h6>` | 所属章节标题 |
| `parent_id` | 父元素 `id="..."` | 父容器的 ID |
| `parent_class` | 父元素 `class="..."` | 父容器的 class |

## rename_images.py — 智能重命名

| 参数 | 默认值 | 说明 |
|---|---|---|
| `image_dir` | `dist/images/` | 图片目录 |
| `--name-from` | `auto` | 命名来源：`auto`/`alt`/`title`/`heading`/`parent_id`/`parent_class`/`index` |
| `--topic-map` | （无） | 手动映射表，JSON 或 `img_01:名称,...` 格式（最高优先级） |
| `--dry-run` | False | 仅预览 |
| `--pattern` | `^(img_\d{2})_` | 文件名前缀匹配正则 |

**`--name-from` 选项说明：**

| 值 | 行为 |
|----|------|
| `auto` | 按优先级链自动选取（默认） |
| `alt` | 只用 alt 属性 |
| `title` | 只用 title 属性 |
| `heading` | 只用章节标题 |
| `parent_id` | 只用父容器 ID |
| `parent_class` | 只用父容器 class |
| `index` | 纯序号命名（`01.png`, `02.png`） |

## 共同依赖

```bash
# 嵌入（压缩）需要
pip install pillow numpy

# 提取和重命名仅需标准库
```

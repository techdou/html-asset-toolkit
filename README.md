# HTML Asset Toolkit 🖼️

> HTML 富文本讲义制作的图片资产管理工具包 —— 嵌入、提取、智能重命名

## 为什么是 HTML？为什么是这个工具？

在 AI Native 时代，**HTML 是讲义制作的最佳载体**：

- 📱 **零依赖传播** — 单个 HTML 文件，微信/钉钉/飞书直接发送，无需服务器
- 🎨 **富文本表现力** — 原生支持排版、动画、交互、响应式，比 PDF/PPT 更生动
- 🔗 **即时可读** — 任何设备双击打开，无需安装任何软件
- 🤖 **AI 原生友好** — Markdown/HTML 是 LLM 最擅长生成和编辑的格式
- 🔄 **版本可控** — 纯文本，Git 友好，diff 清晰，协作无障碍
- 📐 **多端适配** — 手机、平板、电脑自适应，一套内容全平台覆盖

**但 HTML 讲义有个痛点：图片是外部文件，分发时容易丢失。**

这个工具包解决了这个问题 —— **三个脚本覆盖完整的图片管理闭环**：

```
原稿 HTML（外部图片引用）
    ↓ 1. embed — 压缩 + Base64 内嵌
dist/index.html              ← 单文件，图片全部内嵌，可直接分享
    ↓ 2. extract — 提取图片 + 捕获 HTML 语义上下文
dist/images/                  ← 图片文件 + 上下文信息（alt、标题等）
    ↓ 修改图片
    ↓ 3. rename — 智能语义重命名
01_葡萄接收区.png ...
    ↓ 1. embed — 重新嵌入
dist/index.html              ← 更新后的单文件
```

## 核心特性

### 📦 embed — 压缩内嵌

将 HTML 中的本地图片压缩为 WebP 并 Base64 内嵌，**原稿不动**。

- 支持 `<img src>`、`srcset`、CSS `url()`、JS 字符串四种来源
- SSIM 感知质量搜索 —— 自动找到满足视觉质量的最小体积
- SVG 直接嵌入、动图智能保留
- 输出到 `dist/` 子目录，不污染源目录

```bash
python scripts/compress_inline_assets.py index.html
# → dist/index.html（图片全部内嵌）
```

### 📤 extract — 提取 + 语义捕获

从 HTML 中提取 Base64 图片，**同时捕获 HTML 语义上下文**。

- 自动捕获 `alt`、`title`、章节标题、父容器 id/class
- 上下文写入 manifest，供 rename 智能使用
- 支持 `--replace` 生成占位符版 HTML（用于编辑后重新嵌入）

```bash
python scripts/extract_base64.py dist/index.html
# → dist/images/（图片文件 + 上下文信息）
```

### 🏷️ rename — 智能语义重命名

根据 HTML 上下文按**优先级链**自动生成语义化文件名：

```
alt="葡萄接收区"           ← 最精准（图片自身描述）
    ↓ 没有？
title="步骤一"             ← 图片补充说明
    ↓ 没有？
<h2>葡萄接收区</h2>        ← 章节标题（语义范围更大）
    ↓ 没有？
id="step-01"              ← 父容器 ID
    ↓ 都没有？
01.png                    ← 兜底：纯序号
```

```bash
python scripts/rename_images.py dist/images/
# img_01_xxx.png → 葡萄接收区.png（来源: alt 属性）
```

## 典型使用场景

### 场景一：制作 AI 讲义分发给学生

```bash
# 1. 用 AI 生成带图片的 HTML 讲义（或用 Typora 导出）
# 2. 内嵌所有图片，生成单文件
python scripts/compress_inline_assets.py lecture.html
# 3. 分享 dist/lecture.html — 一个文件搞定
```

### 场景二：提取图片编辑后重新嵌入

```bash
# 1. 从内嵌版 HTML 提取图片
python scripts/extract_base64.py dist/lecture.html --replace
# 2. 用 Photoshop/Figma 编辑 dist/images/ 中的图片
# 3. 智能重命名
python scripts/rename_images.py dist/images/
# 4. 更新原稿中的图片引用，重新嵌入
python scripts/compress_inline_assets.py lecture.html
```

### 场景三：批量处理多个课程文件

```bash
for f in day1.html day2.html day3.html; do
  python scripts/compress_inline_assets.py "$f"
done
# → dist/day1.html, dist/day2.html, dist/day3.html
```

## 安装

无需安装，克隆即可使用：

```bash
git clone https://github.com/techdou/html-asset-toolkit.git
cd html-asset-toolkit
```

### 依赖

```bash
# embed（压缩）需要
pip install pillow numpy

# extract 和 rename 仅需 Python 标准库，无需额外安装
```

## 参数参考

详见 [references/parameters.md](references/parameters.md)。

## 作为 Claude Code Skill 使用

如果你使用 [Claude Code](https://claude.ai/code)，可以将此工具包注册为 skill：

```bash
# 复制到 skills 目录
cp -r html-asset-toolkit ~/.claude/skills/html-asset-toolkit
```

然后在 Claude Code 中直接说"把 HTML 里的图片嵌入"即可自动调用。

## 技术细节

| 特性 | 说明 |
|------|------|
| 压缩算法 | WebP (method=6) + SSIM 二分搜索 |
| 质量保证 | 默认 SSIM ≥ 0.985，接近无损 |
| 典型压缩率 | 原始 1-2MB → 压缩后 50-85KB（~95% 体积缩减） |
| 命名策略 | alt → title → heading → parent_id → class → 序号 |
| 文件名安全 | 自动过滤非法字符、截断长度、冲突加序号 |

## License

MIT License — 自由使用、修改和分发。

---

**Made with ❤️ for AI Native educators and content creators**

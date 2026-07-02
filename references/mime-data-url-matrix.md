# MIME 与 Data URL 前缀速查

常见写法：

```text
data:<MIME>;base64,<Base64字符串>
```

| 文件类型 | 推荐 MIME | Data URL 前缀 |
|---|---|---|
| MP3 | `audio/mpeg` | `data:audio/mpeg;base64,` |
| WAV | `audio/wav` | `data:audio/wav;base64,` |
| OGG | `audio/ogg` | `data:audio/ogg;base64,` |
| M4A | `audio/mp4` | `data:audio/mp4;base64,` |
| PNG | `image/png` | `data:image/png;base64,` |
| JPG/JPEG | `image/jpeg` | `data:image/jpeg;base64,` |
| WebP | `image/webp` | `data:image/webp;base64,` |
| GIF | `image/gif` | `data:image/gif;base64,` |
| SVG | `image/svg+xml` | `data:image/svg+xml;base64,` 或 `data:image/svg+xml,` |
| MP4 | `video/mp4` | `data:video/mp4;base64,` |
| WebM | `video/webm` | `data:video/webm;base64,` |
| GLB | `model/gltf-binary` | `data:model/gltf-binary;base64,` |
| glTF | `model/gltf+json` | `data:model/gltf+json;base64,` |
| STL | `model/stl` | `data:model/stl;base64,` |
| OBJ | `model/obj` | `data:model/obj;base64,` |
| USDZ | `model/vnd.usdz+zip` | `data:model/vnd.usdz+zip;base64,` |
| PDF | `application/pdf` | `data:application/pdf;base64,` |
| WASM | `application/wasm` | `data:application/wasm;base64,` |
| CSS | `text/css` | `data:text/css;base64,` |
| JS/MJS | `text/javascript` | `data:text/javascript;base64,` |
| WOFF2 | `font/woff2` | `data:font/woff2;base64,` |
| WOFF | `font/woff` | `data:font/woff;base64,` |
| TTF | `font/ttf` | `data:font/ttf;base64,` |
| OTF | `font/otf` | `data:font/otf;base64,` |

## 建议

- 浏览器原生可识别的图片、音频、视频可以直接放到 `src="data:..."`。
- GLB/STL 这类 3D 文件通常交给 Three.js loader 解析。
- STL 的 MIME 在实际项目中不如 GLB 统一，遇到兼容问题可退到 `application/octet-stream`，再用 `ArrayBuffer` 解析。

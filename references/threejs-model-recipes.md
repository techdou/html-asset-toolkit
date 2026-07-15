# Three.js 模型加载方案

GLB/STL 转成 Base64 后，浏览器不能像图片那样“直接显示”，需要 Three.js loader 解析。

## GLB：直接 load Data URL

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
const glbUrl = 'data:model/gltf-binary;base64,...';

loader.load(glbUrl, (gltf) => {
  scene.add(gltf.scene);
});
```

适合小型 GLB。大型 GLB 更推荐 Blob URL 或外联。

## GLB：Base64 → ArrayBuffer → parse

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

function base64ToArrayBuffer(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

const base64 = '...';
const arrayBuffer = base64ToArrayBuffer(base64);
const loader = new GLTFLoader();

loader.parse(arrayBuffer, '', (gltf) => {
  scene.add(gltf.scene);
});
```

## STL：直接 load Data URL

```js
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

const loader = new STLLoader();
const stlUrl = 'data:model/stl;base64,...';

loader.load(stlUrl, (geometry) => {
  const mesh = new THREE.Mesh(geometry, material);
  scene.add(mesh);
});
```

## STL：Base64 → ArrayBuffer → parse

```js
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

function base64ToArrayBuffer(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

const base64 = '...';
const arrayBuffer = base64ToArrayBuffer(base64);
const loader = new STLLoader();
const geometry = loader.parse(arrayBuffer);
const mesh = new THREE.Mesh(geometry, material);
scene.add(mesh);
```

## Blob URL 方案

当 Data URL 过长，或者某些 loader 对 Data URL 不稳定时，使用 Blob URL：

```js
function dataUrlToBlobUrl(dataUrl) {
  const [header, payload] = dataUrl.split(',');
  const mime = header.match(/^data:([^;]+)/)?.[1] || 'application/octet-stream';
  const binary = atob(payload);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: mime });
  return URL.createObjectURL(blob);
}

const blobUrl = dataUrlToBlobUrl('data:model/gltf-binary;base64,...');
loader.load(blobUrl, onLoad);
```

## 实务建议

- 网页展示优先 GLB，不优先 STL。
- STL 只保存几何，不保存材质、纹理和层级；教学展示可用，但正式 Web 3D 推荐 GLB。
- 大模型先做 Draco/Meshopt 压缩，再决定是否 Base64 内嵌。
- 单文件课程 Demo 中，模型太大时应在页面中加入”模型加载中”的提示。

## Draco 压缩与离线加载

GLB 模型如果用了 `KHR_draco_mesh_compression`，Three.js 的 `DRACOLoader` 会在运行时从 Google CDN 远程拉取解码器：

- `draco_decoder.js`（asm.js 路径）
- `draco_wasm_wrapper.js` + `draco_decoder.wasm`（wasm 路径）

这些文件不在本地构建产物里。直接打包后，离线环境无法加载模型。

### 工具的 Draco 支持

1. **验证提示**：`validate_single_html.py` 扫描内联 JS（包括 `<script>` 块和解码后的 `text/javascript` Data URL），检测到 `draco_decoder` / `DRACOLoader` 引用时输出专用 warning，给出 CDN 下载地址和所需文件列表。在 `--strict` 模式下这是可恢复 warning，不是致命 error（联网环境功能正常）。

2. **自动下载**：`inline_assets.py --fetch-cdn draco` 在打包前从 `gstatic.com/draco/versioned/decoders/X.X.X/` 下载三个解码器文件到 `<root-dir>/draco/`。版本号优先从 JS 代码中提取，提取不到则用默认 1.5.5。下载失败（无网络/CDN 不可达）会降级为提示，不中断打包。

   ```bash
   python scripts/inline_assets.py out/index.html --css-js-mode tag --fetch-cdn draco
   ```

3. **运行时配合**：工具只负责下载文件，不会改写业务 JS 里的 `DRACOLoader.setDecoderPath` 配置。下载完成后，需要确保应用代码把 loader 路径指向本地 `draco/` 目录，单 HTML 才能真正离线加载模型。

   ```js
   const loader = new DRACOLoader();
   loader.setDecoderPath('draco/');  // 指向 --fetch-cdn 下载的本地目录
   ```

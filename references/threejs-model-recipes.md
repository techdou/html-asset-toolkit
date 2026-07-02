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
- 单文件课程 Demo 中，模型太大时应在页面中加入“模型加载中”的提示。

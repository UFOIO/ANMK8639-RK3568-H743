# Vue 3 + Vite

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Vue - Official](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (previously Volar) and disable Vetur

## 转为模块的注意事项
* common.js
```
export 导出所有全局变量 
export 导出 Logger 对象 
```
* decoder.js
```
import { 所有的变更和对象 } from './common'
import { Module, intArrayFromString } from './libwasm'
Module.onRuntimeInitialized = function() {
	onWasmLoaded();
}
```
* downloader.js
```
import { 所有的变更和对象 } from './common'
import { LoaderHLS } from './loader-hls'
import { LoaderHTTP } from './loader-http'
```
* libwasm.js
```
export 导出 function intArrayFromString方法 
export 导出 var Module对象 
```
* loader-hls.js
```
import { 所有的变更和对象 } from './common'
export 导出 LoaderHLS 对象
```
* loader-http.js
```
import { 所有的变更和对象 } from './common'
export 导出 LoaderHTTP 对象
```
* pcm-player.js
```
export 导出 PCMPlayer 对象
```
* player.js
```
import { 所有的变更和对象 } from './common'
import { WebGLPlayer } from './webgl'
import { PCMPlayer } from './pcm-player'
export 导出所有全局变量 
export 导出 TimerCheck, FileInfo, FunsExtend_Stream, FunExtend_NotStream, Player 对象

// 两处new Worker 参数修改：
this.m_pWorker_Dld = new Worker(new URL("./downloader.js",import.meta.url), {type:"module"});
this.m_pWorker_Dec = new Worker(new URL("./decoder.js",import.meta.url), {type:"module"});
```
* webgl.js
```
export 导出 Texture、WebGLPlayer 对象
```

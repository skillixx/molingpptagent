/** 使用项目真实 Vite 配置提供隔离预览，仅覆盖端口和本地验收 API 地址。 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from '../frontend/node_modules/vite/dist/node/index.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>乐章雅韵 · 本地验收预览</title>
<style>html,body{margin:0;width:100%;height:100%;overflow:hidden}iframe{border:0;width:100%;height:100%}#status{position:fixed;top:0;left:0;background:#172d65;color:white;padding:12px;font:14px sans-serif}</style>
<div id="status">正在载入模板样例…</div><iframe id="editor" src="/editor"></iframe><script>
const frame=document.getElementById('editor');
frame.onload=()=>{const script=frame.contentDocument.createElement('script');script.type='module';script.textContent=
\`import {useSlidesStore} from '/src/store/index.ts';
try {
  const response=await fetch('/api/qa/document');if(!response.ok)throw new Error('样例读取失败');const data=await response.json();
  const deadline=Date.now()+30000;while(!document.querySelector('.viewport-wrapper, .mobile-editor')){if(Date.now()>deadline)throw new Error('编辑器载入超时');await new Promise(r=>setTimeout(r,100));}
  document.querySelector('#app').__vue_app__.runWithContext(()=>{const store=useSlidesStore();store.clearPresentationContext();store.setTitle('乐章雅韵·音乐主题');store.setTheme(data.theme);store.setViewportSize(1000);store.setViewportRatio(0.5625);store.setSlides(data.slides);store.updateSlideIndex(0);});
  parent.document.getElementById('status').remove();
} catch(error){parent.document.getElementById('status').textContent=error.message+'，请刷新重试';}\`;
frame.contentDocument.body.appendChild(script);};</script></html>`;

const server = await createServer({ root: path.join(root, 'frontend'), configFile: path.join(root, 'frontend/vite.config.ts'),
  server: { host: '127.0.0.1', port: 5781, strictPort: true, proxy: {
    '/api': { target: 'http://127.0.0.1:6803', changeOrigin: true, rewrite: value => value.replace(/^\/api/, '') },
    '/enter': { target: 'http://127.0.0.1:6803', changeOrigin: true },
  } }, plugins: [{ name: 'template-29-preview', configureServer(vite) {
    // 独立入口载入固定语义稿；用户保存时仅写入验收 API 的专用 SQLite。
    vite.middlewares.use((req, res, next) => {
      if (req.url?.split('?')[0] !== '/__template29') return next();
      res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.end(html);
    });
  } }] });
await server.listen(); server.printUrls();

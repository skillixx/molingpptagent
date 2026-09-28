// 通过真实编辑器渲染候选页面，先检查视觉，再执行后续编辑和往返验收。
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');
const root = path.resolve('doc/assets/template_30_qa');
const output = path.join(root, 'editor-renders');
fs.mkdirSync(output, {recursive:true});

(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});
  const page=await browser.newPage({viewport:{width:1600,height:1000}});
  const document=JSON.parse(fs.readFileSync(path.join(root,'production-document.json'),'utf8'));
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto('http://127.0.0.1:5792/editor');
    await page.locator('.viewport-wrapper').first().waitFor({timeout:60000});
    await page.evaluate(async data=>{
      const {useSlidesStore}=await import('/src/store/index.ts');
      document.querySelector('#app').__vue_app__.runWithContext(()=>{
        const store=useSlidesStore();window.__neonRenderStore=store;
        store.clearPresentationContext();store.setTitle('蓝紫霓虹科技产品发布');store.setTheme(data.theme);
        store.setViewportSize(1000);store.setViewportRatio(.5625);store.setSlides(data.slides);store.updateSlideIndex(0);
      });
    },document);
    for(let i=0;i<document.slides.length;i++){
      await page.evaluate(index=>window.__neonRenderStore.updateSlideIndex(index),i);
      await page.evaluate(async()=>{await document.fonts.ready;await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
      await page.locator('.viewport-wrapper img').evaluateAll(imgs=>Promise.all(imgs.map(image=>image.decode())));
      await page.locator('.viewport-wrapper').first().screenshot({path:path.join(output,`slide-${String(i+1).padStart(2,'0')}.png`)});
      if(i===0)await page.locator('.viewport-wrapper').first().screenshot({path:path.resolve('backend/main_api/template/template_30.jpg'),type:'jpeg',quality:93});
    }
    if(errors.length)throw new Error(errors.join('\n'));
    // 渲染成功不代表整体验收通过；这一摘要只记录真实编辑器截图已经取得。
    fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({status:'RENDERED',slides:document.slides.length,errors},null,2));
    console.log(JSON.stringify({status:'RENDERED',slides:document.slides.length,output}));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

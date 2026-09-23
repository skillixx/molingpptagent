// 使用真实读取失败的图片验证导出错误反馈，并在同一实例恢复后重试。
const fs=require('node:fs');const path=require('node:path');const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');
const root=path.resolve('doc/assets/template_28_qa');const output=path.join(root,'image-failure-summary.json');
fs.writeFileSync(output,JSON.stringify({status:'RUNNING'}));
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});
  try{
    await page.goto('http://127.0.0.1:5780/editor');await page.locator('.viewport-wrapper').waitFor();
    const document=JSON.parse(fs.readFileSync(path.join(root,'production-document.json'),'utf8'));
    const slide=document.slides.find(s=>s.elements.some(e=>e.imageType==='content'));
    const outcome=await page.evaluate(async({slide,theme})=>{
      const {useSlidesStore}=await import('/src/store/index.ts');const {default:useExport}=await import('/src/hooks/useExport.ts');
      document.querySelector('#app').__vue_app__.runWithContext(()=>{const store=useSlidesStore();window.__imageFailureStore=store;window.__imageFailureExporter=useExport();store.clearPresentationContext();store.setTheme(theme);store.setViewportSize(1000);store.setViewportRatio(.5625);store.setSlides([slide]);store.updateSlideIndex(0);});
      const picture=window.__imageFailureStore.slides[0].elements.find(e=>e.imageType==='content');
      window.__imageFailureOriginal=picture.src;
      window.__imageFailureStore.updateElement({id:picture.id,props:{src:'/api/data/template_28_missing_image.png'}});
      let code='';try{await window.__imageFailureExporter.exportPPTX(window.__imageFailureStore.slides,true,true);}catch(error){code=error.message;}
      return {code,exportingReset:window.__imageFailureExporter.exporting.value===false};
    },{slide,theme:document.theme});
    if(outcome.code!=='PPTX_EXPORT_FAILED'||!outcome.exportingReset)throw new Error(JSON.stringify(outcome));
    await page.getByText('导出失败',{exact:true}).waitFor();await page.screenshot({path:path.join(root,'image-read-failure-feedback.png')});
    await page.evaluate(()=>{const picture=window.__imageFailureStore.slides[0].elements.find(e=>e.imageType==='content');window.__imageFailureStore.updateElement({id:picture.id,props:{src:window.__imageFailureOriginal}});});
    const download=page.waitForEvent('download',{timeout:60000});
    const retry=await page.evaluate(()=>window.__imageFailureExporter.exportPPTX(window.__imageFailureStore.slides,true,true));
    await(await download).saveAs(path.join(root,'image-failure-retry.pptx'));
    if(!retry.localSaved)throw new Error('恢复图片后重试未保存');
    const result={status:'PASS',...outcome,visibleError:true,retrySucceeded:true,sameExporterInstance:true};
    fs.writeFileSync(output,JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  }catch(error){fs.writeFileSync(output,JSON.stringify({status:'FAIL',error:error.stack},null,2));throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

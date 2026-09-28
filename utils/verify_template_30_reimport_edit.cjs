// 专门验证 PPTX 重导入后的继续编辑与换图，补足仅检查解析结果不能证明的操作。
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');
const root=path.resolve('doc/assets/template_30_qa');
const source=path.join(root,'editor-verified/roundtrip.pptx');
const report=path.join(root,'reimport-edit-summary.json');
fs.writeFileSync(report,JSON.stringify({status:'RUNNING'}));

(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  try {
    await page.goto('http://127.0.0.1:5792/editor');await page.locator('.viewport-wrapper').first().waitFor();
    await page.evaluate(async encoded=>{
      const {useSlidesStore}=await import('/src/store/index.ts');
      const {default:useImport}=await import('/src/hooks/useImport.ts');
      const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
      const transfer=new DataTransfer();transfer.items.add(new File([bytes],'roundtrip.pptx'));
      document.querySelector('#app').__vue_app__.runWithContext(()=>{
        const s=useSlidesStore();window.__neonReimport=s;s.clearPresentationContext();
        s.setSlides([{id:'reimport-sentinel',elements:[]}]);s.updateSlideIndex(0);
        useImport().importPPTXFile(transfer.files,{cover:true,fixedViewport:true});
      });
    },fs.readFileSync(source).toString('base64'));
    await page.waitForFunction(()=>window.__neonReimport.slides.length===39&&window.__neonReimport.slides[0].id!=='reimport-sentinel',null,{timeout:60000});
    const title=page.locator('.viewport-wrapper .ProseMirror[contenteditable="true"]').filter({hasText:'霓虹科技编辑验收'}).first();
    await title.click();await page.keyboard.press('Control+A');await page.keyboard.insertText('重导入后继续编辑已验证');await page.keyboard.press('Escape');
    // PPTX 的文字可能重导入为原生形状内文字，两种可编辑载体都应验证。
    await page.waitForFunction(()=>window.__neonReimport.slides[0].elements.some(e=>(e.content||e.text?.content||'').includes('重导入后继续编辑已验证')));
    const expected=JSON.parse(fs.readFileSync(path.join(root,'production-document.json'),'utf8')).slides[4].elements.find(e=>e.imageType==='content');
    const replacement=fs.readFileSync(path.join(root,'fixtures/business-1.jpg')).toString('base64');
    const imageResult=await page.evaluate(async ({frame,encoded})=>{
      const {getImageReplacementProps}=await import('/src/hooks/templateImageProtocol.ts');
      const src=`data:image/jpeg;base64,${encoded}`;
      const dimensions=await new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve({width:im.naturalWidth,height:im.naturalHeight});im.onerror=reject;im.src=src;});
      const store=window.__neonReimport,slide=store.slides[4];
      const picture=slide.elements.find(e=>e.type==='image'&&['left','top','width','height'].every(k=>Math.abs(e[k]-frame[k])<2));
      if(!picture||picture.src===src)throw new Error('未定位到可替换的导入业务图片');
      const otherBefore=JSON.stringify(slide.elements.filter(e=>e.id!==picture.id));
      store.updateElement({id:picture.id,slideId:slide.id,props:getImageReplacementProps(picture,src,dimensions.width,dimensions.height)});
      if(otherBefore!==JSON.stringify(slide.elements.filter(e=>e.id!==picture.id)))throw new Error('重导入换图改变了机身或其他元素');
      store.updateSlideIndex(4);
      return {imageReplaced:slide.elements.find(e=>e.id===picture.id).src===src,otherElementsUnchanged:true};
    },{frame:expected,encoded:replacement});
    await page.screenshot({path:path.join(root,'reimport-continued-edit.png')});
    const download=page.waitForEvent('download',{timeout:60000});
    await page.evaluate(async()=>{
      const {default:useExport}=await import('/src/hooks/useExport.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(()=>useExport().exportPPTX(window.__neonReimport.slides,true,true));
    });
    const edited=path.join(root,'reimport-edited.pptx');await(await download).saveAs(edited);
    const result={status:'PASS',titleEditedByKeyboard:true,...imageResult,reexported:true,slides:39,
      sourceSha256:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),output:edited};
    fs.writeFileSync(report,JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  } catch(error){fs.writeFileSync(report,JSON.stringify({status:'FAIL',error:error.stack},null,2));throw error;}
  finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

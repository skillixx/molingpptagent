// 使用真实编辑器执行模板检查；API 写请求全部阻止，业务样例仅在本地浏览器中保存。
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const input = path.resolve(process.argv[2] || 'doc/assets/template_27_qa/production-document.json');
const output = path.resolve(process.argv[3] || 'doc/assets/template_27_qa/editor-verified');
const templateRoot = path.resolve('backend/main_api/template');
fs.mkdirSync(output, { recursive: true });
// 新运行立即使旧 PASS 失效；即使启动、解析或进程失败也不会误用上次结果。
fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({status:'RUNNING',source:input,startedAt:new Date().toISOString()},null,2));
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');
const template = JSON.parse(fs.readFileSync(input, 'utf8'));

async function inStore(page, operation, data) {
  return page.evaluate(async ({ operation, data }) => {
    const { useSlidesStore } = await import('/src/store/index.ts');
    const { getImageReplacementProps } = await import('/src/hooks/templateImageProtocol.ts');
    return document.querySelector('#app').__vue_app__.runWithContext(() => {
      const store = useSlidesStore();
      window.__template27Store = store;
      if (operation === 'load') {
        store.clearPresentationContext();
        store.setTitle('唯美清新验收'); store.setTheme(data.theme);
        store.setViewportSize(data.width || 1000); store.setViewportRatio(0.5625);
        store.setSlides(data.slides); store.updateSlideIndex(0);
      }
      if (operation === 'index') store.updateSlideIndex(data);
      if (operation === 'edit') {
        const cover = store.slides[0];
        const title = cover.elements.find(e => e.textType === 'title');
        store.updateElement({ id: title.id, slideId: cover.id,
          props: { content: title.content.replace(/>[^<>]+<\/span>/, '>唯美清新编辑验收</span>') } });
        const textPage = store.slides.find(s => (s.templateSlideId || s.id) === 'content-text-4');
        const body = textPage.elements.find(e => e.textType === 'item');
        store.updateElement({ id: body.id, slideId: textPage.id,
          props: { content: body.content.replace(/>[^<>]+<\/span>/, '>正文编辑验收：保留项目内容。</span>') } });
      }
      if (operation === 'replace') {
        const s = store.slides.find(s => s.id === data.slideId);
        const image = s.elements.filter(e => e.imageType === 'content')[data.imageIndex];
        const before = JSON.stringify(s.elements.filter(e => e.imageType === 'decoration'));
        // 调用图片面板实际使用的函数，不在验收脚本中复制裁切算法。
        const props = getImageReplacementProps(image, data.src, data.width, data.height);
        store.updateElement({ id: image.id, slideId: s.id, props });
        const actual = s.elements.find(e => e.id === image.id);
        if (actual.src !== data.src || before !== JSON.stringify(s.elements.filter(e => e.imageType === 'decoration')))
          throw new Error('换图未生效或改变了装饰');
        store.updateSlideIndex(store.slides.indexOf(s));
        return { slideId: data.slideId, imageIndex: data.imageIndex, dimensions: [data.width, data.height], range: actual.clip?.range,
          replacementImplementation: 'getImageReplacementProps', decorationProtected: true };
      }
      return JSON.parse(JSON.stringify(store.slides));
    });
  }, { operation, data });
}

async function ready(page) {
  await page.goto('http://127.0.0.1:5778/editor');
  await page.locator('.viewport-wrapper').first().waitFor({ timeout: 60000 });
}

async function capture(page, name) {
  await page.evaluate(() => document.fonts.ready);
  await page.locator('.viewport-wrapper img, .mobile-thumbnails img').evaluateAll(imgs => Promise.all(imgs.map(i => i.decode())));
  await page.screenshot({ path: path.join(output, name) });
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, acceptDownloads: true });
  const errors = [], writes = [];
  context.on('page', p => p.on('pageerror', err => errors.push(err.message)));
  await context.route('**/*', route => {
    const req = route.request(), url = new URL(req.url());
    if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
    if (url.origin !== 'http://127.0.0.1:5778') return route.abort();
    if (req.method() !== 'GET') { writes.push(req.method()+' '+url.pathname); return route.abort(); }
    if (url.pathname === '/api/auth/me') return route.fulfill({ json: { user_id: 1, app_id: 1, product_id: 1 } });
    if (url.pathname.startsWith('/api/data/')) {
      const file = path.join(templateRoot, path.basename(url.pathname));
      return fs.existsSync(file) ? route.fulfill({ body: fs.readFileSync(file), contentType: file.endsWith('.png') ? 'image/png' : 'image/jpeg' }) : route.fulfill({ status: 404 });
    }
    if (url.pathname.startsWith('/api/')) return route.fulfill({ status: 404, json: { code: 'QA_ONLY' } });
    return route.continue();
  });
  try {
    const page = await context.newPage(); await ready(page); await inStore(page, 'load', template);
    for (let i=0;i<template.slides.length;i++) {
      await inStore(page, 'index', i); await capture(page, `slide-${i+1}.png`);
      await page.locator('.viewport-wrapper').first().screenshot({path:path.join(output,`canvas-${i+1}.png`)});
      if(i===0) await page.locator('.viewport-wrapper').first().screenshot({path:path.join(output,'cover.jpg'),type:'jpeg',quality:90});
    }
    // 交付样例在编辑破坏性测试之前导出，避免把验收哨兵文字作为正式样例。
    const cleanDownload = page.waitForEvent('download', {timeout:60000});
    await page.evaluate(async () => {
      const {useSlidesStore} = await import('/src/store/index.ts');
      const {default:useExport} = await import('/src/hooks/useExport.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => useExport().exportPPTX(useSlidesStore().slides,true,true));
    });
    await (await cleanDownload).saveAs(path.join(output, 'weimei-21-layouts.pptx'));
    // 使用真实可编辑控件输入，证明用户可以改标题及独立单位，而不只依赖 store 写入。
    await inStore(page, 'index', 0);
    const titleEditor = page.locator('.viewport-wrapper .ProseMirror[contenteditable="true"]').filter({hasText:'蓝紫光斑·唯美清新'}).first();
    await titleEditor.click(); await page.keyboard.press('Control+A'); await page.keyboard.insertText('唯美清新编辑验收');
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => window.__template27Store.slides[0].elements.some(e => e.textType === 'title' && e.content.includes('唯美清新编辑验收')));
    const metricIndex = template.slides.findIndex(s => (s.templateSlideId || s.id) === 'content-metrics-4');
    await inStore(page, 'index', metricIndex);
    const unitEditor = page.locator('.viewport-wrapper .ProseMirror[contenteditable="true"]').filter({hasText:/^%$/}).first();
    await unitEditor.click(); await page.keyboard.press('Control+A'); await page.keyboard.insertText('百分比');
    await page.keyboard.press('Escape');
    await page.waitForFunction(index => window.__template27Store.slides[index].elements.some(e => e.textType === 'itemUnit' && e.content.includes('百分比')), metricIndex);
    const uiEdits = await page.evaluate(index => {
      const page = window.__template27Store.slides[index];
      return {titleEditedByKeyboard:true,unitEditedByKeyboard:page.elements.some(e=>e.textType==='itemUnit'&&e.content.includes('百分比')),
        metricValueUnchanged:page.elements.find(e=>e.textType==='itemNumber').content.includes('96')};
    },metricIndex);
    if(!uiEdits.metricValueUnchanged) throw new Error('编辑单位改变了独立指标数值');
    await capture(page,'unit-keyboard-edit.png');
    const valueEditor = page.locator('.viewport-wrapper .ProseMirror[contenteditable="true"]').filter({hasText:/^96$/}).first();
    await valueEditor.click(); await page.keyboard.press('Control+A'); await page.keyboard.insertText('128'); await page.keyboard.press('Escape');
    await page.waitForFunction(index=>window.__template27Store.slides[index].elements.some(e=>e.textType==='itemNumber'&&e.content.includes('128')),metricIndex);
    uiEdits.metricValueEditedByKeyboard = true;
    for (const [identity, before, after] of [['content-process-4','明确项目目标','需求确认（已编辑）'],['content-timeline-5','第1周·调研','第1周·需求复核']]) {
      const index=template.slides.findIndex(s=>(s.templateSlideId||s.id)===identity); await inStore(page,'index',index);
      const editor=page.locator('.viewport-wrapper .ProseMirror[contenteditable="true"]').filter({hasText:before}).first();
      await editor.click();await page.keyboard.press('Control+A');await page.keyboard.insertText(after);await page.keyboard.press('Escape');
      await page.waitForFunction(({index,after})=>window.__template27Store.slides[index].elements.some(e=>e.textType==='itemTitle'&&e.content.includes(after)),{index,after});
      uiEdits[`${identity}EditedByKeyboard`]=true;
    }
    await inStore(page, 'edit');
    const sharp = require(process.env.SHARP_PACKAGE_PATH || 'sharp');
    const replacementResults = [];
    for (const slide of template.slides.filter(s => s.elements.some(e => e.imageType === 'content'))) {
      for (const [width,height] of [[1200,800],[800,1200],[1000,1000]]) {
        // 从已生成背景机械裁切测试图片，不生成额外业务图或调用模型。
        const bytes = await sharp(path.join(templateRoot, 'template_27_asset_bg_cover_v1.jpg')).resize(width,height,{fit:'cover'}).jpeg().toBuffer();
        for(let imageIndex=0;imageIndex<slide.elements.filter(e=>e.imageType==='content').length;imageIndex++) {
          replacementResults.push(await inStore(page, 'replace', {slideId:slide.id,imageIndex,src:`data:image/jpeg;base64,${bytes.toString('base64')}`,width,height}));
        }
        await capture(page, `replacement-${slide.id}-${width}x${height}.png`);
      }
    }
    // 恢复横竖裁切测试图，再在独立编辑验收稿保留一张实际更换的业务图片。
    for (const slide of template.slides.filter(s => s.elements.some(e => e.imageType === 'content'))) {
      const pictures = slide.elements.filter(e => e.imageType === 'content');
      for (let imageIndex = 0; imageIndex < pictures.length; imageIndex++) {
        const source = pictures[imageIndex].src;
        const sourceDimensions = await page.evaluate(src => new Promise((resolve, reject) => {
          const image = new Image(); image.onload = () => resolve({width:image.naturalWidth,height:image.naturalHeight});
          image.onerror = () => reject(new Error('业务样例图片无法解码')); image.src = src;
        }),source);
        await inStore(page,'replace',{slideId:slide.id,imageIndex,src:source,...sourceDimensions});
      }
    }
    const editedPictureSlide=template.slides.find(s=>s.elements.some(e=>e.imageType==='content'));
    const editedPictureSrc=`data:image/jpeg;base64,${fs.readFileSync(path.resolve('doc/assets/template_27_qa/fixtures/business-2.jpg')).toString('base64')}`;
    await inStore(page,'replace',{slideId:editedPictureSlide.id,imageIndex:0,src:editedPictureSrc,width:700,height:1000});
    if(editedPictureSrc===editedPictureSlide.elements.find(e=>e.imageType==='content').src)throw new Error('保存样例没有实际更换图片');
    uiEdits.imageReplacementRetainedForSave=true;
    const viewports=[];
    for(const [width,height] of [[1920,1080],[1366,768],[768,1024],[390,844]]) {
      await page.setViewportSize({width,height}); await inStore(page,'index',0);
      await capture(page,`viewport-${width}x${height}.png`);
      // 手机切换到项目已有的预览列表，不再渲染桌面画布；按实际界面检查首张预览。
      const mobile=await page.locator('.mobile-editor').count()>0;
      const box=await page.locator(mobile?'.mobile-thumbnails .thumbnail-slide':'.viewport-wrapper').first().boundingBox();
      const controls=mobile?await page.locator('.mobile-back-btn, .mobile-download-btn').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {text:n.textContent.trim(),visible:r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight,disabled:n.disabled};})):[];
      viewports.push({width,height,mode:mobile?'mobile-preview':'desktop-editor',canvas:box,controls,withinViewport:!!box&&box.x>=-1&&box.y>=-1&&box.x+box.width<=width+1&&box.y+box.height<=height+1});
      if(mobile) {
        const mobileDownload=page.waitForEvent('download',{timeout:60000});
        await page.locator('.mobile-download-btn').click();
        await (await mobileDownload).saveAs(path.join(output,'mobile-download.pptx'));
        if(controls.length!==2||controls.some(c=>!c.visible||c.disabled))throw new Error('手机操作入口不可用');
      }
    }
    await page.setViewportSize({width:1920,height:1080});
    const expected = await inStore(page, 'snapshot');
    const download = page.waitForEvent('download');
    await page.evaluate(async () => {
      const {default: useExport} = await import('/src/hooks/useExport.ts');
      document.querySelector('#app').__vue_app__.runWithContext(() => useExport().exportJSON());
    });
    const jsonPath = path.join(output,'edited.json'); await (await download).saveAs(jsonPath);
    await page.close();
    // 新页面使用真实 JSON 导入器；与保存前完整 slides 比较，不能仅检查页数。
    const reopened = await context.newPage(); await ready(reopened);
    await reopened.evaluate(async raw => {
      const {default: useImport} = await import('/src/hooks/useImport.ts');
      const {useSlidesStore} = await import('/src/store/index.ts');
      const transfer = new DataTransfer(); transfer.items.add(new File([raw],'edited.json',{type:'application/json'}));
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        // 用独立哨兵证明异步导入确实完成，不能等待初始界面已存在的文字。
        window.__template27Store = useSlidesStore();
        window.__template27Store.setSlides([{id:'json-import-sentinel',elements:[],background:{type:'solid',color:'#FFFFFF'}}]);
        window.__template27Store.updateSlideIndex(0);
        useImport().importJSON(transfer.files,true);
      });
    },fs.readFileSync(jsonPath,'utf8'));
    await reopened.waitForFunction(count => window.__template27Store.slides.length === count
      && window.__template27Store.slides[0]?.id !== 'json-import-sentinel', expected.length, {timeout:60000});
    const reloaded = await inStore(reopened,'snapshot');
    if (JSON.stringify(expected)!==JSON.stringify(reloaded)) throw new Error('JSON 保存重载改变了页面数据');
    // 在当前浏览器临时注入 PPTX 写出失败，验证错误提示及恢复，再使用真实写出重试。
    const exportFailure = await reopened.evaluate(async () => {
      const servedSource = await (await fetch('/src/hooks/useExport.ts')).text();
      const dependency = servedSource.match(/from\s+["']([^"']*pptxgenjs[^"']*)["']/);
      if (!dependency) throw new Error('未找到实际导出依赖');
      const {default:PptxGen} = await import(dependency[1]);
      const {useSlidesStore} = await import('/src/store/index.ts');
      const {default:useExport} = await import('/src/hooks/useExport.ts');
      const original = PptxGen.prototype.write;
      const exporter = document.querySelector('#app').__vue_app__.runWithContext(() => useExport());
      const slides = document.querySelector('#app').__vue_app__.runWithContext(() => useSlidesStore().slides);
      let errorCode='';
      try {
        PptxGen.prototype.write = async () => { throw new Error('QA_INJECTED_WRITE_FAILURE'); };
        await exporter.exportPPTX(slides,true,true);
      } catch(error) { errorCode=error.message; }
      finally { PptxGen.prototype.write=original; }
      return {errorCode,exportingReset:exporter.exporting.value===false};
    });
    if(exportFailure.errorCode!=='PPTX_EXPORT_FAILED'||!exportFailure.exportingReset) throw new Error('导出失败未正确反馈或重置');
    await reopened.waitForFunction(() => document.body.innerText.includes('导出失败'));
    await capture(reopened,'export-failure-feedback.png');
    const pptxDownload = reopened.waitForEvent('download',{timeout:60000});
    await reopened.evaluate(async () => {
      const {useSlidesStore} = await import('/src/store/index.ts');
      const {default:useExport} = await import('/src/hooks/useExport.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => useExport().exportPPTX(useSlidesStore().slides,true,true));
    });
    const pptxPath=path.join(output,'roundtrip.pptx'); await (await pptxDownload).saveAs(pptxPath);
    await reopened.evaluate(async encoded => {
      const {useSlidesStore} = await import('/src/store/index.ts');
      const {default:useImport} = await import('/src/hooks/useImport.ts');
      // Base64 作为单个字符串传输，避免大 PPTX 展开为数千万个数值导致 Node 堆耗尽。
      const bytes = Uint8Array.from(atob(encoded), character => character.charCodeAt(0));
      const transfer = new DataTransfer(); transfer.items.add(new File([bytes],'roundtrip.pptx'));
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        // 编辑器依赖当前页；空数组会让视图崩溃，使用一张临时空白页等待替换。
        useSlidesStore().setSlides([{id:'roundtrip-import-sentinel',elements:[],background:{type:'solid',color:'#FFFFFF'}}]);
        useSlidesStore().updateSlideIndex(0);
        window.__template27Store = useSlidesStore();
        useImport().importPPTXFile(transfer.files,{cover:true,fixedViewport:true});
      });
    }, fs.readFileSync(pptxPath).toString('base64'));
    await reopened.waitForFunction(count => window.__template27Store.slides.length === count
      && window.__template27Store.slides[0]?.id !== 'roundtrip-import-sentinel', expected.length, {timeout:90000});
    const actual = await inStore(reopened,'snapshot');
    fs.writeFileSync(path.join(output,'roundtrip-state.json'),JSON.stringify({expected,actual},null,2));
    const text = html => String(html||'').replace(/<[^>]*>/g,'').replace(/&nbsp;/g,' ').replace(/\s+/g,'').trim();
    const missing=[], imageGeometry=[], nativeGeometry=[];
    for(let i=0;i<expected.length;i++) {
      const joined=actual[i].elements.map(e=>text(e.content||e.text?.content)).join('|');
      for(const e of expected[i].elements) {
        const value=text(e.content||e.text?.content);
        if(value&&!joined.includes(value)) missing.push({slide:i+1,text:value});
      }
      // 原生线和节点也必须保留，不能只凭文字与图片数量给出往返 PASS。
      for(const element of expected[i].elements.filter(e=>e.type==='line'||e.type==='shape')) {
        const near=(a,b)=>Math.abs(a-b)<2;
        const restored=actual[i].elements.find(e=>e.type===element.type&&near(e.left,element.left)&&near(e.top,element.top)&&
          (element.type==='line'?near(e.end[0]-e.start[0],element.end[0]-element.start[0])&&near(e.end[1]-e.start[1],element.end[1]-element.start[1]):near(e.width,element.width)&&near(e.height,element.height)));
        if(!restored)throw new Error(`第${i+1}页原生${element.type}类型或几何丢失：${element.id}`);
        nativeGeometry.push({slide:i+1,type:element.type,id:element.id,restoredType:restored.type});
      }
      if(actual[i].elements.filter(e=>e.type==='image').length!==expected[i].elements.filter(e=>e.type==='image').length)
        throw new Error(`PPTX 第 ${i+1} 页图片数量变化`);
      for(const image of expected[i].elements.filter(e=>e.imageType==='content')) {
        const restored=actual[i].elements.find(e=>e.type==='image' && ['left','top','width','height'].every(k=>Math.abs(e[k]-image[k])<2));
        if(!restored) throw new Error(`第 ${i+1} 页业务图片几何位置未保留`);
        imageGeometry.push({slide:i+1,before:[image.left,image.top,image.width,image.height],after:[restored.left,restored.top,restored.width,restored.height]});
        await inStore(reopened,'index',i);await capture(reopened,`reimported-image-${i+1}.png`);
      }
    }
    if(missing.length) throw new Error(`PPTX 文本丢失: ${JSON.stringify(missing)}`);
    await inStore(reopened,'index',0); await capture(reopened,'reimported-cover.png');
    if(errors.length||writes.length) throw new Error(JSON.stringify({errors,writes}));
    if(viewports.some(v=>!v.withinViewport)) throw new Error(`编辑画布超出视口：${JSON.stringify(viewports)}`);
    fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({status:'PASS',templateId:'template_27',stage:template.metadata?.buildStage || 'worker-output',slideCount:expected.length,uiEdits,jsonFullStateEqual:true,pptxEditorReimport:true,exportFailure,exportRetrySucceeded:true,missingTexts:missing,imageGeometry,nativeGeometry,replacementResults,viewports,errors,writes,source:input,sourceSha256:crypto.createHash('sha256').update(fs.readFileSync(input)).digest('hex'),pptxSha256:crypto.createHash('sha256').update(fs.readFileSync(pptxPath)).digest('hex')},null,2));
    console.log(JSON.stringify({status:'PASS',output,slides:expected.length}));
  } catch(error) {
    const failure=JSON.stringify({status:'FAIL',error:error.stack,errors,writes},null,2);
    fs.writeFileSync(path.join(output,'failure.json'),failure);
    fs.writeFileSync(path.join(output,'summary.json'),failure);
    throw error;
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});

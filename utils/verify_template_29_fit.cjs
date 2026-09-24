// 在真实编辑器检查固定长文本的显示边界，并验证供用户查看的隔离预览入口。
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');
const root = path.resolve('doc/assets/template_29_qa');
const target = path.join(root, 'fit-summary.json');
fs.writeFileSync(target, JSON.stringify({status:'RUNNING'}));

(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try {
    await page.goto('http://127.0.0.1:5781/__template29');
    const child=page.frameLocator('#editor');
    await child.locator('.viewport-wrapper').waitFor();
    await page.locator('#status').waitFor({state:'detached',timeout:45000});
    const frame=page.frames().find(f=>f.url().endsWith('/editor'));
    const preview=await frame.evaluate(async()=>{
      const {useSlidesStore}=await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(()=>({slides:useSlidesStore().slides.length,title:useSlidesStore().title}));
    });
    if(preview.slides!==18)throw new Error('用户预览未加载完整模板');
    await page.screenshot({path:path.join(root,'runtime/manual-preview.png')});
    const selectors=[];
    for(const [width,height] of [[1920,1080],[1366,768],[768,1024],[390,844]]){
      await page.setViewportSize({width,height});await page.goto('http://127.0.0.1:5781/app');
      const card=page.locator('.template-card').filter({has:page.getByText('乐章雅韵·音乐主题',{exact:true})});
      await card.waitFor({state:'visible'});await card.scrollIntoViewIfNeeded();await card.locator('img').evaluate(i=>i.decode());await card.click();
      const state=await card.evaluate(e=>{const r=e.getBoundingClientRect();return {selected:e.classList.contains('selected'),fits:r.left>=-1&&r.right<=innerWidth+1};});
      if(!state.selected||!state.fits)throw new Error(`模板卡片显示或选择失败：${width}`);
      selectors.push({width,height,...state});await page.screenshot({path:path.join(root,`runtime/selector-${width}.png`)});
    }
    await page.setViewportSize({width:1440,height:1000});await page.goto('http://127.0.0.1:5781/editor');
    await page.locator('.viewport-wrapper').waitFor();
    const documents=JSON.parse(fs.readFileSync(path.join(root,'stress-documents.json'),'utf8'));
    const observations=[];
    for(const entry of documents){
      await page.evaluate(async doc=>{
        const {useSlidesStore}=await import('/src/store/index.ts');
        document.querySelector('#app').__vue_app__.runWithContext(()=>{const s=useSlidesStore();window.__fitStore=s;s.clearPresentationContext();s.setTheme(doc.theme);s.setViewportSize(1000);s.setViewportRatio(.5625);s.setSlides(doc.slides);s.updateSlideIndex(0);});
      },entry.document);
      for(let index=0;index<entry.document.slides.length;index++){
        await page.evaluate(i=>window.__fitStore.updateSlideIndex(i),index);
        // 字体加载和 ResizeObserver 完成后读取实际文字边界，而非只检查声明的高度。
        await page.evaluate(async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});
        const issue=await page.locator('.viewport-wrapper').first().evaluate(view=>{
          const viewport=view.getBoundingClientRect();const boxes=[];const problems=[];
          for(const element of view.querySelectorAll('.editable-element-text')){
            const editor=element.querySelector('.ProseMirror');if(!editor||!editor.textContent.trim())continue;
            const range=document.createRange();range.selectNodeContents(editor);const box=range.getBoundingClientRect();
            const record={text:editor.textContent,x:box.x,y:box.y,w:box.width,h:box.height};boxes.push(record);
            if(box.left<viewport.left-2||box.right>viewport.right+2||box.top<viewport.top-2||box.bottom>viewport.bottom+2)problems.push({kind:'outside-slide',...record});
          }
          for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){
            const a=boxes[i],b=boxes[j];const w=Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x);const h=Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y);
            if(w>2&&h>2)problems.push({kind:'text-overlap',first:a.text,second:b.text,width:w,height:h});
          }
          return {textCount:boxes.length,problems};
        });
        observations.push({case:entry.name,page:index+1,...issue});
        if(issue.problems.length){await page.screenshot({path:path.join(root,`fit-failure-${entry.name}-${index+1}.png`)});throw new Error(JSON.stringify(observations.at(-1)));}
      }
      await page.screenshot({path:path.join(root,`fit-${entry.name}.png`)});
    }
    const blocked=await page.request.post('http://127.0.0.1:5781/api/presentations/generate',{data:{title:'must not generate'}});
    if(blocked.status()!==405)throw new Error('隔离预览未拒绝真实生成操作');
    if(errors.length)throw new Error(JSON.stringify(errors));
    const result={status:'PASS',manualPreview:preview,selectors,stressPages:observations,previewWriteBlocked:true,errors};
    fs.writeFileSync(target,JSON.stringify(result,null,2));console.log(JSON.stringify({status:'PASS',stressPages:observations.length,selectors:selectors.length}));
  }catch(error){fs.writeFileSync(target,JSON.stringify({status:'FAIL',error:error.stack,errors},null,2));throw error;}
  finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});

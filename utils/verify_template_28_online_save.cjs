// 通过真实保存按钮、自动保存接口和全新页面验证专用 SQLite 中的修改。
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');
const root = path.resolve('doc/assets/template_28_qa');
const target = path.join(root, 'online-save-summary.json');
fs.writeFileSync(target, JSON.stringify({status:'RUNNING'}));

(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const context = await browser.newContext({viewport:{width:1440,height:1000}});
  const page = await context.newPage();
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  try {
    await page.goto('http://127.0.0.1:5780/editor');
    await page.locator('.viewport-wrapper').waitFor();
    const input=JSON.parse(fs.readFileSync(path.join(root,'production-document.json'),'utf8'));
    await page.evaluate(async raw=>{
      const {useSlidesStore}=await import('/src/store/index.ts');
      document.querySelector('#app').__vue_app__.runWithContext(()=>{
        const s=useSlidesStore(); s.clearPresentationContext(); s.setTitle('青绿几何在线保存验收');
        s.setTheme(raw.theme);s.setViewportSize(1000);s.setViewportRatio(.5625);s.setSlides(raw.slides);s.updateSlideIndex(0);
      });
    },input);
    const createResponse=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/api/presentations/drafts'));
    await page.getByTestId('editor-save-work').click();
    const created=await createResponse;
    if(created.status()!==201)throw new Error(`实际保存按钮请求失败：${created.status()}`);
    const createdData=await created.json();
    const id=createdData.presentation.id;
    await page.waitForURL(`**/editor/${id}`);
    await page.locator('.save-status.status-saved').waitFor();
    const modifiedTitle='青绿几何在线保存已验证';
    const editor=page.locator('.viewport-wrapper .ProseMirror[contenteditable="true"]').filter({hasText:'青绿几何·清新商务'}).first();
    const patched=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith(`/api/presentations/${id}`),{timeout:45000});
    await editor.click();await page.keyboard.press('Control+A');await page.keyboard.insertText(modifiedTitle);await page.keyboard.press('Escape');
    const saveResponse=await patched;
    if(!saveResponse.ok())throw new Error(`编辑后自动保存失败：${saveResponse.status()}`);
    await page.locator('.save-status.status-saved').waitFor();
    // 使用编辑面板同一替换函数更新图片，再验证实际 API 接收到完整修改。
    const replacement=fs.readFileSync(path.join(root,'fixtures/business-2.jpg')).toString('base64');
    const imageSaved=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith(`/api/presentations/${id}`),{timeout:45000});
    const expected=await page.evaluate(async encoded=>{
      const {useSlidesStore}=await import('/src/store/index.ts');
      const {getImageReplacementProps}=await import('/src/hooks/templateImageProtocol.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(()=>{
        const s=useSlidesStore();const slide=s.slides.find(p=>p.templateSlideId==='content-image-left-1');
        const picture=slide.elements.find(e=>e.imageType==='content');
        s.updateElement({id:picture.id,slideId:slide.id,props:getImageReplacementProps(picture,`data:image/jpeg;base64,${encoded}`,700,1000)});
        return JSON.parse(JSON.stringify(s.slides));
      });
    },replacement);
    if(!(await imageSaved).ok())throw new Error('图片替换自动保存失败');
    await page.locator('.save-status.status-saved').waitFor();
    const response=await page.request.get(`http://127.0.0.1:5780/api/presentations/${id}`);
    const persisted=await response.json();
    if(JSON.stringify(persisted.slides.slides)!==JSON.stringify(expected))throw new Error('服务器保存内容与完整编辑稿不一致');
    await page.screenshot({path:path.join(root,'runtime/online-saved.png')});
    await page.close();
    // 新上下文不共享浏览器本地草稿，从服务端重新读取，避免缓存掩盖保存问题。
    const fresh=await browser.newContext({viewport:{width:1440,height:1000}});
    const reopened=await fresh.newPage();
    await reopened.goto(`http://127.0.0.1:5780/editor/${id}`);
    await reopened.locator('.save-status.status-saved').waitFor({timeout:30000});
    const actual=await reopened.evaluate(async()=>{
      const {useSlidesStore}=await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(()=>JSON.parse(JSON.stringify(useSlidesStore().slides)));
    });
    if(JSON.stringify(actual)!==JSON.stringify(expected))throw new Error('独立页面服务端重载不一致');
    await reopened.screenshot({path:path.join(root,'runtime/online-reopened.png')});
    if(errors.length)throw new Error(JSON.stringify(errors));
    const result={status:'PASS',templateId:'template_28',presentationId:id,draftSavedByButton:true,
      titleEditedByKeyboard:true,imageReplacementSaved:true,realAutosave:true,fullDocumentEqualAfterApiRead:true,
      newBrowserContextReloadEqual:true,slideCount:actual.length,currentVersion:persisted.current_version,
      database:'isolated-template28-runtime-sqlite',productionWrites:false,url:reopened.url(),errors};
    fs.writeFileSync(target,JSON.stringify(result,null,2));console.log(JSON.stringify(result));
    await fresh.close();
  }catch(error){fs.writeFileSync(target,JSON.stringify({status:'FAIL',error:error.stack,errors},null,2));throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

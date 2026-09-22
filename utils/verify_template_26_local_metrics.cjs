// 通过真实编辑器的本地生成接口验证指标协议，不写 API、不调用模型。
const fs = require('node:fs');
const path = require('node:path');
const output = path.resolve(process.argv[2] || 'doc/assets/template_26_qa/ship-local-metrics');
fs.mkdirSync(output, {recursive:true});
fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({status:'RUNNING'}));
const {chromium} = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const errors=[], writes=[];
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/*',route=>{
      const request=route.request(),url=new URL(request.url());
      if(['data:','blob:'].includes(url.protocol))return route.continue();
      if(url.origin!=='http://127.0.0.1:5778')return route.abort();
      if(request.method()!=='GET'){writes.push(request.method()+' '+url.pathname);return route.abort();}
      if(url.pathname==='/api/auth/me')return route.fulfill({json:{user_id:1,app_id:1,product_id:1}});
      return route.continue();
    });
    await page.goto('http://127.0.0.1:5778/editor');
    await page.locator('.viewport-wrapper').first().waitFor();
    const cases=[];
    for(const count of [4,3,13]){
      const result=await page.evaluate(async count=>{
        const {default:useAIPPT}=await import('/src/hooks/useAIPPT.ts');
        const {useSlidesStore}=await import('/src/store/index.ts');
        const template=await(await fetch('/api/data/template_26.json')).json();
        return document.querySelector('#app').__vue_app__.runWithContext(()=>{
          const input={type:'content',data:{title:'本地指标协议检查',layoutKind:'metrics',items:Array.from({length:count},(_,i)=>({title:`指标${i}`,value:i,unit:i?'小时':'',text:`完整说明${i}`}))}};
          const original=JSON.stringify(input);
          const slides=[...useAIPPT().AIPPTGenerator(template.slides,[input])];
          const text=e=>new DOMParser().parseFromString(e.content||'','text/html').body.textContent||'';
          const all=slides.flatMap(s=>s.elements.map(text)).join('\n');
          for(const item of input.data.items)if(!all.includes(item.title)||!all.includes(item.text)||!all.includes(String(item.value)))throw new Error('本地指标内容缺失');
          if(count===4){
            const values=slides[0].elements.filter(e=>e.textType==='itemNumber').map(text);
            const units=slides[0].elements.filter(e=>e.textType==='itemUnit').map(text);
            if(JSON.stringify(values)!==JSON.stringify(['0','1','2','3'])||JSON.stringify(units)!==JSON.stringify(['','小时','小时','小时']))throw new Error('独立指标绑定错误');
          }else for(let i=1;i<count;i++)if(!all.includes(i+'小时'))throw new Error('指标回退丢单位');
          if(JSON.stringify(input)!==original)throw new Error('调用方输入被修改');
          const store=useSlidesStore();store.clearPresentationContext();store.setTheme(template.theme);store.setViewportSize(1000);store.setViewportRatio(0.5625);store.setSlides(slides);store.updateSlideIndex(0);
          return {count,slides:slides.length,contentPreserved:true,inputUnchanged:true};
        });
      },count);
      await page.evaluate(()=>document.fonts.ready);
      await page.locator('.viewport-wrapper img').evaluateAll(images=>Promise.all(images.map(image=>image.decode())));
      await page.locator('.viewport-wrapper').first().screenshot({path:path.join(output,`metrics-${count}.png`)});
      cases.push(result);
    }
    const rejected=await page.evaluate(async()=>{
      const {default:useAIPPT}=await import('/src/hooks/useAIPPT.ts');
      const template=await(await fetch('/api/data/template_26.json')).json();
      return document.querySelector('#app').__vue_app__.runWithContext(()=>{
        try{[...useAIPPT().AIPPTGenerator(template.slides,[{type:'content',images:[{src:'https://example.invalid/business.png'}],data:{title:'带图指标',layoutKind:'metrics',items:[{title:'指标',value:1,unit:'小时',text:'说明'}]}}])];return false;}
        catch(error){return error.message.includes('本地指标生成暂不支持同时包含业务图片');}
      });
    });
    await page.getByText('本地指标生成暂不支持同时包含业务图片，请使用云端生成或将图片拆成独立图文页',{exact:true}).waitFor();
    if(!rejected||errors.length||writes.length)throw new Error(JSON.stringify({rejected,errors,writes}));
    fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({status:'PASS',cases,imageMetricRejectedWithVisibleFeedback:true,errors,writes},null,2));
    console.log(JSON.stringify({status:'PASS',cases:cases.length,visibleErrorFeedback:true}));
  }catch(error){fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({status:'FAIL',error:error.stack},null,2));throw error;}
  finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

// 重放真实 PPTX 导入，检查流程和时间轴连接线是否仍为可见、可编辑的原生线条。
const fs=require('node:fs');const path=require('node:path');const {chromium}=require('playwright');
const root=path.resolve('doc/assets/template_27_qa');const output=path.join(root,'connector-summary.json');
fs.writeFileSync(output,JSON.stringify({status:'RUNNING'}));
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const results=[];
  try{
    await page.goto('http://127.0.0.1:5779/editor');await page.locator('.viewport-wrapper').waitFor();
    await page.evaluate(async encoded=>{
      const {useSlidesStore}=await import('/src/store/index.ts');const {default:useImport}=await import('/src/hooks/useImport.ts');
      const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));const files=new DataTransfer();files.items.add(new File([bytes],'sample.pptx'));
      document.querySelector('#app').__vue_app__.runWithContext(()=>{window.__connectorStore=useSlidesStore();window.__connectorStore.setSlides([{id:'sentinel',elements:[]}]);window.__connectorStore.updateSlideIndex(0);useImport().importPPTXFile(files.files,{cover:true,fixedViewport:true});});
    },fs.readFileSync(path.join(root,'editor-verified/weimei-21-layouts.pptx')).toString('base64'));
    await page.waitForFunction(()=>window.__connectorStore.slides.length===21,null,{timeout:60000});
    for(const [index,minimum] of [[17,4],[18,5]]){
      await page.evaluate(i=>window.__connectorStore.updateSlideIndex(i),index);
      await page.screenshot({path:path.join(root,`reimported-connectors-${index+1}.png`)});
      const data=await page.evaluate(i=>{
        const elements=window.__connectorStore.slides[i].elements;
        return {page:i+1,lines:elements.filter(e=>e.type==='line'),zeroShapes:elements.filter(e=>e.type==='shape'&&(e.width===0||e.height===0))};
      },index);results.push(data);
      if(data.lines.length<minimum)throw new Error(`第${index+1}页原生连接线丢失：应至少${minimum}条，实际${data.lines.length}条；退化图形${data.zeroShapes.length}个`);
      const original=JSON.parse(fs.readFileSync(path.join(root,'production-document.json'),'utf8')).slides[index];
      const shapeCount=await page.evaluate(i=>window.__connectorStore.slides[i].elements.filter(e=>e.type==='shape'&&e.width>1&&e.height>1).length,index);
      if(shapeCount<original.elements.filter(e=>e.type==='shape').length)throw new Error('流程或时间轴的可编辑节点缺失');
      const connector=data.lines[1];const canvas=await page.locator('.viewport-wrapper').first().boundingBox();
      await page.mouse.click(canvas.x+(connector.left+(connector.start[0]+connector.end[0])/2)*canvas.width/1000,
        canvas.y+(connector.top+(connector.start[1]+connector.end[1])/2)*canvas.height/562.5);
      await page.keyboard.press('ArrowDown');
      await page.waitForFunction(({index,id,top})=>window.__connectorStore.slides[index].elements.find(e=>e.id===id)?.top>top,{index,id:connector.id,top:connector.top});
      data.nativeNodeCount=shapeCount;data.connectorMovedByKeyboard=true;
      await page.screenshot({path:path.join(root,`edited-reimported-connectors-${index+1}.png`)});
    }
    fs.writeFileSync(output,JSON.stringify({status:'PASS',results},null,2));console.log(JSON.stringify({status:'PASS',counts:results.map(x=>x.lines.length)}));
  }catch(error){fs.writeFileSync(output,JSON.stringify({status:'FAIL',error:error.message,results},null,2));throw error;}
  finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});

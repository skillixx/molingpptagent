#!/usr/bin/env node
/** 蓝黑城市融资路演：构建原生可编辑版式，背景只承担固定装饰。 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const C = { bg: '#080B10', navy: '#101B2C', blue: '#1263A5', cyan: '#4CBDE3', white: '#F5F7FA', body: '#C3CBD6', rule: '#657286' };
const ASSETS = {
  cover: 'template_25_asset_bg_city_cover_v1.jpg',
  contents: 'template_25_asset_bg_nebula_contents_v1.jpg',
  building: 'template_25_asset_bg_building_section_v1.jpg',
  meeting: 'template_25_asset_bg_meeting_section_v1.jpg',
  end: 'template_25_asset_bg_city_end_v1.jpg',
};
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const rect = 'M 0 0 L 200 0 L 200 200 L 0 200 Z';
const diamond = 'M 100 0 L 200 100 L 100 200 L 0 100 Z';
const arrow = 'M 0 0 L 150 0 L 200 100 L 150 200 L 0 200 L 50 100 Z';
const slide = (id, type, options = {}) => ({ id, type, background: { type: 'solid', color: C.bg }, elements: [], ...options });
function add(s, role, type, props) {
  const e = { type, id: `t25-${s.id}-${role}-${s.elements.length + 1}`, rotate: 0, ...props };
  s.elements.push(e); return e;
}
function text(s, role, value, x, y, w, h, slot, opts = {}) {
  const { size = 20, min = 16, color = C.body, align = 'left', bold = false, groupId, font = '微软雅黑' } = opts;
  return add(s, role, 'text', {
    left: x, top: y, width: w, height: h, defaultFontName: font, defaultColor: color,
    // 当前导出器按“冒号＋空格”解析样式，字重使用它支持的 bold/normal，保证往返一致。
    content: `<p style="text-align: ${align};"><span style="font-family: ${font};font-size: ${size}px;color: ${color};font-weight: ${bold ? 'bold' : 'normal'};line-height: 1.3;">${escape(value)}</span></p>`,
    textLineHeight: 1.3, minimumFontSize: min,
    ...(slot ? { textType: slot } : {}), ...(groupId ? { groupId } : {}),
  });
}
function shape(s, role, x, y, w, h, fill = C.blue, opts = {}) {
  return add(s, role, 'shape', {
    left: x, top: y, width: w, height: h, viewBox: [200, 200], path: opts.path || rect,
    fill, fixedRatio: false, outline: { color: opts.stroke || fill, width: opts.strokeWidth || 0, style: 'solid' },
    ...(opts.opacity !== undefined ? { opacity: opts.opacity } : {}),
    ...(opts.groupId ? { groupId: opts.groupId } : {}),
  });
}
function rule(s, role, x, y, width, color = C.rule, groupId, dy = 0) {
  return add(s, role, 'line', { left: x, top: y, start: [0, 0], end: [width, dy], points: ['', ''], width: 1.5, color, style: 'solid', ...(groupId ? { groupId } : {}) });
}
function image(s, role, asset, x, y, w, h, groupId) {
  return add(s, role, 'image', {
    left: x, top: y, width: w, height: h, src: `/api/data/${asset}`, fixedRatio: false,
    imageType: groupId ? 'content' : 'decoration',
    ...(groupId ? { groupId, strictImageCount: true, requireSourceDimensions: true, clip: { shape: 'rect', range: [[0, 0], [100, 100]] } } : { lock: true }),
  });
}
function background(s, asset) { image(s, 'background', asset, 0, 0, 1000, 562.5); }
function header(s, value = '项目关键内容') {
  text(s, 'title', value, 48, 28, 904, 94, 'title', { size: 30, min: 24, color: C.cyan, bold: true });
  rule(s, 'header-rule', 48, 127, 904);
}
function item(s, index, x, y, w, bodyHeight, opts = {}) {
  const groupId = opts.groupId || `${s.id}-item-${index + 1}`;
  text(s, 'item-title', `内容要点${index + 1}`, x, y, w, opts.titleHeight || 56, 'itemTitle', { size: opts.titleSize || 22, min: 18, color: C.white, bold: true, groupId, align: opts.align });
  text(s, 'item-body', '完整展示项目内容，保留业务背景、具体行动与必要说明。', x, y + (opts.bodyOffset || 64), w, bodyHeight, 'item', { size: opts.bodySize || 18, min: 16, groupId, align: opts.align });
}
function cover(long = false) {
  const s = slide(long ? 'cover-city-long-title' : 'cover-city', 'cover', {
    variantKey: long ? 'long-title' : 'city', fitTitleBeforeVariant: true,
    titleFitLimits: { maxWide: long ? 40 : 24, maxAscii: long ? 78 : 48, singleWide: long ? 20 : 12, singleAscii: long ? 39 : 24 },
  });
  background(s, ASSETS.cover);
  shape(s, 'contrast-wash', 0, 0, 1000, 562.5, C.bg, { opacity: 0.25 });
  rule(s, 'top-line', 390, 125, 220, C.white);
  text(s, 'title', long ? '让复杂商业价值获得清晰完整的表达' : '商业创业计划书', 96, 165, 808, 158, 'title', { size: long ? 42 : 52, min: 36, color: C.white, bold: true, align: 'center' });
  text(s, 'subtitle', '项目愿景、商业路径与合作机会', 170, 344, 660, 94, 'content', { size: 22, min: 16, color: C.white, align: 'center' });
  return s;
}
function contents(count) {
  const s = slide(`contents-${count}`, 'contents'); background(s, ASSETS.contents);
  shape(s, 'contrast-wash', 0, 0, 1000, 562.5, C.bg, { opacity: 0.28 });
  text(s, 'heading', '目录', 385, 40, 230, 70, null, { size: 34, color: C.white, align: 'center', bold: true });
  for (let i = 0; i < count; i++) {
    const x = 70 + (i % 2) * 470, y = 153 + Math.floor(i / 2) * 122, groupId = `${s.id}-item-${i + 1}`;
    shape(s, 'number-diamond', x, y + 1, 66, 66, C.navy, { path: diamond, stroke: C.white, strokeWidth: 1.5, groupId });
    text(s, 'number', String(i + 1).padStart(2, '0'), x + 10, y + 9, 46, 48, 'itemNumber', { size: 22, color: C.cyan, align: 'center', groupId, font: 'Arial' });
    text(s, 'item', `目录主题${i + 1}`, x + 90, y, 290, 83, 'item', { size: 22, color: C.white, min: 18, groupId });
  }
  return s;
}
function transition(meeting = false) {
  const s = slide(meeting ? 'transition-meeting' : 'transition-building', 'transition', {
    variantKey: meeting ? 'meeting' : 'building', variantAliases: meeting ? ['spectrum', 'stage'] : ['horizon', 'particle'],
  });
  background(s, meeting ? ASSETS.meeting : ASSETS.building);
  // 双层菱形保持原生形状，章节文字始终独立可编辑。
  shape(s, 'outer-diamond', 284, 65, 432, 432, C.white, { path: diamond });
  shape(s, 'inner-diamond', 294, 75, 412, 412, C.bg, { path: diamond });
  text(s, 'number', '01', 420, 136, 160, 100, 'partNumber', { size: 68, min: 48, align: 'center', color: C.white, font: 'Arial', bold: true });
  rule(s, 'number-rule', 385, 245, 230, C.white);
  text(s, 'title', '项目概况', 345, 260, 310, 90, 'title', { size: 32, min: 24, color: C.white, align: 'center', bold: true });
  text(s, 'content', '章节导语', 385, 350, 230, 68, 'content', { size: 18, min: 16, align: 'center' });
  return s;
}
function textPage(count) {
  const s = slide(`content-text-${count}`, 'content', { allowedItemCounts: [count] }); header(s);
  const layout = {1:[100,180,800,220,1,0,0],2:[58,180,414,215,2,470,0],3:[48,176,278,230,3,313,0],4:[58,153,418,110,2,468,192]}[count];
  const [x,y,w,h,cols,dx,dy] = layout;
  for (let i=0;i<count;i++) {
    const left=x+(i%cols)*dx, top=y+Math.floor(i/cols)*dy, groupId=`${s.id}-item-${i+1}`;
    rule(s,'item-accent',left,top-10,54,C.cyan,groupId);
    item(s,i,left,top,w,h,{groupId,bodySize:count>=3?16:20,titleSize:count===1?28:22,bodyOffset:64});
  }
  return s;
}
function imagePage(count, topImage = false) {
  const id=count===1?(topImage?'content-image-top-1':'content-image-left-1'):`content-image-${count}`;
  const s=slide(id,'content',{allowedItemCounts:[count],...(count===1?{variantKey:topImage?'top':'left'}:{})}); header(s,'业务图文');
  for(let i=0;i<count;i++) {
    const groupId=`${id}-item-${i+1}`;
    if(count===1&&!topImage) {
      image(s,'business-image',ASSETS.cover,48,159,446,338,groupId);
      item(s,i,542,175,410,210,{groupId,bodyOffset:90,titleHeight:78,bodySize:20});
    } else if(count===1) {
      image(s,'business-image',ASSETS.cover,48,146,904,184,groupId);
      item(s,i,64,350,872,104,{groupId,bodyOffset:63,bodySize:20});
    } else {
      const gap=24, w=(904-gap*(count-1))/count, x=48+i*(w+gap), ih=count===2?200:count===3?180:152;
      image(s,'business-image',ASSETS.cover,x,154,w,ih,groupId);
      item(s,i,x,154+ih+18,w, count===2?92:count===3?110:138,{groupId,bodyOffset:63,titleSize:20,bodySize:16});
    }
  }
  return s;
}
function special(kind,count) {
  const s=slide(`content-${kind}-${count}`,'content',{allowedItemCounts:[count],layoutKind:kind,...(kind==='metrics'?{metricValueField:'value'}:{})});
  header(s,{process:'实施路径',timeline:'发展里程碑',metrics:'关键指标',compare:'方案对比'}[kind]);
  for(let i=0;i<count;i++) {
    const groupId=`${s.id}-item-${i+1}`;
    if(kind==='timeline') {
      const y=154+i*123;
      if(i<2)rule(s,'timeline',108,y+38,0,C.rule,undefined,123);
      shape(s,'node',93,y+14,30,30,C.blue,{path:diamond,groupId});
      item(s,i,174,y,730,58,{groupId,titleSize:22,bodyOffset:55,bodySize:18});
    } else if(kind==='metrics') {
      const x=58+(i%2)*470,y=155+Math.floor(i/2)*184;
      text(s,'value',`${(i+1)*20}%`,x,y,160,75,'itemNumber',{size:40,min:24,color:C.cyan,bold:true,font:'Arial',groupId});
      item(s,i,x+184,y+2,234,92,{groupId,titleSize:20,bodySize:16,bodyOffset:58});
      rule(s,'metric-rule',x,y+159,414,C.rule,groupId);
    } else if(kind==='process') {
      const x=48+i*232;
      shape(s,'step-arrow',x,170,208,94,C.blue,{path:arrow,groupId});
      text(s,'step-number',String(i+1).padStart(2,'0'),x+50,185,105,60,'itemNumber',{size:30,min:22,color:C.white,align:'center',font:'Arial',groupId});
      item(s,i,x,295,208,151,{groupId,titleSize:20,bodySize:16,bodyOffset:64});
    } else {
      const x=58+i*470;
      shape(s,'compare-band',x,167,414,5,i?C.cyan:C.blue,{groupId});
      item(s,i,x+10,194,394,211,{groupId,titleSize:26,bodySize:20,bodyOffset:87,titleHeight:74});
    }
  }
  return s;
}
function end(contact=false) {
  const s=slide(contact?'end-contact':'end-thanks','end',{variantKey:contact?'contact':'thanks',preserveEndItemBody:contact});
  background(s,ASSETS.end);
  shape(s,'contrast-wash',0,0,1000,562.5,C.bg,{opacity:0.32});
  text(s,'title',contact?'期待与您携手前行':'感谢观看',120,contact?62:160,760,120,'title',{size:48,min:34,color:C.white,align:'center',bold:true});
  text(s,'content',contact?'合作诉求与联系信息':'期待交流，共创价值',160,contact?183:305,680,85,'content',{size:22,min:16,color:C.white,align:'center'});
  if(contact)for(let i=0;i<3;i++)text(s,'contact-item',`联系信息${i+1}`,170,280+i*76,660,70,'item',{size:18,min:16,color:C.white,align:'center',groupId:`${s.id}-item-${i+1}`});
  return s;
}
export function build() {
  const slides=[cover(),cover(true),...[2,3,4,5,6].map(contents),transition(),transition(true),...[1,2,3,4].map(textPage),imagePage(1),imagePage(1,true),imagePage(2),imagePage(3),imagePage(4),special('process',4),special('timeline',3),special('metrics',4),special('compare',2),end(),end(true)];
  return {id:'template_25',title:'蓝黑城市·融资路演',width:1000,height:562.5,supportsLosslessContentPagination:true,unsupportedLayoutPolicy:'ordinary',sourceImageCountPolicy:'one-per-item',
    theme:{themeColors:[C.blue,C.cyan,C.navy],fontColor:C.body,fontName:'微软雅黑',backgroundColor:C.bg},
    metadata:{buildStage:'production',sourceReference:'融资路演(1).ppt',assetGeneration:'GPT2 图片模板；实际模型以素材记录为准',assetFiles:Object.values(ASSETS),productionSlideIds:slides.map(s=>s.id)},slides};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const output=path.resolve(process.argv[2]||path.join(ROOT,'backend/main_api/template/template_25.json'));
  fs.mkdirSync(path.dirname(output),{recursive:true}); fs.writeFileSync(output,JSON.stringify(build(),null,2)+'\n','utf8'); console.log(output);
}

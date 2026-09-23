#!/usr/bin/env node
/** 唯美清新模板：六张固定装饰与可编辑业务内容分层，按既定库存生成二十一个版式。 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const C = { background: '#172D65', white: '#FFFFFF', body: '#E6EBFF', lavender: '#C9D3FF', cyan: '#B8E8FF', panel: '#30477B', rule: '#7088BF' };
export const ASSETS = Object.fromEntries(Object.entries({ cover: 'bg_cover_v1.jpg', content: 'bg_content_v1.jpg',
  section: 'bg_section_v1.jpg', end: 'bg_end_v1.jpg', ring: 'glass_ring_v1.png', glow: 'corner_glow_v1.png',
}).map(([key, name]) => [key, `template_27_asset_${name}`]));
const RECT = 'M 0 0 L 200 0 L 200 200 L 0 200 Z';
const CIRCLE = 'M 100 0 A 100 100 0 1 1 100 200 A 100 100 0 1 1 100 0 Z';
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const slide = (id, type, props = {}) => ({ id, type, elements: [], background: { type: 'solid', color: C.background }, ...props });

function add(s, role, type, props) {
  const e = { type, id: `t27-${s.id}-${role}-${s.elements.length + 1}`, rotate: 0, ...props };
  s.elements.push(e); return e;
}
function text(s, role, value, x, y, w, h, slot, opts = {}) {
  const { size = 18, min = 16, color = C.body, bold = false, align = 'left', font = '微软雅黑', groupId } = opts;
  // 字号、字重、段落对齐使用现有导出器支持的格式，文字始终保留为原生对象。
  return add(s, role, 'text', { left: x, top: y, width: w, height: h, defaultFontName: font, defaultColor: color,
    content: `<p style="text-align: ${align};"><span style="font-family: ${font};font-size: ${size}px;color: ${color};font-weight: ${bold ? 'bold' : 'normal'};line-height: 1.3;">${escape(value)}</span></p>`,
    textLineHeight: 1.3, minimumFontSize: min, ...(slot ? { textType: slot } : {}), ...(groupId ? { groupId } : {}) });
}
function shape(s, role, x, y, w, h, opts = {}) {
  return add(s, role, 'shape', { left: x, top: y, width: w, height: h, viewBox: [200, 200],
    path: opts.circle ? CIRCLE : RECT, fill: opts.fill || C.panel, fixedRatio: false,
    outline: { color: opts.stroke || C.rule, width: opts.strokeWidth ?? 0.7, style: 'solid' },
    ...(opts.circle ? {} : { pathFormula: 'roundRect', keypoints: [0.06] }),
    ...(opts.groupId ? { groupId: opts.groupId } : {}) });
}
function line(s, role, x1, y1, x2, y2, groupId) {
  // 线条使用局部端点，保证导出没有负数宽高。
  const left = Math.min(x1, x2), top = Math.min(y1, y2);
  return add(s, role, 'line', { left, top, start: [x1 - left, y1 - top], end: [x2 - left, y2 - top],
    points: ['', ''], width: 1, color: C.rule, style: 'solid', ...(groupId ? { groupId } : {}) });
}
function image(s, role, asset, x, y, w, h, groupId) {
  return add(s, role, 'image', { left: x, top: y, width: w, height: h, src: `/api/data/${asset}`, fixedRatio: false,
    imageType: groupId ? 'content' : 'decoration',
    ...(groupId ? { groupId, strictImageCount: true, requireSourceDimensions: true,
      clip: { shape: 'rect', range: [[0, 0], [100, 100]] } } : { lock: true }) });
}
function base(s, kind = 'content') { image(s, 'background', ASSETS[kind], 0, 0, 1000, 562.5); }
function header(s, value = '让想法清晰呈现') {
  text(s, 'title', value, 56, 30, 888, 72, 'title', { size: 30, min: 24, color: C.white, bold: true });
  line(s, 'heading-rule', 56, 114, 944, 114);
}
function item(s, index, x, y, w, bodyHeight, opts = {}) {
  const groupId = opts.groupId || `${s.id}-item-${index + 1}`;
  text(s, 'item-title', `项目要点${index + 1}`, x, y, w, opts.titleHeight || 54, 'itemTitle',
    { size: opts.titleSize || 22, min: 16, color: C.white, bold: true, groupId });
  text(s, 'item-body', '聚焦真实需求，明确行动安排，让每一项成果都能清晰呈现。', x, y + (opts.bodyOffset || 62), w, bodyHeight, 'item',
    { size: opts.bodySize || 18, min: 16, groupId });
}
function cover(long = false) {
  const s = slide(long ? 'cover-long-title' : 'cover-ring', 'cover', { variantKey: long ? 'long-title' : 'ring', fitTitleBeforeVariant: true,
    titleFitLimits: { maxWide: long ? 48 : 24, maxAscii: long ? 92 : 48, singleWide: long ? 24 : 12, singleAscii: long ? 46 : 24 } });
  base(s, 'cover');
  // 普通封面把文字留在圆环的透明内侧；长标题封面将圆环退到文字区上方。
  image(s, 'glass-ring', ASSETS.ring, long ? 834 : 245, long ? 35 : 10, long ? 112 : 510, long ? 112 : 510);
  image(s, 'corner-glow', ASSETS.glow, 0, 427.5, 360, 135);
  text(s, 'title', long ? '面向未来业务发展的项目建设目标与阶段成果汇报' : '蓝紫光斑·唯美清新', 90, long ? 174 : 202, 820, long ? 160 : 125, 'title',
    { size: long ? 40 : 42, min: 32, color: C.white, align: 'center', bold: true });
  text(s, 'subtitle', '把想法变成清晰的表达', 170, long ? 362 : 355, 660, 92, 'content', { size: 22, align: 'center' });
  return s;
}
function contents(count) {
  const s = slide(`contents-${count}`, 'contents'); base(s);
  text(s, 'directory-label', '目录', 56, 222, 180, 88, null, { size: 46, color: C.white, bold: true });
  text(s, 'directory-caption', 'CONTENTS', 60, 312, 160, 42, null, { size: 16, color: C.lavender, font: 'Arial' });
  const rows = count > 4 ? 3 : count, step = count > 4 ? 129 : 108;
  const startY = (562.5 - rows * step) / 2 + 3;
  for (let i = 0; i < count; i++) {
    const two = count > 4, x = two ? 281 + (i % 2) * 333 : 304, y = startY + (two ? Math.floor(i / 2) : i) * step;
    const groupId = `${s.id}-item-${i + 1}`;
    shape(s, 'number-circle', x, y + 6, 52, 52, { circle: true, groupId });
    // 编号框为公共文字适配器保留内边距，避免两位数字被误判为多行溢出。
    text(s, 'number', String(i + 1).padStart(2, '0'), x, y + 13, 52, 62, 'itemNumber', { size: 25, min: 20, color: C.cyan, font: 'Arial', align: 'center', groupId });
    text(s, 'directory-item', `目录主题${i + 1}`, x + 68, y, two ? 239 : 565, 91, 'item', { size: 24, min: 18, color: C.white, groupId });
    line(s, 'directory-rule', x + 68, y + 94, x + (two ? 307 : 633), y + 94, groupId);
  }
  return s;
}
function transition() {
  const s = slide('transition-ring', 'transition'); base(s, 'section');
  image(s, 'glass-ring', ASSETS.ring, 51, 142, 302, 302);
  text(s, 'number', '01', 129, 239, 146, 106, 'partNumber', { size: 64, min: 42, color: C.white, font: 'Arial', align: 'center' });
  text(s, 'title', '让灵感成为行动', 406, 165, 526, 133, 'title', { size: 38, min: 24, color: C.white, bold: true });
  text(s, 'content', '围绕共同目标，开启下一段清晰、有序的项目旅程。', 406, 327, 526, 137, 'content', { size: 21 });
  return s;
}
function textPage(count) {
  const s = slide(`content-text-${count}`, 'content', { allowedItemCounts: [count] }); base(s); header(s);
  if (count === 4) {
    for (let i = 0; i < 4; i++) {
      const x = 56 + (i % 2) * 464, y = 144 + Math.floor(i / 2) * 189, groupId = `${s.id}-item-${i + 1}`;
      shape(s, 'content-card', x, y, 424, 173, { groupId });
      item(s, i, x + 20, y + 12, 384, 94, { groupId, titleSize: 21, bodySize: 18, bodyOffset: 60 });
    }
  } else {
    const boxes = { 1: [[80, 160, 840, 245]], 2: [[56, 156, 424, 258], [520, 156, 424, 258]],
      3: [[56, 158, 280, 256], [360, 158, 280, 256], [664, 158, 280, 256]] }[count];
    boxes.forEach(([x, y, w, h], i) => {
      const groupId = `${s.id}-item-${i + 1}`;
      shape(s, 'content-card', x, y, w, 340, { groupId });
      item(s, i, x + 22, y + 22, w - 44, h, { groupId, titleSize: count === 1 ? 30 : 23, bodySize: count === 3 ? 18 : 20, bodyOffset: 72 });
    });
  }
  return s;
}
function imagePage(count, right = false) {
  const id = count === 1 ? `content-image-${right ? 'right' : 'left'}-1` : `content-image-${count}`;
  const s = slide(id, 'content', { allowedItemCounts: [count], ...(count === 1 ? { variantKey: right ? 'right' : 'left' } : {}) });
  base(s); header(s, '每一张图，都有清晰的表达');
  for (let i = 0; i < count; i++) {
    const groupId = `${id}-item-${i + 1}`;
    if (count === 1) {
      image(s, 'business-image', ASSETS.cover, right ? 540 : 56, 149, 404, 348, groupId);
      item(s, i, right ? 56 : 508, 174, 436, 219, { groupId, titleSize: 26, titleHeight: 80, bodyOffset: 91, bodySize: 20 });
    } else {
      const gap = 24, width = (888 - (count - 1) * gap) / count, x = 56 + i * (width + gap), ih = count === 2 ? 205 : count === 3 ? 181 : 152;
      image(s, 'business-image', ASSETS.cover, x, 148, width, ih, groupId);
      item(s, i, x, 148 + ih + 15, width, count === 2 ? 101 : count === 3 ? 125 : 154, { groupId, titleSize: 20, bodySize: 16, bodyOffset: 62 });
    }
  }
  return s;
}
function special(kind) {
  const count = kind === 'timeline' ? 5 : 4;
  const s = slide(`content-${kind}-${count}`, 'content', { allowedItemCounts: [count], layoutKind: kind,
    ...(kind === 'metrics' ? { metricValueField: 'value', metricUnitField: 'unit' } : {}) });
  base(s); header(s, kind === 'metrics' ? '用数字记录每一份进展' : kind === 'timeline' ? '让每个阶段都有明确方向' : '从目标走向成果');
  for (let i = 0; i < count; i++) {
    const groupId = `${s.id}-item-${i + 1}`;
    if (kind === 'metrics') {
      const x = 56 + (i % 2) * 464, y = 147 + Math.floor(i / 2) * 185;
      shape(s, 'metric-card', x, y, 424, 166, { groupId });
      text(s, 'value', [96, 24, 8, 100][i], x + 21, y + 20, 125, 77, 'itemNumber', { size: 42, min: 24, color: C.cyan, bold: true, font: 'Arial', groupId });
      text(s, 'unit', '%', x + 24, y + 98, 120, 60, 'itemUnit', { size: 18, groupId });
      item(s, i, x + 163, y + 19, 237, 80, { groupId, titleSize: 20, bodySize: 16, bodyOffset: 55 });
    } else {
      const step = count === 5 ? 182 : 232, x = 56 + i * step, width = count === 5 ? 160 : 192;
      const cx = x + width / 2;
      if (i < count - 1) line(s, 'connector', cx + 36, 210, cx + step - 36, 210);
      shape(s, 'node', cx - 35, 175, 70, 70, { circle: true, groupId });
      text(s, 'number', String(i + 1).padStart(2, '0'), cx - 28, 188, 56, 60, 'itemNumber', { size: 30, min: 22, font: 'Arial', align: 'center', color: C.cyan, groupId });
      // 节点按同一视觉行从左到右排列，避免公共填充器重排时间轴顺序。
      item(s, i, x, 279, width, 152, { groupId, titleSize: 20, bodySize: 16, titleHeight: 64, bodyOffset: 70 });
    }
  }
  return s;
}
function end() {
  const s = slide('end-thanks', 'end'); base(s, 'end');
  image(s, 'corner-glow', ASSETS.glow, 0, 400.5, 432, 162);
  text(s, 'title', '感谢您的关注', 140, 198, 720, 121, 'title', { size: 46, min: 32, color: C.white, bold: true, align: 'center' });
  text(s, 'content', '期待下一次共同创造', 180, 346, 640, 106, 'content', { size: 23, align: 'center' });
  return s;
}
export function build() {
  const pages = [cover(), cover(true), ...[2, 3, 4, 5, 6].map(contents), transition(), ...[1, 2, 3, 4].map(textPage),
    imagePage(1), imagePage(1, true), ...[2, 3, 4].map(n => imagePage(n)), special('process'), special('timeline'), special('metrics'), end()];
  return { id: 'template_27', title: '蓝紫光斑·唯美清新', width: 1000, height: 562.5,
    supportsLosslessContentPagination: true, unsupportedLayoutPolicy: 'ordinary', sourceImageCountPolicy: 'one-per-item',
    theme: { themeColors: [C.lavender, C.cyan, C.panel], fontColor: C.body, fontName: '微软雅黑', backgroundColor: C.background },
    metadata: { buildStage: 'production', sourceReference: '唯美清新(2).ppt',
      sourceReferenceSha256: '1afc890ced8aa79bccc4dad0e67965bb652f6c9889f20524c317bb614d0bd1e9', rightsPolicy: 'reference-media-excluded',
      assetGeneration: 'GPT2 图片模板；内置 imagegen；实际模型工具未暴露', assetFiles: Object.values(ASSETS),
      productionSlideIds: pages.map(s => s.id) }, slides: pages };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const output = path.resolve(process.argv[2] || path.join(ROOT, 'backend/main_api/template/template_27.json'));
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(build(), null, 2) + '\n', 'utf8');
  console.log(output);
}

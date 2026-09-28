#!/usr/bin/env node
/** 蓝紫霓虹科技模板：固定视觉与可编辑业务元素分离，使用项目现有语义槽协议。 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const C = { bg: '#060820', title: '#92FCFF', body: '#E8EEFF', white: '#FFFFFF', blue: '#7284FF', pink: '#EC36CF' };
export const ASSETS = Object.fromEntries(Object.entries({
  cover: 'bg_cover_v1.jpg', content: 'bg_content_v1.jpg', directory: 'bg_directory_v1.jpg',
  city: 'city_platform_v1.png', sculpture: 'data_sculpture_v1.png',
  monitor: 'monitor_frame_v1.png', laptop: 'laptop_frame_v1.png', phone: 'phone_frame_v1.png',
}).map(([key, value]) => [key, `template_30_asset_${value}`]));
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const RECT = 'M 0 0 L 200 0 L 200 200 L 0 200 Z';
const CIRCLE = 'M 100 0 A 100 100 0 1 1 100 200 A 100 100 0 1 1 100 0 Z';
// 复用项目已采用的 IconPark 图标路径（Briefcase / Tool / Phone / Plug），保持可编辑原生形状。
const FEATURE_ICONS = [
  'M32 16C32 9.92487 28.4183 4 24 4C19.5817 4 16 9.92487 16 16 M9 16H39L40 28H27V25H21V28H8L9 16Z M8 28L6 42H42L40 28 M21 25H27V31H21V25Z',
  'M44 16C44 22.6274 38.6274 28 32 28C29.9733 28 28.0639 27.4975 26.3896 26.6104L9 44L4 39L21.3896 21.6104C20.5025 19.9361 20 18.0267 20 16C20 9.37258 25.3726 4 32 4C34.0267 4 35.9361 4.50245 37.6104 5.38959L30 13L35 18L42.6104 10.3896C43.4975 12.0639 44 13.9733 44 16Z',
  'M8 30H40V42C40 43.1046 39.1046 44 38 44H10C8.89543 44 8 43.1046 8 42V30Z M40 30V6C40 4.89543 39.1046 4 38 4H10C8.89543 4 8 4.89543 8 6V30 M22 37H26',
  'M6 14H42V24C38 32 32 36 24 36C16 36 10 32 6 24V14Z M33 34L32 44H16L15 34 M22 24H26 M16 4L16 12 M32 4V12',
];

function page(id, type, sourceLayout, extra = {}) {
  return { id, type, sourceLayout, isBaseLayout: Boolean(sourceLayout), background: { type: 'solid', color: C.bg }, elements: [], ...extra };
}
function add(s, role, type, properties) {
  const element = { id: `t30-${s.id}-${role}-${s.elements.length + 1}`, type, rotate: 0, ...properties };
  s.elements.push(element);
  return element;
}
function text(s, role, value, x, y, w, h, slot, options = {}) {
  const { size = 18, min = 16, color = C.body, bold = false, align = 'left', groupId, slotIndex } = options;
  return add(s, role, 'text', { left: x, top: y, width: w, height: h,
    defaultFontName: '微软雅黑', defaultColor: color, minimumFontSize: min, textLineHeight: 1.3,
    content: `<p style="text-align: ${align};"><span style="font-family: 微软雅黑;font-size: ${size}px;color: ${color};font-weight: ${bold ? 'bold' : 'normal'};line-height: 1.3;">${escape(value)}</span></p>`,
    ...(slot ? { textType: slot } : {}), ...(groupId ? { groupId } : {}),
    ...(Number.isInteger(slotIndex) ? { slotIndex } : {}) });
}
function decoration(s, role, asset, x, y, w, h) {
  return add(s, role, 'image', { left: x, top: y, width: w, height: h, src: `/api/data/${asset}`,
    imageType: 'decoration', fixedRatio: false, lock: true });
}
function background(s, kind = 'content') { decoration(s, 'background', ASSETS[kind], 0, 0, 1000, 562.5); }
function shape(s, role, x, y, w, h, options = {}) {
  // 信息图的节点与基础几何保留为原生形状，导出后仍可编辑。
  const { circle = false, fill = C.blue, opacity = 1, stroke = C.title, gradient = false, groupId } = options;
  return add(s, role, 'shape', { left: x, top: y, width: w, height: h,
    viewBox: [200, 200], path: circle ? CIRCLE : RECT, fill, opacity, fixedRatio: false,
    outline: { color: stroke, width: 1, style: 'solid' },
    ...(gradient ? { gradient: { type: 'linear', rotate: 90, colors: [{ color: C.title, pos: 0 }, { color: C.blue, pos: 100 }] } } : {}),
    ...(groupId ? { groupId } : {}) });
}
function line(s, role, x1, y1, x2, y2, color = C.blue, width = 1, groupId) {
  const left = Math.min(x1, x2), top = Math.min(y1, y2);
  return add(s, role, 'line', { left, top, start: [x1 - left, y1 - top], end: [x2 - left, y2 - top],
    points: ['', ''], width, color, style: 'solid', ...(groupId ? { groupId } : {}) });
}
function header(s) {
  text(s, 'title', '让科技连接真实场景', 54, 28, 892, 82, 'title', { size: 30, min: 23, color: C.title, bold: true });
  line(s, 'header-rule', 54, 116, 945, 116, '#334B75');
}
function item(s, index, x, y, w, bodyHeight, options = {}) {
  const groupId = `${s.id}-item-${index + 1}`;
  text(s, 'item-title', `项目要点${index + 1}`, x, y, w, options.titleHeight || 56, 'itemTitle',
    { size: options.titleSize || 22, min: 16, color: C.white, bold: true, groupId: `${groupId}-title`, slotIndex: index });
  text(s, 'item-body', '围绕真实需求，明确实施路径，呈现可验证的产品价值。', x, y + (options.bodyOffset || 60), w, bodyHeight, 'item',
    { size: options.bodySize || 18, min: 16, groupId, slotIndex: index });
  return groupId;
}
function cover(long = false) {
  const s = page(long ? 'cover-long-title' : 'cover-neon', 'cover', 'L01', {
    isBaseLayout: !long,
    variantKey: long ? 'long-title' : 'neon', variantAliases: long ? [] : ['L01'], fitTitleBeforeVariant: true,
    titleFitLimits: { maxWide: long ? 52 : 24, maxAscii: long ? 100 : 48,
      singleWide: long ? 26 : 12, singleAscii: long ? 50 : 24 } });
  background(s, 'cover');
  text(s, 'title', '智联未来', 88, long ? 126 : 160, 824, long ? 180 : 140, 'title',
    { size: long ? 42 : 52, min: 30, color: C.white, bold: true, align: 'center' });
  text(s, 'subtitle', '蓝紫霓虹科技产品发布', 105, 335, 790, 114, 'content', { size: 22, min: 18, align: 'center' });
  return s;
}

function contents(count) {
  const s = page(`contents-${count}`, 'contents', 'L02', { isBaseLayout: count === 4 });
  background(s, 'directory');
  text(s, 'label', '目录', 84, 55, 510, 90, null, { size: 44, color: C.white, bold: true });
  const step = count > 4 ? 62 : 88, start = count > 4 ? 140 : 152;
  for (let i = 0; i < count; i++) {
    const y = start + i * step, gid = `${s.id}-entry-${i}`;
    shape(s, 'number-orb', 87, y + 9, 35, 35, { circle: true, fill: C.pink, stroke: C.pink, groupId: gid });
    text(s, 'number', String(i + 1).padStart(2, '0'), 126, y, 66, 58, 'itemNumber', { size: 25, min: 18, groupId: gid, color: C.title });
    text(s, 'chapter', `目录主题${i + 1}`, 201, y, 406, count > 4 ? 62 : 82, 'item', { size: 26, min: 18, groupId: gid, color: C.white });
  }
  return s;
}
function transition() {
  const s = page('transition-neon', 'transition', 'L03');
  background(s);
  decoration(s, 'city', ASSETS.city, 50, 293, 350, 263);
  text(s, 'number', '01', 455, 94, 430, 106, 'partNumber', { size: 60, min: 36, color: C.blue, bold: true });
  text(s, 'title', '连接产品与未来', 455, 222, 470, 137, 'title', { size: 38, min: 25, color: C.title, bold: true });
  text(s, 'content', '从需求出发，走向清晰的行动与成果。', 455, 382, 470, 134, 'content', { size: 21, min: 18 });
  return s;
}
function contentPage(id, sourceLayout, count, kind) {
  const s = page(id, 'content', sourceLayout, { allowedItemCounts: [count],
    // 普通源版式通过别名支持精确选择，同时参与没有显式变体的默认生成。
    // 通用回退页沿用现有 left 默认协议，并用页面 ID 提供唯一的显式入口。
    ...(sourceLayout ? (kind ? { variantKey: sourceLayout } : { variantAliases: [sourceLayout] })
      : { variantKey: 'left', variantAliases: [id] }), ...(kind ? { layoutKind: kind } : {}) });
  background(s); header(s);
  return s;
}
function picture(s, x, y, w, h, clipShape = 'rect') {
  // 同页一张主图可以配多条说明；显式允许图少于文字，避免套用一项一图的旧约束。
  return add(s, 'business-image', 'image', { left: x, top: y, width: w, height: h,
    src: `/api/data/${ASSETS.content}`, imageType: 'content', groupId: `${s.id}-hero-image`,
    fixedRatio: false, strictImageCount: true, requireSourceDimensions: true, allowExtraItems: true,
    clip: { shape: clipShape, range: [[0, 0], [100, 100]] } });
}
function device(s, kind, x, y, w) {
  // 业务槽位按设备图片中实际屏幕内缘标定，预留一像素边界，不能覆盖机身边框。
  const config = { monitor: [590 / 668, 79 / 668, 71 / 590, 509 / 668, 322 / 590],
    laptop: [960 / 1639, 189 / 1639, 77 / 960, 1250 / 1639, 782 / 960],
    phone: [1500 / 717, 48 / 717, 217 / 1500, 626 / 717, 1099 / 1500] }[kind];
  const h = w * config[0];
  decoration(s, `${kind}-frame`, ASSETS[kind], x, y, w, h);
  picture(s, x + config[1] * w, y + config[2] * h, config[3] * w, config[4] * h);
  s.deviceFrame = { kind, frame: { x, y, width: w, height: h }, screen: config.slice(1) };
}
function number(s, i, x, y, w = 64, color = C.title) {
  text(s, 'number', String(i + 1).padStart(2, '0'), x, y, w, 60, 'itemNumber',
    { size: 24, min: 16, color, align: 'center', groupId: `${s.id}-item-${i + 1}`, slotIndex: i });
}
function verticalItems(s, count, x, y, w, step, bodyHeight) {
  for (let i = 0; i < count; i++) {
    number(s, i, x, y + i * step, 55);
    item(s, i, x + 67, y + i * step, w - 67, bodyHeight, { titleSize: 21, titleHeight: 43, bodyOffset: 45, bodySize: 17 });
  }
}
function cityPage() {
  const s = contentPage('content-city-3', 'L04', 3);
  decoration(s, 'city', ASSETS.city, 587, 238, 365, 274);
  verticalItems(s, 3, 55, 146, 520, 126, 77);
  return s;
}
function monitorPage() {
  const s = contentPage('content-monitor-3', 'L05', 3);
  device(s, 'monitor', 533, 151, 420);
  verticalItems(s, 3, 54, 146, 455, 126, 77);
  return s;
}
function circlesPage() {
  const s = contentPage('content-circles-3', 'L06', 3);
  for (let i = 0; i < 3; i++) {
    const x = 73 + i * 308;
    shape(s, 'theme-orb', x + 68, 150, 138, 138, { circle: true, gradient: true });
    number(s, i, x + 103, 190, 70, '#091333');
    item(s, i, x, 307, 270, 139, { titleSize: 24, titleHeight: 60, bodyOffset: 65, bodySize: 19 });
  }
  return s;
}
function imageNotePage() {
  const s = contentPage('content-image-note-1', 'L07', 1);
  picture(s, 54, 146, 402, 351);
  item(s, 0, 505, 157, 434, 249, { titleSize: 28, titleHeight: 78, bodyOffset: 89, bodySize: 20 });
  line(s, 'note-rule', 505, 506, 938, 506, C.title, 3);
  return s;
}
function swotPage() {
  const s = contentPage('content-swot-4', 'L08', 4, 'compare');
  const letters = ['S', 'W', 'O', 'T'];
  for (let i = 0; i < 4; i++) {
    const x = 80 + (i % 2) * 139, y = 202 + Math.floor(i / 2) * 140;
    shape(s, 'swot-orb', x, y, 122, 122, { circle: true, gradient: true });
    text(s, 'swot-label', letters[i], x + 13, y + 29, 96, 74, null, { size: 42, color: C.white, bold: true, align: 'center' });
    item(s, i, 415 + (i % 2) * 278, 147 + Math.floor(i / 2) * 195, 249, 110,
      { titleSize: 22, titleHeight: 61, bodyOffset: 66, bodySize: 17 });
  }
  return s;
}
function imageLeftPage() {
  const s = contentPage('content-image-left-3', 'L09', 3);
  picture(s, 55, 150, 339, 361);
  verticalItems(s, 3, 436, 146, 508, 126, 77);
  return s;
}
function sculpturePage() {
  const s = contentPage('content-sculpture-2', 'L10', 2);
  decoration(s, 'sculpture', ASSETS.sculpture, 603, 165, 353, 353);
  for (let i = 0; i < 2; i++) {
    line(s, 'item-accent', 59, 151 + i * 195, 94, 151 + i * 195, C.title, 4);
    item(s, i, 59, 169 + i * 195, 507, 112, { titleSize: 25, bodySize: 19, bodyOffset: 63 });
  }
  return s;
}
function crossPage() {
  const s = contentPage('content-cross-4', 'L11', 4, 'hub-spoke');
  line(s, 'cross-a', 433, 195, 565, 416, C.title, 5);
  line(s, 'cross-b', 565, 195, 433, 416, C.title, 5);
  line(s, 'cross-top', 433, 195, 565, 195, C.blue, 3);
  line(s, 'cross-bottom', 433, 416, 565, 416, C.blue, 3);
  for (let i = 0; i < 4; i++) {
    const right = i % 2, bottom = Math.floor(i / 2), x = right ? 639 : 54, y = 145 + bottom * 204;
    shape(s, 'relation-node', right ? 535 : 399, 166 + bottom * 221, 60, 60, { circle: true, gradient: true });
    number(s, i, right ? 535 : 399, 173 + bottom * 221, 60, '#091333');
    item(s, i, x, y, 306, 105, { titleHeight: 58, bodyOffset: 66 });
  }
  return s;
}
function columnsPage() {
  const s = contentPage('content-icon-columns-4', 'L12', 4, 'process');
  for (let i = 0; i < 4; i++) {
    const x = 55 + i * 228;
    shape(s, 'step-orb', x + 48, 151, 112, 112, { circle: true, gradient: true });
    const icon = shape(s, 'step-symbol', x + 80, 180, 48, 48, { fill: '#FFFFFF00', stroke: C.white });
    icon.path = FEATURE_ICONS[i]; icon.viewBox = [48, 48]; icon.outline.width = 2;
    number(s, i, x + 69, 274, 70);
    item(s, i, x, 338, 205, 111, { titleSize: 20, titleHeight: 65, bodyOffset: 68, bodySize: 17 });
  }
  return s;
}
function metricsPage() {
  const s = contentPage('content-metrics-image-3', 'L13', 3, 'metrics');
  s.metricValueField = 'value'; s.metricUnitField = 'unit';
  picture(s, 545, 153, 400, 358, 'roundRect');
  for (let i = 0; i < 3; i++) {
    const y = 146 + i * 126, gid = `${s.id}-metric-${i}`;
    text(s, 'metric-value', String((i + 1) * 17), 56, y, 110, 68, 'itemNumber', { size: 40, min: 23, color: C.title, bold: true, groupId: gid });
    text(s, 'metric-unit', '%', 166, y + 8, 47, 58, 'itemUnit', { size: 25, min: 16, color: C.title, groupId: gid });
    text(s, 'metric-name', `核心指标${i + 1}`, 238, y, 265, 49, 'itemTitle', { size: 21, min: 16, color: C.white, bold: true, groupId: `${gid}-title` });
    text(s, 'metric-description', '以可靠的数据呈现实际应用成果。', 238, y + 50, 265, 77, 'item', { size: 17, min: 16, groupId: gid });
  }
  return s;
}
function fanPage() {
  const s = contentPage('content-fan-4', 'L14', 4, 'hub-spoke');
  // 四块扇形对应四项关系，使用原生路径而非烘焙成图，保持源版式的扇面结构。
  const rim = [[0, 0], [29.29, 70.71], [100, 100], [170.71, 70.71], [200, 0]];
  const labels = [[55, 144], [55, 353], [704, 353], [704, 144]];
  const badges = [[381, 236], [439, 317], [516, 317], [574, 236]];
  for (let i = 0; i < 4; i++) {
    const a = rim[i], b = rim[i + 1];
    const sector = shape(s, 'fan-sector', 355, 220, 290, 196, { gradient: true, stroke: C.white });
    sector.viewBox = [200, 100];
    sector.path = `M 100 0 L ${a[0]} ${a[1]} A 100 100 0 0 0 ${b[0]} ${b[1]} Z`;
    number(s, i, badges[i][0], badges[i][1], 52, '#091333');
    item(s, i, labels[i][0], labels[i][1], 238, 99, { titleHeight: 62, bodyOffset: 67, bodySize: 17 });
  }
  shape(s, 'hub', 468, 174, 64, 64, { circle: true, gradient: true });
  return s;
}
function stepsPage() {
  const s = contentPage('content-steps-4', 'L15', 4, 'process');
  for (let i = 0; i < 4; i++) {
    const x = 55 + i * 228;
    shape(s, 'step-block', x, 285, 204, 65, { gradient: true });
    number(s, i, x + 68, 291, 70, '#091333');
    if (i < 3) line(s, 'step-link', x + 205, 319, x + 227, 319, C.title, 2);
    item(s, i, x, i % 2 ? 367 : 135, 204, i % 2 ? 83 : 82,
      { titleHeight: 65, bodyOffset: 68, titleSize: 20, bodySize: 17 });
  }
  return s;
}
function laptopPage() {
  const s = contentPage('content-laptop-1', 'L16', 1);
  device(s, 'laptop', 465, 199, 487);
  item(s, 0, 56, 156, 372, 254, { titleSize: 27, titleHeight: 84, bodyOffset: 91, bodySize: 20 });
  return s;
}
function positioningPage() {
  const s = contentPage('content-positioning-3', 'L17', 3, 'positioning');
  for (let i = 0; i < 3; i++) item(s, i, 55 + i * 309, 145, 273, 99, { titleSize: 22, bodyOffset: 63 });
  // 网格与节点是该版式的关系示意图，全部用原生线条和形状表达。
  for (let i = 0; i < 7; i++) {
    const y = 359 + i * 26, inset = (6 - i) * 30;
    line(s, 'grid-row', 70 + inset, y, 930 - inset, y, '#445CC1', 1);
  }
  for (let i = 0; i < 10; i++) line(s, 'grid-ray', 250 + i * 55.5, 359, 70 + i * 95.5, 515, '#445CC1', 1);
  [[286, 390], [504, 448], [780, 396]].forEach(([x, y], i) => {
    shape(s, 'location', x - 15, y - 15, 30, 30, { circle: true, fill: C.pink, stroke: C.pink });
    number(s, i, x - 32, y - 63, 64);
  });
  return s;
}
function phonePage() {
  const s = contentPage('content-phone-6', 'L18', 6);
  device(s, 'phone', 723, 138, 181);
  for (let i = 0; i < 6; i++) item(s, i, 56 + (i % 2) * 294, 144 + Math.floor(i / 2) * 130, 253, 79,
    { titleSize: 20, titleHeight: 45, bodyOffset: 48, bodySize: 17 });
  return s;
}
function compareImagePage() {
  const s = contentPage('content-compare-image-4', 'L19', 4, 'compare');
  picture(s, 689, 156, 255, 355);
  for (let i = 0; i < 4; i++) {
    const x = 55 + (i % 2) * 311, y = 150 + Math.floor(i / 2) * 194;
    if (i % 2) shape(s, 'compare-band', x - 15, y - 8, 295, 176, { fill: '#263578', opacity: .65, stroke: '#415998' });
    item(s, i, x, y, 264, 99, { titleHeight: 60, bodyOffset: 66, bodySize: 17 });
  }
  return s;
}
function ringsPage() {
  const s = contentPage('content-ring-image-5', 'L20', 5, 'hub-spoke');
  for (let i = 0; i < 5; i++) {
    const centerX = 123 + i * 188, diameter = i === 2 ? 166 : 138;
    shape(s, 'relation-ring', centerX - diameter / 2, 218 + (166 - diameter) / 2, diameter, diameter, { circle: true, gradient: true });
    if (i === 2) {
      picture(s, centerX - 73, 228, 146, 146, 'ellipse');
      number(s, i, centerX - 35, 156, 70);
    } else number(s, i, centerX - 35, 271, 70, '#091333');
    item(s, i, centerX - 81, 395, 162, 88, { titleSize: 18, titleHeight: 62, bodyOffset: 63, bodySize: 16 });
  }
  return s;
}
function cyclePage() {
  const s = contentPage('content-cycle-4', 'L21', 4, 'process');
  const points = [[406, 220], [510, 220], [510, 324], [406, 324]];
  points.forEach(([x, y], i) => {
    const block = shape(s, 'cycle-block', x, y, 84, 84, { gradient: true });
    block.path = 'M 32 0 L 200 0 L 168 200 L 0 200 Z';
    number(s, i, x + 9, y + 16, 64, '#091333');
    item(s, i, i === 1 || i === 2 ? 661 : 55, i < 2 ? 149 : 352, 282, 109, { titleHeight: 58, bodyOffset: 64 });
  });
  [[490, 262, 509, 262], [552, 304, 552, 323], [510, 366, 491, 366], [448, 324, 448, 305]].forEach((edge, i) => {
    const arrow = line(s, `cycle-arrow-${i}`, ...edge, C.title, 2);
    arrow.points = ['', 'arrow'];
  });
  return s;
}
function ordinary(count) {
  const s = contentPage(`content-text-${count}`, null, count);
  const columns = count === 1 ? 1 : count === 3 ? 3 : 2, rows = Math.ceil(count / columns);
  const w = (892 - (columns - 1) * 30) / columns, step = 388 / rows;
  for (let i = 0; i < count; i++) {
    const x = 54 + (i % columns) * (w + 30), y = 143 + Math.floor(i / columns) * step;
    item(s, i, x, y, w, step - (rows === 3 ? 51 : 66) - 9,
      { titleSize: count === 1 ? 28 : 22, titleHeight: rows === 3 ? 45 : 60,
        bodyOffset: rows === 3 ? 49 : 64, bodySize: count === 1 ? 21 : 18 });
  }
  return s;
}
function ordinaryImage(count) {
  const s = contentPage(`content-image-default-${count}`, null, count);
  picture(s, 55, 146, count > 3 ? 290 : 351, 367);
  const x0 = count > 3 ? 385 : 449, columns = count > 3 ? 2 : 1, rows = Math.ceil(count / columns);
  const w = (945 - x0 - (columns - 1) * 24) / columns, step = 381 / rows;
  for (let i = 0; i < count; i++) item(s, i, x0 + (i % columns) * (w + 24), 145 + Math.floor(i / columns) * step,
    w, step - (rows === 3 ? 50 : 66) - 8, { titleSize: count === 1 ? 26 : 20,
      titleHeight: rows === 3 ? 44 : 60, bodyOffset: rows === 3 ? 48 : 64, bodySize: count > 3 ? 16 : 18 });
  return s;
}
function end() {
  const s = page('end-neon', 'end', 'L22', { variantKey: 'L22' }); background(s, 'cover');
  text(s, 'title', '感谢您的关注', 88, 179, 824, 140, 'title', { size: 49, min: 30, color: C.white, bold: true, align: 'center' });
  text(s, 'content', '让科技创造更多可能', 105, 344, 790, 113, 'content', { size: 23, min: 18, align: 'center' });
  return s;
}
export function build() {
  const base = [cover(), contents(4), transition(), cityPage(), monitorPage(), circlesPage(), imageNotePage(),
    swotPage(), imageLeftPage(), sculpturePage(), crossPage(), columnsPage(), metricsPage(), fanPage(), stepsPage(),
    laptopPage(), positioningPage(), phonePage(), compareImagePage(), ringsPage(), cyclePage(), end()];
  const slides = [...base, cover(true), ...[2, 3, 5, 6].map(contents), ...[1, 2, 3, 4, 5, 6].map(ordinary),
    ...[1, 2, 3, 4, 5, 6].map(ordinaryImage)];
  return { id: 'template_30', title: '蓝紫霓虹·科技产品发布', width: 1000, height: 562.5,
    supportsLosslessContentPagination: true, unsupportedLayoutPolicy: 'ordinary',
    theme: { themeColors: [C.title, C.blue, C.pink], fontColor: C.body, fontName: '微软雅黑', backgroundColor: C.bg },
    metadata: { buildStage: 'development', sourceReference: '产品发布 (6).pptx',
      sourceReferenceSha256: '0ff0a66c88d582ea25573c2b58f3a16ce794a50a7238edd9afc8aad9cf3fbe70',
      assetFiles: [...new Set(slides.flatMap(s => s.elements.filter(e => e.imageType === 'decoration').map(e => e.src.split('/').at(-1))))],
      baseSlideIds: base.map(s => s.id), baseLayoutCount: 22,
      productionSlideIds: slides.map(s => s.id) }, slides };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const output = path.resolve(process.argv[2] || path.join(ROOT, 'backend/main_api/template/template_30.json'));
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(build(), null, 2) + '\n', 'utf8');
  console.log(output);
}

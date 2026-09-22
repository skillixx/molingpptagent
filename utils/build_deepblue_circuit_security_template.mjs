#!/usr/bin/env node
/** 深蓝电路网络安全模板：固定装饰分层，业务信息始终使用可编辑对象。 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const C = { bg: '#0B1524', panel: '#183749', cyan: '#A0C9D8', accent: '#81B8CB', white: '#E6F2F6', body: '#C5DCE5', rule: '#3B6578' };
export const ASSETS = Object.fromEntries(Object.entries({
  cover: 'bg_cover_v1.jpg', content: 'bg_content_v1.jpg', section: 'bg_section_v1.jpg', end: 'bg_end_v1.jpg',
  lock: 'lock_v1.png', upper: 'circuit_upper_right_v1.png', lower: 'circuit_lower_left_v1.png', sphere: 'network_sphere_v1.png',
}).map(([key, suffix]) => [key, `template_26_asset_${suffix}`]));
const RECT = 'M 0 0 L 200 0 L 200 200 L 0 200 Z';
const CIRCLE = 'M 100 0 A 100 100 0 1 1 99.99 0 Z';
const HEX = 'M 50 0 L 150 0 L 200 100 L 150 200 L 50 200 L 0 100 Z';
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const makeSlide = (id, type, options = {}) => ({ id, type, background: { type: 'solid', color: C.bg }, elements: [], ...options });

function add(s, role, type, props) {
  const element = { type, id: `t26-${s.id}-${role}-${s.elements.length + 1}`, rotate: 0, ...props };
  s.elements.push(element); return element;
}
function text(s, role, value, x, y, w, h, slot, options = {}) {
  const { size = 18, min = 16, color = C.body, bold = false, align = 'left', groupId, font = '微软雅黑' } = options;
  // 样式采用导出器识别的格式，保证编辑器与 PPTX 字体、字重一致。
  return add(s, role, 'text', {
    left: x, top: y, width: w, height: h, defaultFontName: font, defaultColor: color,
    content: `<p style="text-align: ${align};"><span style="font-family: ${font};font-size: ${size}px;color: ${color};font-weight: ${bold ? 'bold' : 'normal'};line-height: 1.3;">${escape(value)}</span></p>`,
    textLineHeight: 1.3, minimumFontSize: min,
    ...(slot ? { textType: slot } : {}), ...(groupId ? { groupId } : {}),
  });
}
function shape(s, role, x, y, w, h, fill, options = {}) {
  return add(s, role, 'shape', { left: x, top: y, width: w, height: h, viewBox: [200, 200],
    path: options.path || RECT, fill, fixedRatio: false,
    outline: { color: options.stroke || fill, width: options.strokeWidth || 0, style: 'solid' },
    ...(options.groupId ? { groupId: options.groupId } : {}),
  });
}
function line(s, role, x1, y1, x2, y2, color = C.rule, groupId) {
  // 连接线保持原生对象；负斜率通过局部端点表示，避免负数宽高。
  const left = Math.min(x1, x2), top = Math.min(y1, y2);
  return add(s, role, 'line', { left, top, start: [x1 - left, y1 - top], end: [x2 - left, y2 - top],
    points: ['', ''], width: 1.2, color, style: 'solid', ...(groupId ? { groupId } : {}) });
}
function image(s, role, asset, x, y, w, h, groupId) {
  return add(s, role, 'image', { left: x, top: y, width: w, height: h, src: `/api/data/${asset}`, fixedRatio: false,
    imageType: groupId ? 'content' : 'decoration',
    ...(groupId ? { groupId, strictImageCount: true, requireSourceDimensions: true, clip: { shape: 'rect', range: [[0, 0], [100, 100]] } } : { lock: true }),
  });
}
function base(s, kind = 'content') { image(s, 'background', ASSETS[kind], 0, 0, 1000, 562.5); }
function header(s, value = '网络安全项目策划', slot = 'title') {
  image(s, 'header-lock', ASSETS.lock, 40, 27, 44, 44);
  text(s, 'title', value, 104, 24, 846, 74, slot, { size: 28, min: 24, color: C.cyan, bold: true });
  line(s, 'header-rule', 104, 108, 950, 108);
}
function item(s, index, x, y, w, bodyHeight, options = {}) {
  const groupId = options.groupId || `${s.id}-item-${index + 1}`;
  text(s, 'item-title', `安全要点${index + 1}`, x, y, w, options.titleHeight || 56, 'itemTitle', {
    size: options.titleSize || 22, min: options.titleMin || 16, color: C.cyan, bold: true, groupId, align: options.align,
  });
  text(s, 'item-body', '围绕实际业务需求，明确安全目标、实施行动与交付安排。', x, y + (options.bodyOffset || 64), w, bodyHeight, 'item', {
    size: options.bodySize || 18, min: 16, groupId, align: options.align,
  });
}
function cover(long = false) {
  const s = makeSlide(long ? 'cover-long-title' : 'cover-lock', 'cover', {
    variantKey: long ? 'long-title' : 'lock', fitTitleBeforeVariant: true,
    titleFitLimits: { maxWide: long ? 48 : 24, maxAscii: long ? 92 : 48, singleWide: long ? 24 : 12, singleAscii: long ? 46 : 24 },
  });
  base(s, 'cover');
  image(s, 'upper-circuit', ASSETS.upper, 650, 0, 350, 350);
  if (!long) image(s, 'lower-circuit', ASSETS.lower, 0, 242.5, 320, 320);
  image(s, 'hero-lock', ASSETS.lock, long ? 456 : 447, long ? 75 : 88, long ? 88 : 106, long ? 88 : 106);
  text(s, 'title', long ? '面向业务持续发展的网络安全建设与实施计划' : '网络安全项目计划书', 88, long ? 187 : 219, 824, long ? 155 : 125, 'title', {
    size: long ? 40 : 48, min: 32, color: C.white, align: 'center', bold: true,
  });
  text(s, 'subtitle', '安全目标 · 实施路径 · 持续保障', 160, long ? 369 : 375, 680, 96, 'content', { size: 21, align: 'center' });
  return s;
}
function contents(count) {
  const s = makeSlide(`contents-${count}`, 'contents'); base(s);
  image(s, 'upper-circuit', ASSETS.upper, 685, 0, 315, 315);
  shape(s, 'directory-label', 50, 210, 180, 155, C.panel, { path: HEX, stroke: C.accent, strokeWidth: 1.5 });
  text(s, 'directory-heading', '目录', 71, 240, 138, 73, null, { size: 36, color: C.cyan, bold: true, align: 'center' });
  const rows = count <= 4 ? count : 3;
  const step = count <= 4 ? 104 : 130;
  const startY = (562.5 - rows * step) / 2 + 6;
  for (let i = 0; i < count; i++) {
    const twoColumns = count > 4, x = twoColumns ? 283 + (i % 2) * 337 : 318;
    const y = startY + (twoColumns ? Math.floor(i / 2) : i) * step, groupId = `${s.id}-item-${i + 1}`;
    text(s, 'number', `${i + 1}`.padStart(2, '0'), x, y, 65, 62, 'itemNumber', { size: 33, color: C.accent, font: 'Arial', groupId });
    text(s, 'item', `目录主题${i + 1}`, x + 77, y + 1, twoColumns ? 232 : 514, 90, 'item', { size: 24, min: 18, color: C.white, groupId });
    line(s, 'directory-rule', x + 77, y + 95, x + (twoColumns ? 306 : 591), y + 95, C.rule, groupId);
  }
  return s;
}
function transition() {
  const s = makeSlide('transition-circuit', 'transition'); base(s, 'section');
  image(s, 'upper-circuit', ASSETS.upper, 540, 0, 460, 460);
  image(s, 'lock', ASSETS.lock, 100, 107, 82, 82);
  text(s, 'part-number', '01', 101, 220, 126, 114, 'partNumber', { size: 64, min: 42, color: C.accent, font: 'Arial' });
  text(s, 'title', '安全建设目标', 249, 203, 637, 123, 'title', { size: 36, min: 24, color: C.white, bold: true });
  text(s, 'content', '从业务需求出发，形成清晰的安全实施路径。', 249, 340, 637, 120, 'content', { size: 21 });
  return s;
}
function textPage(count) {
  const s = makeSlide(`content-text-${count}`, 'content', { allowedItemCounts: [count] }); base(s);
  if (count === 1) image(s, 'lower-circuit', ASSETS.lower, 0, 312.5, 250, 250);
  if (count === 4) image(s, 'network-sphere', ASSETS.sphere, 31, 185, 298, 298);
  header(s);
  if (count === 4) {
    // 右侧四组保持足够的正文高度，长原题回填时仍容纳两行，不因标题拆成单项页。
    // 公共容量预检按 1.5 行高计算：正文框保留 68px，覆盖两行 16px 文字及内边距。
    for (let i = 0; i < 4; i++) item(s, i, 359, 110 + i * 112, 593, 68, { titleHeight: 44, bodyOffset: 44, titleSize: 18, bodySize: 16 });
  } else {
    const boxes = { 1: [[142, 186, 710, 218]], 2: [[66, 171, 405, 236], [534, 171, 405, 236]],
      3: [[48, 166, 277, 258], [361, 166, 277, 258], [674, 166, 277, 258]] }[count];
    boxes.forEach(([x, y, w, h], i) => {
      const groupId = `${s.id}-item-${i + 1}`;
      line(s, 'accent', x, y - 11, x + 54, y - 11, C.accent, groupId);
      item(s, i, x, y, w, h, { groupId, titleSize: count === 1 ? 28 : 22, bodySize: count === 3 ? 16 : 20 });
    });
  }
  return s;
}
function imagePage(count, right = false) {
  const id = count === 1 ? `content-image-${right ? 'right' : 'left'}-1` : `content-image-${count}`;
  const s = makeSlide(id, 'content', { allowedItemCounts: [count], ...(count === 1 ? { variantKey: right ? 'right' : 'left' } : {}) });
  base(s); header(s, '业务场景与安全实践');
  for (let i = 0; i < count; i++) {
    const groupId = `${id}-item-${i + 1}`;
    if (count === 1) {
      image(s, 'business-image', ASSETS.content, right ? 540 : 48, 153, 410, 343, groupId);
      item(s, i, right ? 48 : 510, 165, 440, 219, { groupId, titleHeight: 80, bodyOffset: 90, bodySize: 20 });
    } else {
      const gap = 24, w = (904 - gap * (count - 1)) / count, x = 48 + i * (w + gap), ih = count === 2 ? 208 : count === 3 ? 185 : 155;
      image(s, 'business-image', ASSETS.content, x, 147, w, ih, groupId);
      item(s, i, x, 147 + ih + 14, w, count === 2 ? 100 : count === 3 ? 121 : 150, { groupId, titleSize: 20, bodySize: 16, bodyOffset: 62 });
    }
  }
  return s;
}
function special(kind) {
  const count = kind === 'hub-spoke' ? 6 : 4;
  const id = kind === 'hub-spoke' ? 'content-hub-6' : `content-${kind}-4`;
  const s = makeSlide(id, 'content', { allowedItemCounts: [count], layoutKind: kind, ...(kind === 'metrics' ? { metricValueField: 'value', metricUnitField: 'unit' } : {}) });
  base(s);
  // 关系图的唯一标题槽位位于中心，中心主题会随语义标题填充，而不是固定示例文字。
  header(s, kind === 'hub-spoke' ? '安全能力关联' : kind === 'metrics' ? '关键安全指标' : '实施流程', kind === 'hub-spoke' ? null : 'title');
  if (kind === 'hub-spoke') {
    for (let i = 0; i < 6; i++) {
      const right = i % 2 === 1, y = 142 + Math.floor(i / 2) * 130;
      line(s, 'spoke', 500, 328, right ? 656 : 344, y + 45);
    }
    shape(s, 'hub', 391, 229, 218, 198, C.panel, { path: HEX, stroke: C.accent, strokeWidth: 2 });
    text(s, 'hub-title', '网络安全体系', 407, 266, 186, 116, 'title', { size: 25, min: 16, color: C.white, align: 'center', bold: true });
  }
  for (let i = 0; i < count; i++) {
    const groupId = `${id}-item-${i + 1}`;
    if (kind === 'metrics') {
      const x = 58 + (i % 2) * 470, y = 154 + Math.floor(i / 2) * 187;
      text(s, 'metric-value', `${(i + 1) * 20}`, x, y, 164, 84, 'itemNumber', { size: 39, min: 24, color: C.cyan, bold: true, font: 'Arial', groupId });
      text(s, 'metric-unit', '%', x, y + 88, 164, 62, 'itemUnit', { size: 18, min: 16, color: C.accent, groupId });
      item(s, i, x + 184, y + 2, 234, 94, { groupId, titleSize: 20, bodySize: 16, bodyOffset: 60 });
      line(s, 'metric-rule', x, y + 162, x + 418, y + 162, C.rule, groupId);
    } else if (kind === 'process') {
      const x = 48 + i * 232;
      if (i < 3) line(s, 'connector', x + 147, 208, x + 317, 208);
      shape(s, 'step-node', x + 56, 164, 96, 88, C.panel, { path: HEX, stroke: C.accent, strokeWidth: 1.5, groupId });
      text(s, 'step-number', String(i + 1).padStart(2, '0'), x + 68, 181, 72, 59, 'itemNumber', { size: 30, min: 22, color: C.cyan, align: 'center', font: 'Arial', groupId });
      item(s, i, x, 279, 208, 168, { groupId, titleSize: 20, bodySize: 16, bodyOffset: 64 });
    } else {
      // 按从上到下、每行从左到右构建节点，使对象序列与公共填充器的视觉行序一致。
      const x = i % 2 === 0 ? 52 : 667, y = 139 + Math.floor(i / 2) * 130;
      item(s, i, x, y, 281, 72, { groupId, titleHeight: 44, bodyOffset: 46, titleSize: 18, bodySize: 16 });
    }
  }
  return s;
}
function end(action = false) {
  const s = makeSlide(action ? 'end-action' : 'end-thanks', 'end', { variantKey: action ? 'action' : 'thanks', preserveEndItemBody: action });
  base(s, 'end'); image(s, 'lower-circuit', ASSETS.lower, 0, 257.5, 305, 305);
  if (!action) image(s, 'lock', ASSETS.lock, 458, 113, 84, 84);
  text(s, 'title', action ? '期待与您交流' : '感谢您的观看', 118, action ? 62 : 231, 764, 118, 'title', { size: 45, min: 32, color: C.white, align: 'center', bold: true });
  text(s, 'content', action ? '联系信息与下一步行动' : '共同构建可信赖的安全环境', 160, action ? 181 : 367, 680, 87, 'content', { size: 21, align: 'center' });
  if (action) for (let i = 0; i < 3; i++) text(s, 'action', `行动信息${i + 1}`, 180, 282 + i * 76, 640, 70, 'item', { size: 18, align: 'center', groupId: `${s.id}-item-${i + 1}` });
  return s;
}
export function build(stage = 'production') {
  if (!['mvp', 'production'].includes(stage)) throw new Error('阶段必须是 mvp 或 production');
  const all = [cover(), cover(true), ...[2, 3, 4, 5, 6].map(contents), transition(), ...[1, 2, 3, 4].map(textPage),
    imagePage(1), imagePage(1, true), ...[2, 3, 4].map(n => imagePage(n)), special('process'), special('metrics'), special('hub-spoke'), end(), end(true)];
  const additions = new Set(['cover-long-title', 'content-image-2', 'content-image-3', 'content-image-4', 'content-process-4', 'content-metrics-4', 'content-hub-6', 'end-action']);
  const mvp = all.filter(s => !additions.has(s.id));
  return { id: 'template_26', title: '深蓝电路·网络安全', width: 1000, height: 562.5,
    supportsLosslessContentPagination: true, unsupportedLayoutPolicy: 'ordinary', sourceImageCountPolicy: 'one-per-item',
    theme: { themeColors: [C.cyan, C.accent, C.panel], fontColor: C.body, fontName: '微软雅黑', backgroundColor: C.bg },
    metadata: { buildStage: stage, sourceReference: '项目策划(3).pptx', sourceReferenceSha256: 'd1b398e9538faa293eff277196682b8c1e91275c2d672bcede06303395b7ec06',
      rightsPolicy: 'reference-media-excluded', assetGeneration: 'GPT2 图片模板；实际模型工具未暴露', assetFiles: Object.values(ASSETS),
      mvpSlideIds: mvp.map(s => s.id), productionSlideIds: all.map(s => s.id) },
    slides: stage === 'mvp' ? mvp : all,
  };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2), stageIndex = args.indexOf('--stage');
  const stage = stageIndex >= 0 ? args[stageIndex + 1] : 'production';
  const output = path.resolve(args[0] && !args[0].startsWith('--') ? args[0] : path.join(ROOT, 'backend/main_api/template/template_26.json'));
  fs.mkdirSync(path.dirname(output), { recursive: true }); fs.writeFileSync(output, JSON.stringify(build(stage), null, 2) + '\n', 'utf8');
  console.log(output);
}

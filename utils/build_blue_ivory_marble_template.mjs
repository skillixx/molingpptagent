#!/usr/bin/env node

/**
 * 确定性构建蓝米流纹商务汇报模板。
 * 参考 PPT 只提供构图和视觉语言，生产图片使用原创或授权明确素材。
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, "..");
const TEMPLATE_DIR = path.join(ROOT, "backend", "main_api", "template");

const COLORS = {
  white: "#FFFFFF",
  ivory: "#ECEBDD",
  blue: "#183F59",
  blue2: "#235775",
  mist: "#7FA7B5",
  gray: "#555E64",
  lightGray: "#E7E8E8",
  black: "#111111",
};

const ASSETS = {
  // 蓝白封面使用新文件名，避免新生成文档命中浏览器中的旧背景缓存。
  cover: "/api/data/template_21_asset_bg_cover_v2.jpg",
  content: "/api/data/template_21_asset_bg_content_v1.jpg",
  section: "/api/data/template_21_asset_bg_section_v1.jpg",
  end: "/api/data/template_21_asset_bg_end_v1.jpg",
  blueTile: "/api/data/template_21_asset_marble_tile_blue_v1.jpg",
  ivoryTile: "/api/data/template_21_asset_marble_tile_ivory_v1.jpg",
  corner: "/api/data/template_21_asset_corner_flow_v1.png",
};

const REFERENCE = {
  "cover-marble-frame": [1],
  "cover-marble-minimal": [1],
  "contents-2": [2], "contents-3": [2], "contents-4": [2],
  "contents-5": [2], "contents-6": [2], "contents-10": [2],
  "transition-marble-left": [3, 9, 15, 20],
  "transition-marble-right": [3, 9, 15, 20],
  "content-text-2": [5, 6], "content-text-3": [4, 5], "content-text-4": [6, 8, 12, 22, 24],
  "content-focus-1": [10, 21], "content-image-1": [19], "content-metrics-4": [11, 14, 18, 23],
  "end-marble-frame": [25], "end-action": [25],
};

function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function createSlide(id, type, options = {}) {
  return {
    id,
    type,
    elements: [],
    background: { type: "solid", color: COLORS.white },
    sourceReferenceSlides: REFERENCE[id] || [],
    sourceFidelity: {
      mustMatchReferenceStyle: true,
      preserve: options.preserve || ["blue_ivory_fluid_marble", "white_content_plane", "source_page_rhythm", "source_spacing"],
      deviations: options.deviations || [],
    },
    remark: [
      "[Sources]",
      "- Visual style source: C:\\Users\\sk20\\Desktop\\创意风格 (56).pptx",
      "- Source media excluded; project assets generated with built-in GPT2 image template",
      "- Final output must preserve the original image and PPT visual style",
    ].join("\n"),
    ...(options.allowedItemCounts ? { allowedItemCounts: options.allowedItemCounts } : {}),
    ...(options.layoutKind ? { layoutKind: options.layoutKind } : {}),
    ...(options.titleFitLimits ? { titleFitLimits: options.titleFitLimits } : {}),
    __counter: 0,
  };
}

function nextId(slide, role) {
  slide.__counter += 1;
  return `t21-${slide.id}-${role}-${String(slide.__counter).padStart(3, "0")}`;
}

function image(slide, role, src, left, top, width, height, options = {}) {
  return {
    type: "image", id: nextId(slide, role), src, left, top, width, height,
    rotate: options.rotate || 0, fixedRatio: options.fixedRatio ?? false,
    imageType: options.imageType || "decoration", lock: options.lock ?? true,
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(options.clip ? { clip: options.clip } : {}),
    ...(options.strictImageCount ? { strictImageCount: true } : {}),
    ...(options.requireSourceDimensions ? { requireSourceDimensions: true } : {}),
    ...(options.originalWidth ? { originalWidth: options.originalWidth } : {}),
    ...(options.originalHeight ? { originalHeight: options.originalHeight } : {}),
  };
}

function shape(slide, role, left, top, width, height, fill, options = {}) {
  return {
    type: "shape", id: nextId(slide, role), left, top, width, height,
    viewBox: [200, 200], path: "M 0 0 L 200 0 L 200 200 L 0 200 Z",
    fill, fixedRatio: false, rotate: options.rotate || 0,
    outline: { color: options.outline || fill, width: options.outlineWidth ?? 0, style: "solid" },
    lock: options.lock ?? true, ...(options.groupId ? { groupId: options.groupId } : {}),
  };
}

function line(slide, role, left, top, length, color = COLORS.blue, width = 2) {
  return { type: "line", id: nextId(slide, role), left, top, start: [0, 0], end: [length, 0], points: ["", ""], color, style: "solid", width, rotate: 0, lock: true };
}

function text(slide, role, value, left, top, width, height, options = {}) {
  const fontSize = options.fontSize || 18;
  const color = options.color || COLORS.gray;
  const font = options.font || "微软雅黑";
  const align = options.align || "left";
  const weight = options.bold ? "font-weight: 700;" : "";
  // 显示与后端容量估算共用行高，防止默认文字未换字时被误判溢出。
  const lineHeight = options.textLineHeight || options.lineHeight || 1.25;
  return {
    type: "text", id: nextId(slide, role), left, top, width, height, rotate: options.rotate || 0,
    defaultFontName: font, defaultColor: color,
    content: `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: ${font};line-height: ${lineHeight};${weight}">${escapeHtml(value)}</span></p>`,
    ...(options.textType ? { textType: options.textType } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(options.minimumFontSize ? { minimumFontSize: options.minimumFontSize } : {}),
    textLineHeight: lineHeight,
  };
}

function addHeader(slide, titleValue) {
  slide.elements.push(
    text(slide, "title", titleValue, 72, 28, 700, 86, { fontSize: 35, color: COLORS.blue, bold: true, textType: "title", minimumFontSize: 35, textLineHeight: 1.1 }),
    line(slide, "header-rule", 72, 112, 100, COLORS.blue, 3),
  );
}

function addCorner(slide, position = "right") {
  slide.elements.push(image(slide, `corner-${position}`, ASSETS.corner, position === "right" ? 720 : -120, position === "right" ? 360 : -40, 400, 300, { rotate: position === "right" ? 0 : 180 }));
}

function cover(id, minimal = false) {
  const slide = createSlide(id, "cover", { preserve: ["source_cover_frame", "blue_ivory_fluid_marble", "white_title_safe_center", "cover_end_symmetry"], titleFitLimits: { maxWide: 18, maxAscii: 40, singleWide: 9, singleAscii: 20 } });
  slide.elements.push(
    image(slide, "background", ASSETS.cover, 0, 0, 1000, 562.5),
    shape(slide, "title-frame", 220, 104, 560, 340, COLORS.white, { outline: COLORS.blue, outlineWidth: 2 }),
    text(slide, "english-label", "BUSINESS REVIEW", 300, 128, 400, 28, { font: "Arial", fontSize: 16, color: COLORS.blue, bold: true, align: "center" }),
    text(slide, "title", minimal ? "业务汇报" : "蓝米流纹商务汇报", 200, 170, 600, 150, { fontSize: 54, color: COLORS.blue, bold: true, align: "center", textType: "title", minimumFontSize: 50, textLineHeight: 1.05 }),
    // 为两行中文副标题保留高度，保持字号下限及下方装饰线的位置不变。
    text(slide, "content", "以清晰结构承载业务表达", 285, 320, 430, 72, { fontSize: 18, color: COLORS.gray, align: "center", textType: "content", minimumFontSize: 16 }),
    line(slide, "bottom-rule", 390, 395, 220, COLORS.blue, 2),
  );
  return slide;
}

function contents(count) {
  const slide = createSlide(`contents-${count}`, "contents", { allowedItemCounts: [count], preserve: ["source_contents_rhythm", "edge_marble", "white_content_plane"] });
  slide.elements.push(image(slide, "background", ASSETS.content, 0, 0, 1000, 562.5), text(slide, "contents-label", "CONTENTS", 72, 150, 300, 72, { font: "Arial", fontSize: 52, color: COLORS.blue, bold: true }), text(slide, "title", "目录", 72, 230, 240, 82, { fontSize: 35, color: COLORS.black, bold: true, textType: "title", minimumFontSize: 35, textLineHeight: 1.1 }));
  const columns = count > 6 ? 2 : 1;
  const rows = Math.ceil(count / columns);
  // 六项目录也为两行中文保留完整高度，避免换行后触发最小字号保护。
  const itemHeight = 60;
  for (let index = 0; index < count; index += 1) {
    const column = Math.floor(index / rows); const row = index % rows;
    const x = 460 + column * 250; const y = 112 + row * itemHeight;
    const groupId = `contents-${count}-item-${index + 1}`;
    slide.elements.push(shape(slide, `dot-${index + 1}`, x, y + 12, 12, 12, COLORS.blue, { groupId }), text(slide, `item-${index + 1}`, `目录项目 ${index + 1}`, x + 24, y, 205, 56, { fontSize: 18, color: COLORS.blue, bold: true, textType: "item", groupId, minimumFontSize: 14, textLineHeight: 1.1 }));
  }
  return slide;
}

function transition(id, side = "left") {
  const slide = createSlide(id, "transition", { preserve: ["source_section_focus", "single_marble_slice", "continuous_whitespace"] });
  slide.elements.push(image(slide, "background", ASSETS.section, 0, 0, 1000, 562.5), image(slide, "tile", ASSETS.blueTile, side === "left" ? 70 : 680, 130, 210, 300, { rotate: side === "left" ? 0 : 180 }), shape(slide, "frame", side === "left" ? 240 : 120, 104, 660, 350, "rgba(255,255,255,0)", { outline: COLORS.blue, outlineWidth: 2 }), text(slide, "part", "PART 01", side === "left" ? 480 : 190, 175, 240, 50, { font: "Arial", fontSize: 30, color: COLORS.blue, textType: "partNumber" }), text(slide, "title", "章节标题", side === "left" ? 480 : 190, 250, 380, 66, { fontSize: 42, color: COLORS.black, bold: true, textType: "title" }), text(slide, "content", "章节说明文字", side === "left" ? 480 : 190, 330, 380, 60, { fontSize: 18, color: COLORS.gray, textType: "content" }));
  return slide;
}

function contentText(count) {
  const slide = createSlide(`content-text-${count}`, "content", { allowedItemCounts: [count], preserve: ["source_content_spacing", "blue_title_hierarchy", "white_content_plane"] });
  slide.elements.push(image(slide, "background", ASSETS.content, 0, 0, 1000, 562.5));
  addHeader(slide, "页面标题");
  // 利用下方留白容纳四行中文正文；两行项目间保留间距，不降低字号或放宽分页保护。
  const columns = count > 2 ? 2 : count; const rows = Math.ceil(count / columns); const gapX = 430; const baseX = 84; const baseY = 155; const rowH = 170;
  for (let index = 0; index < count; index += 1) { const col = Math.floor(index / rows); const row = index % rows; const x = baseX + col * gapX; const y = baseY + row * rowH; const groupId = `content-text-${count}-item-${index + 1}`; slide.elements.push(image(slide, `tile-${index + 1}`, ASSETS.blueTile, x, y, 82, 82, { groupId }), text(slide, `item-title-${index + 1}`, `内容项标题 ${index + 1}`, x + 106, y + 4, 260, 48, { fontSize: count >= 3 ? 18 : 22, color: COLORS.blue, bold: true, textType: "itemTitle", groupId, minimumFontSize: count >= 3 ? 14 : 18, textLineHeight: 1.1 }), text(slide, `item-${index + 1}`, "内容项正文示例，保留完整表达并支持后续分页。", x + 106, y + 54, 280, 66, { fontSize: 16, color: COLORS.gray, textType: "item", groupId, minimumFontSize: 14 })); }
  for (const element of slide.elements) {
    if (element.textType === "item") element.height = 110;
  }
  return slide;
}

function contentImage() {
  const slide = createSlide("content-image-1", "content", { preserve: ["source_content_image_composition", "business_image_slot", "fixed_decoration_layer"] });
  slide.elements.push(image(slide, "background", ASSETS.content, 0, 0, 1000, 562.5));
  addHeader(slide, "图文页面");
  slide.elements.push(text(slide, "itemTitle", "图文内容标题", 80, 150, 300, 42, { fontSize: 24, color: COLORS.blue, bold: true, textType: "itemTitle", groupId: "content-image-1-item-1" }), text(slide, "item", "图文内容正文示例，业务图片可替换，固定流纹装饰保持不变。", 80, 205, 300, 110, { fontSize: 18, color: COLORS.gray, textType: "item", groupId: "content-image-1-item-1" }), image(slide, "content-image", ASSETS.cover, 470, 138, 420, 290, { imageType: "content", lock: false, strictImageCount: true, requireSourceDimensions: true, originalWidth: 1672, originalHeight: 941, groupId: "content-image-1-item-1" }), image(slide, "corner", ASSETS.corner, 720, 370, 300, 220));
  return slide;
}

function focus() { const s = createSlide("content-focus-1", "content"); s.elements.push(image(s, "background", ASSETS.content, 0, 0, 1000, 562.5)); addHeader(s, "单项结论"); s.elements.push(text(s, "itemTitle", "核心结论标题", 90, 190, 820, 70, { fontSize: 42, color: COLORS.blue, bold: true, textType: "itemTitle", align: "center", groupId: "focus-item-1" }), text(s, "item", "结论说明文字。", 160, 290, 680, 80, { fontSize: 20, color: COLORS.gray, textType: "item", align: "center", groupId: "focus-item-1" })); return s; }

function metrics() { const s = createSlide("content-metrics-4", "content"); s.elements.push(image(s, "background", ASSETS.content, 0, 0, 1000, 562.5)); addHeader(s, "指标概览"); for(let i=0;i<4;i+=1){const x=100+(i%2)*420,y=155+Math.floor(i/2)*170,g=`metrics-${i+1}`;s.elements.push(text(s,`metric-title-${i+1}`,`指标 ${i+1}`,x,y,180,30,{fontSize:18,color:COLORS.blue,bold:true,textType:"itemTitle",groupId:g}),text(s,`metric-value-${i+1}`,`${65+i*7}%`,x,y+40,180,56,{font:"Arial",fontSize:36,color:COLORS.blue,bold:true,textType:"itemNumber",groupId:g}),shape(s,`metric-bar-bg-${i+1}`,x,y+112,300,12,COLORS.lightGray,{groupId:g}),shape(s,`metric-bar-${i+1}`,x,y+112,190+i*25,12,COLORS.blue2,{groupId:g}));} return s; }

function end(id = "end-marble-frame") {
  const s = createSlide(id, "end", { preserve: ["source_end_cover_symmetry", "white_title_frame", "fluid_marble_edges"] });
  // 默认结束语可能不经过动态换字，必须显式声明与显示一致的行高。
  s.elements.push(
    image(s, "background", ASSETS.end, 0, 0, 1000, 562.5),
    shape(s, "frame", 220, 104, 560, 340, COLORS.white, { outline: COLORS.blue, outlineWidth: 2 }),
    text(s, "title", "感谢观看", 290, 210, 420, 90, { fontSize: 54, color: COLORS.blue, bold: true, align: "center", textType: "title", textLineHeight: 1.1 }),
    text(s, "content", "谢谢", 350, 320, 300, 48, { fontSize: 20, color: COLORS.gray, align: "center", textType: "content", textLineHeight: 1.25 }),
  );
  return s;
}

function build(stage) {
  const probe = [cover("cover-marble-frame"), contentText(4), contentImage()];
  const mvp = [cover("cover-marble-frame"), ...[2,3,4,5,6,10].map(contents), transition("transition-marble-left"), contentText(2), contentText(3), contentText(4), end()];
  const production = [...mvp, cover("cover-marble-minimal", true), transition("transition-marble-right", "right"), focus(), contentImage(), metrics(), end("end-action")];
  const slides = stage === "probe" ? probe : stage === "mvp" ? mvp : production;
  // 为默认单行语义文字补足真实高度；这些槽位下方均预留了独立空间。
  for (const slide of slides) {
    for (const element of slide.elements) {
      if (slide.type === "transition" && element.textType === "title") element.height = 74;
      if (slide.type === "transition" && element.textType === "partNumber") element.height = 60;
      if (slide.id === "content-focus-1" && element.textType === "itemTitle") element.height = 74;
      if (slide.id === "content-image-1" && element.textType === "itemTitle") element.height = 52;
      if (slide.id === "content-metrics-4" && element.textType === "itemTitle") element.height = 44;
      if (slide.id === "content-metrics-4" && element.textType === "itemNumber") {
        element.top += 6;
        element.height = 65;
      }
    }
  }
  const clean = slides.map(({ __counter, ...slide }) => slide);
  const metadata = {
    aspectRatio: "16:9", buildStage: stage, sourceReference: "创意风格 (56).pptx",
    sourceReferenceSha256: "EE80AB40B1E168B3713E42A18EA7176C2A7AA38772E58151285A4CE2D72A543C",
    rightsPolicy: "reference-media-excluded", sourceFidelity: "must-match-reference-style-composition-color-texture-spacing-rhythm",
    probeSlideIds: ["cover-marble-frame", "content-text-4", "content-image-1"],
    mvpSlideIds: mvp.map(s => s.id), productionSlideIds: production.map(s => s.id),
    imageSlotMarker: "imageType=content", decorativeImageMarker: "imageType=decoration",
    assetGeneration: "GPT2 image template; actual model identifier recorded when exposed",
    assetFiles: ["template_21_asset_bg_cover_v2.jpg", "template_21_asset_bg_content_v1.jpg", "template_21_asset_bg_section_v1.jpg", "template_21_asset_bg_end_v1.jpg", "template_21_asset_marble_tile_blue_v1.jpg", "template_21_asset_marble_tile_ivory_v1.jpg", "template_21_asset_bottom_flow_v1.png", "template_21_asset_side_flow_v1.png", "template_21_asset_corner_flow_v1.png"],
  };
  return { id: "template_21", title: "蓝米流纹商务汇报", width: 1000, height: 562.5, supportsLosslessContentPagination: true, paginationGrowthPolicy: { factor: 1.75, slack: 5 }, theme: { themeColors: [COLORS.blue, COLORS.mist], fontColor: COLORS.black, fontName: "微软雅黑", backgroundColor: COLORS.white }, metadata, slides: clean };
}

const args = process.argv.slice(2);
const stageIndex = args.indexOf("--stage");
const stage = stageIndex >= 0 ? args[stageIndex + 1] : "production";
const output = args.find((value, index) => index !== stageIndex && index !== stageIndex + 1 && value.endsWith(".json")) || path.join(TEMPLATE_DIR, "template_21.json");
if (!["probe", "mvp", "production"].includes(stage)) throw new Error("--stage must be probe, mvp, or production");
fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
fs.writeFileSync(path.resolve(output), `${JSON.stringify(build(stage), null, 2)}\n`, "utf8");
console.log(path.resolve(output));

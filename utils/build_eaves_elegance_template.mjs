#!/usr/bin/env node

/**
 * 确定性构建“飞檐雅韵”PPTist 模板。
 *
 * 视觉来源：用户提供的《精品系列(2).pptx》。只复用构图、配色、留白和页面节奏，
 * 不复制参考媒体、非商业字体、音频、动画和原生图表。
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = path.resolve(SCRIPT_DIR, "..");

const COLORS = {
  background: "#F6F2EA",
  dustyRose: "#B77D80",
  ink: "#211B1C",
  tileGray: "#4D4D4B",
  body: "#4A4643",
  cinnabar: "#A83F36",
  mutedGold: "#B6925F",
  paleRose: "#E9DADB",
  white: "#FFFFFF",
};

const ASSETS = {
  coverBackground: "/api/data/template_18_asset_bg_cover_v1.jpg",
  sectionBackground: "/api/data/template_18_asset_bg_section_v1.jpg",
  endBackground: "/api/data/template_18_asset_bg_end_v1.jpg",
  roofBand: "/api/data/template_18_asset_rooftile_band_v1.png",
  eavesCorner: "/api/data/template_18_asset_eaves_corner_v1.png",
  plumBranch: "/api/data/template_18_asset_plum_branch_v1.png",
  cranePair: "/api/data/template_18_asset_crane_pair_v1.png",
  medallion: "/api/data/template_18_asset_medallion_v1.png",
};

const MVP_IDS = [
  "cover-rooftile",
  "contents-2",
  "contents-3",
  "contents-4",
  "contents-5",
  "contents-6",
  "contents-10",
  "transition-rose-band",
  "content-text-2",
  "content-text-3",
  "content-text-4",
  "end-rooftile",
];

const PRODUCTION_IDS = [
  "cover-rooftile",
  "cover-eaves",
  "contents-2",
  "contents-3",
  "contents-4",
  "contents-5",
  "contents-6",
  "contents-10",
  "transition-rose-band",
  "transition-medallion",
  "content-statement-1",
  "content-image-1",
  "content-text-2",
  "content-text-3",
  "content-text-4",
  "content-metrics-4",
  "end-rooftile",
  "end-action",
];

const SAMPLE_IDS = [
  "cover-rooftile",
  "contents-4",
  "transition-rose-band",
  "content-text-2",
  "end-rooftile",
];

const REFERENCE_SLIDES = {
  "cover-rooftile": [1],
  "cover-eaves": [1, 8, 25],
  "contents-2": [2],
  "contents-3": [2],
  "contents-4": [2],
  "contents-5": [2],
  "contents-6": [2],
  "contents-10": [2],
  "transition-rose-band": [3, 9, 15, 21],
  "transition-medallion": [3, 9, 15, 21],
  "content-statement-1": [4, 13, 20, 25],
  "content-image-1": [5, 8],
  "content-text-2": [7, 10, 18, 24],
  "content-text-3": [12, 17, 19],
  "content-text-4": [6, 14, 22, 24],
  "content-metrics-4": [22],
  "end-rooftile": [26],
  "end-action": [26, 17],
};


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}


function createSlide(id, type, options = {}) {
  return {
    id,
    type,
    elements: [],
    background: { type: "solid", color: COLORS.background },
    sourceReferenceSlides: REFERENCE_SLIDES[id] || [],
    sourceFidelity: {
      preserve: options.preserve || [],
      deviations: options.deviations || [],
    },
    remark: [
      "[Sources]",
      "- Visual composition reference: user-provided 精品系列(2).pptx",
      "- Reference media excluded; original project assets generated with built-in imagegen",
      "- Actual image model identifier was not exposed by the tool",
    ].join("\n"),
    ...(options.allowedItemCounts ? { allowedItemCounts: options.allowedItemCounts } : {}),
    ...(options.layoutKind ? { layoutKind: options.layoutKind } : {}),
    ...(options.variantMode ? { variantMode: options.variantMode } : {}),
    ...(options.titleFitLimits ? { titleFitLimits: options.titleFitLimits } : {}),
    __counter: 0,
  };
}


function nextId(slide, role) {
  slide.__counter += 1;
  return `t18-${slide.id}-${role}-${String(slide.__counter).padStart(3, "0")}`;
}


function image(slide, role, src, left, top, width, height, options = {}) {
  return {
    type: "image",
    id: nextId(slide, role),
    src,
    left,
    top,
    width,
    height,
    rotate: options.rotate || 0,
    fixedRatio: options.fixedRatio ?? false,
    imageType: options.imageType || "decoration",
    lock: options.lock ?? true,
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(options.clip ? { clip: options.clip } : {}),
    ...(options.strictImageCount ? { strictImageCount: true } : {}),
    ...(options.requireSourceDimensions ? { requireSourceDimensions: true } : {}),
    ...(options.originalWidth ? { originalWidth: options.originalWidth } : {}),
    ...(options.originalHeight ? { originalHeight: options.originalHeight } : {}),
  };
}


function shape(slide, role, left, top, width, height, fill, options = {}) {
  const ellipse = options.ellipse === true;
  return {
    type: "shape",
    id: nextId(slide, role),
    left,
    top,
    width,
    height,
    viewBox: [200, 200],
    path: ellipse
      ? "M 100 0 A 100 100 0 1 1 100 200 A 100 100 0 1 1 100 0 Z"
      : "M 0 0 L 200 0 L 200 200 L 0 200 Z",
    fill,
    fixedRatio: false,
    rotate: options.rotate || 0,
    outline: {
      color: options.outline || fill,
      width: options.outlineWidth ?? 0,
      style: "solid",
    },
    lock: options.lock ?? true,
    ...(options.rounded && !ellipse ? { pathFormula: "roundRect", keypoints: [0.08] } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
  };
}


function line(slide, role, left, top, length, color = COLORS.dustyRose, width = 2) {
  return {
    type: "line",
    id: nextId(slide, role),
    left,
    top,
    start: [0, 0],
    end: [length, 0],
    points: ["", ""],
    color,
    style: "solid",
    width,
    rotate: 0,
    lock: true,
  };
}


function text(slide, role, value, left, top, width, height, options = {}) {
  const fontSize = options.fontSize || 18;
  const color = options.color || COLORS.body;
  const font = options.font || "微软雅黑";
  const align = options.align || "left";
  const weight = options.bold ? "font-weight: 700;" : "";
  const tracking = Number.isFinite(options.letterSpacing)
    ? `letter-spacing: ${options.letterSpacing}px;`
    : "";
  return {
    type: "text",
    id: nextId(slide, role),
    left,
    top,
    width,
    height,
    rotate: options.rotate || 0,
    defaultFontName: font,
    defaultColor: color,
    vertical: options.vertical || false,
    content: `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: ${font};line-height: ${options.lineHeight || 1.35};${weight}${tracking}">${escapeHtml(value)}</span></p>`,
    ...(options.textType ? { textType: options.textType } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(options.minimumFontSize ? { minimumFontSize: options.minimumFontSize } : {}),
    ...(options.textLineHeight ? { textLineHeight: options.textLineHeight } : {}),
    ...(options.textWidthFactor ? { textWidthFactor: options.textWidthFactor } : {}),
  };
}


function addContentHeader(slide, titleValue = "飞檐雅韵内容结构", part = "壹") {
  slide.elements.push(
    text(slide, "part-mark", part, 0, 24, 58, 54, {
      fontSize: 44,
      color: COLORS.dustyRose,
      font: "微软雅黑",
      align: "center",
    }),
    text(slide, "page-title", titleValue, 78, 34, 700, 82, {
      fontSize: 35,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 35,
    }),
    line(slide, "title-line", 78, 120, 650, COLORS.dustyRose, 1.5),
    image(slide, "header-plum", ASSETS.plumBranch, 720, 2, 250, 102, { fixedRatio: true }),
  );
}


function coverRooftile() {
  const slide = createSlide("cover-rooftile", "cover", {
    preserve: ["roof-tile visual weight", "plum branches", "four-circle title rhythm", "large upper whitespace"],
    deviations: ["source media replaced", "single editable title spans four native circles"],
    titleFitLimits: { maxWide: 24, maxAscii: 48, singleWide: 12, singleAscii: 24 },
  });
  slide.elements.push(image(slide, "background", ASSETS.coverBackground, 0, 0, 1000, 562.5));
  const circleLefts = [95, 300, 505, 710];
  for (const left of circleLefts) {
    slide.elements.push(shape(slide, "title-circle", left, 224, 142, 142, COLORS.ink, { ellipse: true }));
  }
  for (const [index, character] of [..."飞檐雅韵"].entries()) {
    slide.elements.push(text(slide, "brand-character", character, circleLefts[index], 253, 142, 78, {
      fontSize: 48,
      color: COLORS.white,
      align: "center",
      bold: true,
    }));
  }
  slide.elements.push(
    shape(slide, "subtitle-panel", 240, 378, 520, 160, "rgba(246,242,234,0.94)", {
      outline: COLORS.ink,
      outlineWidth: 2,
      rounded: true,
    }),
    shape(slide, "subtitle-node", 260, 430, 42, 42, COLORS.cinnabar, { ellipse: true }),
    text(slide, "title", "东方古建主题演示", 320, 382, 420, 78, {
      fontSize: 35,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 35,
    }),
    text(slide, "subtitle", "让东方意境承载清晰表达", 320, 462, 420, 72, {
      fontSize: 15,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 14,
    }),
  );
  return slide;
}


function coverEaves() {
  const slide = createSlide("cover-eaves", "cover", {
    preserve: ["ancient architecture corner weight", "warm ivory whitespace", "asymmetric image balance"],
    deviations: ["source media replaced", "business image slot added for production use"],
    titleFitLimits: { maxWide: 24, maxAscii: 48, singleWide: 15, singleAscii: 30 },
  });
  const groupId = "cover-eaves-content-image-1";
  slide.elements.push(
    image(slide, "background", ASSETS.sectionBackground, 0, 0, 1000, 562.5),
    shape(slide, "image-backing", 76, 148, 390, 252, COLORS.paleRose, { rounded: true }),
    image(slide, "content-image", ASSETS.sectionBackground, 94, 166, 354, 216, {
      imageType: "content",
      lock: false,
      strictImageCount: true,
      requireSourceDimensions: true,
      originalWidth: 1920,
      originalHeight: 1080,
      groupId,
      clip: { shape: "rect", range: [[0, 0], [100, 100]] },
    }),
    text(slide, "title", "飞檐雅韵", 510, 178, 390, 110, {
      fontSize: 50,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 50,
    }),
    line(slide, "title-line", 514, 300, 300, COLORS.dustyRose, 2),
    text(slide, "subtitle", "用古建秩序承载当代表达", 515, 323, 360, 80, {
      fontSize: 18,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  return slide;
}


function contentsSlide(count) {
  const slide = createSlide(`contents-${count}`, "contents", {
    preserve: ["dusty-rose vertical rail", "sparse index rhythm", "large warm-ivory whitespace"],
    deviations: ["source mountain media replaced", "horizontal editable contents"],
    allowedItemCounts: [count],
  });
  slide.elements.push(
    shape(slide, "rose-rail", 755, 0, 175, 562.5, COLORS.dustyRose),
    image(slide, "rail-medallion", ASSETS.medallion, 774, 66, 138, 138, { fixedRatio: true }),
    text(slide, "contents-label", "目录", 810, 250, 60, 100, {
      fontSize: 40,
      color: COLORS.white,
      bold: true,
      vertical: true,
      align: "center",
    }),
    image(slide, "roof-band", ASSETS.roofBand, 0, 444, 755, 118.5, { fixedRatio: false }),
  );

  const columns = count <= 3 ? 1 : 2;
  const rows = Math.ceil(count / columns);
  const lefts = columns === 1 ? [165] : [80, 395];
  const rowGap = Math.min(86, 300 / Math.max(1, rows - 1));
  const startTop = rows === 1 ? 242 : 145;
  for (let index = 0; index < count; index += 1) {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const left = lefts[column];
    const top = startTop + row * rowGap;
    const groupId = `contents-${count}-item-${index + 1}`;
    slide.elements.push(
      text(slide, "item-number", String(index + 1).padStart(2, "0"), left, top, 48, 46, {
        font: "Arial",
        fontSize: 16,
        color: COLORS.dustyRose,
        bold: true,
        textType: "itemNumber",
        groupId,
      }),
      line(slide, "item-line", left + 48, top + 18, 28, COLORS.mutedGold, 1),
      text(slide, "item", `目录项目 ${index + 1}`, left + 86, top - 4, columns === 1 ? 430 : 220, 48, {
        fontSize: rows >= 5 ? 16 : 18,
        color: COLORS.ink,
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
    );
  }
  return slide;
}


function transitionRoseBand() {
  const slide = createSlide("transition-rose-band", "transition", {
    preserve: ["dusty-rose vertical band", "medallion", "eaves lower right", "plum upper right", "short vertical chapter title"],
    deviations: ["source media replaced", "body copy made horizontal for readability"],
    variantMode: "deterministic",
  });
  slide.elements.push(
    image(slide, "background", ASSETS.sectionBackground, 0, 0, 1000, 562.5),
    shape(slide, "rose-band", 138, 0, 260, 562.5, COLORS.dustyRose),
    shape(slide, "text-safe-panel", 440, 130, 315, 320, "rgba(246,242,234,0.95)", {
      rounded: true,
      outline: "rgba(246,242,234,0.95)",
      outlineWidth: 0,
    }),
    image(slide, "medallion", ASSETS.medallion, 178, 75, 180, 180, { fixedRatio: true }),
    text(slide, "part-number", "第壹章", 235, 292, 66, 170, {
      fontSize: 44,
      color: COLORS.white,
      bold: true,
      vertical: true,
      align: "center",
      textType: "partNumber",
      minimumFontSize: 35,
    }),
    text(slide, "title", "章节标题", 470, 145, 410, 130, {
      fontSize: 44,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 44,
      textLineHeight: 1.2,
    }),
    line(slide, "title-line", 470, 285, 260, COLORS.dustyRose, 2),
    text(slide, "content", "用一段简洁说明承接上一章节，并为下一部分建立清晰语境。", 472, 310, 250, 120, {
      fontSize: 18,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  return slide;
}


function transitionMedallion() {
  const slide = createSlide("transition-medallion", "transition", {
    preserve: ["medallion focal point", "architecture corner", "asymmetric whitespace"],
    deviations: ["source vertical body removed", "editable horizontal title and summary"],
    variantMode: "deterministic",
  });
  slide.elements.push(
    image(slide, "medallion", ASSETS.medallion, 80, 112, 275, 275, { fixedRatio: true }),
    image(slide, "eaves", ASSETS.eavesCorner, 700, 345, 300, 217.5, { fixedRatio: true }),
    image(slide, "plum", ASSETS.plumBranch, 645, 20, 305, 124, { fixedRatio: true }),
    text(slide, "part-number", "02", 390, 148, 90, 68, {
      font: "Arial",
      fontSize: 28,
      color: COLORS.dustyRose,
      bold: true,
      textType: "partNumber",
    }),
    text(slide, "title", "章节标题", 390, 205, 540, 130, {
      fontSize: 44,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 38,
      textLineHeight: 1.2,
    }),
    text(slide, "content", "以古典纹章和飞檐关系建立章节转换。", 394, 350, 280, 90, {
      fontSize: 18,
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  return slide;
}


function statementSlide() {
  const slide = createSlide("content-statement-1", "content", {
    preserve: ["single conclusion focus", "large whitespace", "architecture corner"],
    deviations: ["vertical body changed to horizontal editable statement"],
    allowedItemCounts: [1],
    layoutKind: "text",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  addContentHeader(slide, "核心结论", "壹");
  slide.elements.push(
    shape(slide, "statement-rail", 104, 164, 10, 245, COLORS.dustyRose),
    text(slide, "statement-title", "让核心观点成为页面唯一重心", 150, 176, 590, 100, {
      fontSize: 32,
      color: COLORS.ink,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 24,
      groupId: "content-statement-1-item-1",
    }),
    text(slide, "statement-body", "单项内容页用于承载结论、引语或摘要。装饰保持克制，正文获得足够空间。", 154, 300, 525, 150, {
      fontSize: 18,
      textType: "item",
      minimumFontSize: 16,
      groupId: "content-statement-1-item-1",
    }),
    image(slide, "eaves", ASSETS.eavesCorner, 700, 230, 300, 225, { fixedRatio: true }),
  );
  return slide;
}


function imageContentSlide() {
  const slide = createSlide("content-image-1", "content", {
    preserve: ["one image plus one text block", "soft rose image backing", "circular image language from reference slide 19", "crane decoration"],
    deviations: ["source content image replaced with a semantic circular image slot"],
    allowedItemCounts: [1],
    layoutKind: "1-image-text",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  addContentHeader(slide, "图文内容", "贰");
  const groupId = "content-image-1-item-1";
  slide.elements.push(
    shape(slide, "rose-backing", 0, 140, 1000, 230, COLORS.paleRose),
    shape(slide, "image-ring", 114, 144, 222, 222, "rgba(255,255,255,0)", {
      ellipse: true,
      outline: COLORS.mutedGold,
      outlineWidth: 3,
    }),
    image(slide, "content-image", ASSETS.sectionBackground, 124, 154, 202, 202, {
      imageType: "content",
      lock: false,
      strictImageCount: true,
      requireSourceDimensions: true,
      originalWidth: 1920,
      originalHeight: 1080,
      groupId,
      clip: { shape: "ellipse", range: [[0, 0], [100, 100]] },
    }),
    text(slide, "item-number", "01", 430, 175, 52, 38, {
      font: "Arial",
      fontSize: 18,
      color: COLORS.dustyRose,
      bold: true,
      textType: "itemNumber",
      groupId,
    }),
    text(slide, "item-title", "输入标题内容", 488, 168, 370, 62, {
      fontSize: 24,
      color: COLORS.ink,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 24,
      groupId,
    }),
    text(slide, "item-body", "业务图片与正文保持清晰分区，固定双鹤装饰不会被换图覆盖。", 432, 245, 425, 104, {
      fontSize: 17,
      textType: "item",
      minimumFontSize: 16,
      groupId,
    }),
    image(slide, "cranes", ASSETS.cranePair, 650, 350, 290, 184, { fixedRatio: true }),
  );
  return slide;
}


function textItemsSlide(count) {
  const slide = createSlide(`content-text-${count}`, "content", {
    preserve: [`${count}-item rhythm`, "large whitespace", "lightweight numbering"],
    deviations: ["narrow vertical body changed to horizontal editable text"],
    allowedItemCounts: [count],
    layoutKind: "text",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  addContentHeader(slide, "飞檐雅韵内容结构", count === 2 ? "贰" : count === 3 ? "叁" : "肆");
  const columns = count === 2 ? 2 : count === 3 ? 3 : 2;
  const rows = Math.ceil(count / columns);
  const width = columns === 3 ? 250 : 390;
  const gap = columns === 3 ? 50 : 80;
  const startLeft = columns === 3 ? 75 : 80;
  for (let index = 0; index < count; index += 1) {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const left = startLeft + column * (width + gap);
    const top = rows === 1 ? 178 : 152 + row * 185;
    const bodyHeight = rows === 1 ? 210 : 78;
    const groupId = `content-text-${count}-item-${index + 1}`;
    slide.elements.push(
      text(slide, "item-number", String(index + 1).padStart(2, "0"), left, top, 48, 46, {
        font: "Arial",
        fontSize: 18,
        color: COLORS.dustyRose,
        bold: true,
        textType: "itemNumber",
        groupId,
      }),
      line(slide, "item-line", left + 52, top + 18, 34, COLORS.mutedGold, 1),
      text(slide, "item-title", `内容标题 ${index + 1}`, left + 96, top - 6, width - 96, 60, {
        fontSize: 24,
        color: COLORS.ink,
        bold: true,
        textType: "itemTitle",
        minimumFontSize: 24,
        groupId,
      }),
      text(slide, "item-body", "在此输入完整说明，保持观点、证据与行动之间的清晰关系。", left + 4, top + 74, width - 8, bodyHeight, {
        fontSize: 17,
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
    );
  }
  if (count === 2) {
    slide.elements.push(image(slide, "eaves", ASSETS.eavesCorner, 0, 350, 283.33, 212.5, { fixedRatio: true }));
  }
  if (count === 3) {
    slide.elements.push(image(slide, "medallion", ASSETS.medallion, 720, 335, 175, 175, { fixedRatio: true }));
  }
  if (count === 4) {
    // 四项正文的内容区延伸到页面下半部，双鹤缩小并沉到右下安全区，避免压住第 4 项正文。
    slide.elements.push(image(slide, "cranes", ASSETS.cranePair, 840, 490, 110, 70, { fixedRatio: true }));
  }
  return slide;
}


function metricsSlide() {
  const slide = createSlide("content-metrics-4", "content", {
    preserve: ["four evenly spaced metrics", "gold circular rhythm", "left visual accent"],
    deviations: ["native charts replaced with editable text and shapes"],
    allowedItemCounts: [4],
    layoutKind: "metrics",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  addContentHeader(slide, "四项核心指标", "肆");
  slide.elements.push(image(slide, "eaves", ASSETS.eavesCorner, 0, 320, 280, 210, { fixedRatio: true }));
  for (let index = 0; index < 4; index += 1) {
    const left = 280 + index * 170;
    const groupId = `content-metrics-4-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "metric-ring", left, 160, 112, 112, "rgba(255,255,255,0)", {
        ellipse: true,
        outline: COLORS.mutedGold,
        outlineWidth: 12,
        groupId,
      }),
      text(slide, "metric-number", String(index + 1).padStart(2, "0"), left + 25, 194, 62, 44, {
        font: "Arial",
        fontSize: 24,
        color: COLORS.ink,
        align: "center",
        bold: true,
        textType: "itemNumber",
        groupId,
      }),
      text(slide, "metric-title", `指标 ${index + 1}`, left - 10, 292, 132, 68, {
        fontSize: 24,
        color: COLORS.ink,
        align: "center",
        bold: true,
        textType: "itemTitle",
        minimumFontSize: 24,
        groupId,
      }),
      text(slide, "metric-body", "指标说明", left - 10, 365, 132, 104, {
        fontSize: 16,
        color: COLORS.body,
        align: "center",
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
    );
  }
  return slide;
}


function endRooftile() {
  const slide = createSlide("end-rooftile", "end", {
    preserve: ["roof-tile visual weight", "four-circle closing rhythm", "plum branches", "cover-end symmetry"],
    deviations: ["source media and fonts replaced", "editable closing title"],
  });
  slide.elements.push(image(slide, "background", ASSETS.endBackground, 0, 0, 1000, 562.5));
  const circleLefts = [95, 300, 505, 710];
  for (const left of circleLefts) {
    slide.elements.push(shape(slide, "title-circle", left, 250, 142, 142, COLORS.ink, { ellipse: true }));
  }
  for (const [index, character] of [..."感谢聆听"].entries()) {
    slide.elements.push(text(slide, "closing-character", character, circleLefts[index], 279, 142, 78, {
      fontSize: 48,
      color: COLORS.white,
      align: "center",
      bold: true,
    }));
  }
  slide.elements.push(
    shape(slide, "subtitle-panel", 300, 388, 400, 136, "rgba(246,242,234,0.94)", {
      rounded: true,
      outline: COLORS.ink,
      outlineWidth: 1,
    }),
    text(slide, "title", "期待下一次相见", 325, 392, 350, 78, {
      fontSize: 35,
      color: COLORS.ink,
      align: "center",
      bold: true,
      textType: "title",
      minimumFontSize: 35,
    }),
    text(slide, "content", "让东方意境留下余韵", 325, 476, 350, 44, {
      fontSize: 14,
      color: COLORS.ink,
      align: "center",
      textType: "content",
      minimumFontSize: 14,
    }),
  );
  return slide;
}


function endAction() {
  const slide = createSlide("end-action", "end", {
    preserve: ["cover-end symmetry", "three-step rhythm", "ancient architecture accents"],
    deviations: ["action items added as semantic groups"],
  });
  slide.elements.push(
    image(slide, "background", ASSETS.endBackground, 0, 0, 1000, 562.5),
    shape(slide, "safe-panel", 78, 92, 844, 405, "rgba(246,242,234,0.90)", {
      rounded: true,
      outline: COLORS.dustyRose,
      outlineWidth: 1,
    }),
    text(slide, "title", "下一步行动", 160, 112, 680, 96, {
      fontSize: 44,
      color: COLORS.ink,
      align: "center",
      bold: true,
      textType: "title",
      minimumFontSize: 44,
    }),
    text(slide, "content", "明确负责人、完成标准和复盘时间", 180, 205, 640, 56, {
      fontSize: 18,
      align: "center",
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  for (let index = 0; index < 3; index += 1) {
    const left = 135 + index * 255;
    const groupId = `end-action-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "action-card", left, 300, 220, 115, "rgba(255,255,255,0.88)", {
        rounded: true,
        outline: COLORS.dustyRose,
        outlineWidth: 1,
        groupId,
      }),
      shape(slide, "action-node", left + 18, 333, 48, 48, COLORS.dustyRose, {
        ellipse: true,
        groupId,
      }),
      text(slide, "action-number", String(index + 1).padStart(2, "0"), left + 18, 342, 48, 32, {
        font: "Arial",
        fontSize: 15,
        color: COLORS.white,
        align: "center",
        bold: true,
        groupId,
      }),
      text(slide, "action-item", `行动 ${index + 1}`, left + 82, 331, 116, 52, {
        fontSize: 17,
        color: COLORS.ink,
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
    );
  }
  return slide;
}


function finalizeSlide(slide) {
  delete slide.__counter;
  return slide;
}


function allSlides() {
  return [
    coverRooftile(),
    coverEaves(),
    contentsSlide(2),
    contentsSlide(3),
    contentsSlide(4),
    contentsSlide(5),
    contentsSlide(6),
    contentsSlide(10),
    transitionRoseBand(),
    transitionMedallion(),
    statementSlide(),
    imageContentSlide(),
    textItemsSlide(2),
    textItemsSlide(3),
    textItemsSlide(4),
    metricsSlide(),
    endRooftile(),
    endAction(),
  ].map(finalizeSlide);
}


function buildTemplate(stage) {
  const selectedIds = new Set(
    stage === "sample" ? SAMPLE_IDS : stage === "mvp" ? MVP_IDS : PRODUCTION_IDS,
  );
  const slides = allSlides().filter(slide => selectedIds.has(slide.id));
  const actual = new Set(slides.map(slide => slide.id));
  const missing = [...selectedIds].filter(id => !actual.has(id));
  if (missing.length) throw new Error(`模板缺少声明版式: ${missing.join(", ")}`);
  return {
    id: "template_18",
    title: "飞檐雅韵",
    width: 1000,
    height: 562.5,
    theme: {
      themeColors: [
        COLORS.dustyRose,
        COLORS.ink,
        COLORS.tileGray,
        COLORS.cinnabar,
        COLORS.mutedGold,
        COLORS.paleRose,
      ],
      fontColor: COLORS.body,
      fontName: "微软雅黑",
      backgroundColor: COLORS.background,
      shadow: { h: 2, v: 3, blur: 5, color: "#000000", opacity: 0.18 },
      outline: { width: 1, color: COLORS.dustyRose, style: "solid" },
    },
    metadata: {
      aspectRatio: "16:9",
      buildStage: stage,
      sourceReference: "精品系列(2).pptx",
      sourceReferenceSha256: "7433A07E7FD206D847EE01F1AC4B206E42416EB801D433DB60C2BBFC24E8CF8B",
      rightsPolicy: "reference-media-excluded",
      sourceFidelity: "high-composition-color-spacing-rhythm",
      mvpSlideIds: MVP_IDS,
      productionSlideIds: PRODUCTION_IDS,
      imageSlotMarker: "imageType=content",
      decorativeImageMarker: "imageType=decoration",
      assetGeneration: "built-in imagegen; requested GPT Image 2; actual model identifier not exposed",
      assetFiles: Object.values(ASSETS).map(value => value.split("/").at(-1)),
    },
    slides,
  };
}


function parseArgs(argv) {
  let stage = "production";
  let output = "";
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--stage") {
      stage = argv[index + 1] || "";
      index += 1;
    }
    else if (!output) output = argv[index];
  }
  if (!new Set(["sample", "mvp", "production"]).has(stage)) {
    throw new Error("--stage 只能是 sample、mvp 或 production");
  }
  if (!output) {
    throw new Error("用法: node utils/build_eaves_elegance_template.mjs [--stage sample|mvp|production] <输出JSON>");
  }
  return { stage, output: path.resolve(REPOSITORY_ROOT, output) };
}


try {
  const { stage, output } = parseArgs(process.argv.slice(2));
  const template = buildTemplate(stage);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(template, null, 2)}\n`, "utf8");
  process.stdout.write(`${output}\n`);
}
catch (error) {
  process.stderr.write(`${error.message || error}\n`);
  process.exit(1);
}

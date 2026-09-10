#!/usr/bin/env node

/**
 * 确定性构建“抽象油彩商务汇报”PPTist模板。
 *
 * 参考稿只提供构图、色彩、油彩质感和页面节奏。生产资源使用原创图片，
 * 文字、编号、形状和业务图片槽保持可编辑。
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = path.resolve(SCRIPT_DIR, "..");

const COLORS = {
  background: "#FFFFFF",
  teal: "#10746A",
  paintTeal: "#0E5A63",
  orange: "#FF9409",
  paintOrange: "#E4651E",
  yellow: "#FDC90E",
  black: "#000000",
  body: "#282828",
  gray: "#9C9C9C",
  pale: "#F4DEBD",
  white: "#FFFFFF",
};

const ASSETS = {
  coverBackground: "/api/data/template_20_asset_bg_cover_v1.jpg",
  contentBackground: "/api/data/template_20_asset_bg_content_v1.jpg",
  sectionBackground: "/api/data/template_20_asset_bg_section_v1.jpg",
  endBackground: "/api/data/template_20_asset_bg_end_v1.jpg",
  tealBrushBand: "/api/data/template_20_asset_teal_brush_band_v1.png",
  orangeBrushSweep: "/api/data/template_20_asset_orange_brush_sweep_v1.png",
  yellowHighlight: "/api/data/template_20_asset_yellow_highlight_v1.png",
  paintCorner: "/api/data/template_20_asset_paint_corner_v1.png",
  pigmentSpeckles: "/api/data/template_20_asset_pigment_speckles_v1.png",
};

const PROBE_IDS = ["cover-abstract-paint", "content-text-4", "content-image-1"];
const SAMPLE_IDS = [
  "cover-abstract-paint",
  "contents-4",
  "transition-teal-paint",
  "content-text-2",
  "end-abstract-paint",
];
const MVP_IDS = [
  "cover-abstract-paint",
  "contents-2",
  "contents-3",
  "contents-4",
  "contents-5",
  "contents-6",
  "contents-10",
  "transition-teal-paint",
  "content-text-2",
  "content-text-3",
  "content-text-4",
  "end-abstract-paint",
];
const PRODUCTION_IDS = [
  "cover-abstract-paint",
  "cover-image",
  "contents-2",
  "contents-3",
  "contents-4",
  "contents-5",
  "contents-6",
  "contents-10",
  "transition-teal-paint",
  "transition-orange-stroke",
  "content-statement-1",
  "content-image-1",
  "content-text-2",
  "content-text-3",
  "content-text-4",
  "content-metrics-4",
  "end-abstract-paint",
  "end-action",
];

const REFERENCE_SLIDES = {
  "cover-abstract-paint": [1],
  "cover-image": [2, 4],
  "contents-2": [3],
  "contents-3": [3],
  "contents-4": [3],
  "contents-5": [3],
  "contents-6": [3],
  "contents-10": [3],
  "transition-teal-paint": [7, 13, 19],
  "transition-orange-stroke": [7, 13, 19],
  "content-statement-1": [4, 9],
  "content-text-2": [5, 6],
  "content-text-3": [11, 14],
  "content-text-4": [8, 18],
  "content-image-1": [10],
  "content-metrics-4": [12],
  "end-abstract-paint": [24],
  "end-action": [22, 24],
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
      mustMatchReferenceStyle: true,
      preserve: options.preserve || [],
      deviations: options.deviations || [],
    },
    remark: [
      "[Sources]",
      "- Visual composition reference: user-provided 精品系列(36).pptx",
      "- Reference media excluded; original project assets generated with built-in imagegen",
      "- GPT Image 2 requested; actual model identifier may be unavailable",
      "- Final template must preserve the reference style, composition, palette and page rhythm",
    ].join("\n"),
    ...(options.allowedItemCounts ? { allowedItemCounts: options.allowedItemCounts } : {}),
    ...(options.layoutKind ? { layoutKind: options.layoutKind } : {}),
    ...(options.titleFitLimits ? { titleFitLimits: options.titleFitLimits } : {}),
    __counter: 0,
  };
}


function nextId(slide, role) {
  slide.__counter += 1;
  return `t20-${slide.id}-${role}-${String(slide.__counter).padStart(3, "0")}`;
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
  return {
    type: "shape",
    id: nextId(slide, role),
    left,
    top,
    width,
    height,
    viewBox: [200, 200],
    path: "M 0 0 L 200 0 L 200 200 L 0 200 Z",
    fill,
    fixedRatio: false,
    rotate: options.rotate || 0,
    outline: {
      color: options.outline || fill,
      width: options.outlineWidth ?? 0,
      style: "solid",
    },
    lock: options.lock ?? true,
    ...(options.groupId ? { groupId: options.groupId } : {}),
  };
}


function line(slide, role, left, top, length, color = COLORS.teal, width = 2) {
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
    content: `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: ${font};line-height: ${options.lineHeight || 1.3};${weight}">${escapeHtml(value)}</span></p>`,
    ...(options.textType ? { textType: options.textType } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(options.minimumFontSize ? { minimumFontSize: options.minimumFontSize } : {}),
    ...(options.textLineHeight ? { textLineHeight: options.textLineHeight } : {}),
    ...(options.textWidthFactor ? { textWidthFactor: options.textWidthFactor } : {}),
  };
}


function addBarcode(slide, left = 900, top = 18, color = COLORS.teal) {
  const widths = [2, 5, 2, 3, 2, 5, 2, 2, 4];
  let cursor = left;
  for (const width of widths) {
    slide.elements.push(shape(slide, "barcode", cursor, top, width, 54, color));
    cursor += width + 3;
  }
}


function addContentHeader(slide, titleValue, part = "ONE") {
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "header-paint", ASSETS.coverBackground, 24, 20, 72, 54, {
      fixedRatio: false,
      clip: { shape: "rect", range: [[5, 5], [95, 95]] },
    }),
    text(slide, "part", part, 28, 22, 64, 42, {
      font: "Arial",
      fontSize: 16,
      color: COLORS.white,
      bold: true,
      align: "center",
      textType: "partNumber",
      minimumFontSize: 14,
      textLineHeight: 1,
      lineHeight: 1,
    }),
    text(slide, "title", titleValue, 105, 18, 640, 64, {
      fontSize: 35,
      color: COLORS.black,
      bold: true,
      textType: "title",
      minimumFontSize: 35,
      textLineHeight: 1.15,
      lineHeight: 1.15,
    }),
    text(slide, "kicker", "BUSINESS REVIEW", 106, 76, 230, 18, {
      font: "Arial",
      fontSize: 12,
      color: COLORS.body,
      bold: true,
      lineHeight: 1,
    }),
  );
  addBarcode(slide);
}


function coverAbstractPaint() {
  const slide = createSlide("cover-abstract-paint", "cover", {
    preserve: [
      "full-bleed teal-orange oil paint",
      "oversized white title",
      "vertical English label",
      "teal subtitle rail",
      "upper-right barcode accent",
    ],
    deviations: ["reference media replaced with original generated oil-paint artwork"],
    titleFitLimits: { maxWide: 24, maxAscii: 48, singleWide: 12, singleAscii: 24 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.coverBackground, 0, 0, 1000, 562.5),
    text(slide, "vertical-label", "BUSINESS", 5, 205, 250, 56, {
      font: "Arial",
      fontSize: 44,
      color: COLORS.white,
      bold: true,
      rotate: -90,
      align: "center",
      lineHeight: 1,
    }),
    shape(slide, "year-block", 102, 378, 52, 105, COLORS.orange),
    text(slide, "year", "2026", 84, 409, 88, 28, {
      font: "Arial",
      fontSize: 18,
      color: COLORS.black,
      bold: true,
      rotate: -90,
      align: "center",
      lineHeight: 1,
    }),
    text(slide, "title", "抽象油彩商务汇报", 255, 160, 690, 140, {
      fontSize: 54,
      color: COLORS.white,
      bold: true,
      align: "center",
      textType: "title",
      minimumFontSize: 50,
      textLineHeight: 1.05,
      lineHeight: 1.05,
    }),
    shape(slide, "subtitle-rail", 285, 306, 610, 76, COLORS.teal),
    text(slide, "content", "用强烈笔触承载清晰表达", 310, 314, 560, 64, {
      fontSize: 20,
      color: COLORS.white,
      align: "center",
      textType: "content",
      minimumFontSize: 16,
      textLineHeight: 1.15,
      lineHeight: 1.15,
    }),
    shape(slide, "presenter-panel", 675, 408, 285, 42, COLORS.white),
    text(slide, "presenter", "汇报人：XXX", 690, 416, 250, 26, {
      fontSize: 16,
      color: COLORS.black,
      align: "center",
      textType: "content",
      minimumFontSize: 14,
      lineHeight: 1,
    }),
  );
  addBarcode(slide, 886, 20, COLORS.white);
  return slide;
}


function coverImage() {
  const slide = createSlide("cover-image", "cover", {
    preserve: [
      "white editorial field",
      "left oversized title",
      "right business image",
      "painted edge accents",
    ],
    deviations: ["reference photograph replaced by an editable business-image slot"],
    titleFitLimits: { maxWide: 20, maxAscii: 42, singleWide: 10, singleAscii: 22 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "teal-band", ASSETS.tealBrushBand, -70, 48, 560, 162),
    text(slide, "vertical-label", "BUSINESS", 22, 290, 210, 48, {
      font: "Arial", fontSize: 34, color: COLORS.teal, bold: true, rotate: -90, align: "center", lineHeight: 1,
    }),
    text(slide, "title", "业务增长与价值创造", 122, 162, 410, 128, {
      fontSize: 50, color: COLORS.black, bold: true, textType: "title",
      minimumFontSize: 46, textLineHeight: 1.08, lineHeight: 1.08,
    }),
    text(slide, "content", "聚焦关键问题，形成清晰行动", 126, 310, 382, 54, {
      fontSize: 18, color: COLORS.body, textType: "content", minimumFontSize: 16,
    }),
    shape(slide, "image-backing", 590, 82, 340, 400, COLORS.teal),
    image(slide, "content-image", ASSETS.coverBackground, 606, 98, 308, 368, {
      imageType: "content", lock: false, strictImageCount: true,
      requireSourceDimensions: true, originalWidth: 1600, originalHeight: 900,
      clip: { shape: "rect", range: [[0, 0], [100, 100]] },
    }),
    image(slide, "orange-sweep", ASSETS.orangeBrushSweep, 690, 410, 300, 84),
  );
  addBarcode(slide);
  return slide;
}


function contents(count) {
  const slide = createSlide(`contents-${count}`, "contents", {
    preserve: [
      "white content canvas",
      "oversized English contents label",
      "compact numbered entries",
      "narrow paint edge accents",
    ],
    allowedItemCounts: [count],
    titleFitLimits: { maxWide: 18, maxAscii: 40, singleWide: 9, singleAscii: 20 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "teal-band", ASSETS.tealBrushBand, -80, 80, 610, 176),
    image(slide, "speckles", ASSETS.pigmentSpeckles, 760, 332, 240, 135),
    text(slide, "english-label", "CONTENTS", 60, 110, 440, 82, {
      font: "Arial", fontSize: 56, color: COLORS.white, bold: true, lineHeight: 1,
    }),
    text(slide, "title", "目录", 64, 202, 200, 72, {
      fontSize: 35, color: COLORS.black, bold: true, textType: "title", minimumFontSize: 35,
    }),
  );
  const columns = count > 6 ? 2 : 1;
  const rows = Math.ceil(count / columns);
  const itemHeight = Math.min(58, 310 / rows);
  for (let index = 0; index < count; index += 1) {
    const column = Math.floor(index / rows);
    const row = index % rows;
    const left = 505 + column * 232;
    const top = 98 + row * itemHeight;
    const groupId = `contents-${count}-item-${index + 1}`;
    slide.elements.push(
      text(slide, "item-number", String(index + 1).padStart(2, "0"), left, top, 48, 34, {
        font: "Arial", fontSize: count > 6 ? 16 : 18, color: index % 2 ? COLORS.orange : COLORS.teal,
        bold: true, textType: "itemNumber", groupId, textLineHeight: 1, lineHeight: 1,
      }),
      line(slide, "item-line", left + 48, top + 12, 30, index % 2 ? COLORS.orange : COLORS.teal, 2),
      text(slide, "item", `目录主题 ${index + 1}`, left + 88, top - 2, 132, itemHeight - 5, {
        fontSize: count > 6 ? 14 : 17, color: COLORS.body, textType: "item",
        minimumFontSize: count > 6 ? 12 : 14, textLineHeight: 1.15, lineHeight: 1.15, groupId,
      }),
    );
  }
  addBarcode(slide);
  return slide;
}


function transitionPaint(id, variantKey, useOrange) {
  const slide = createSlide(id, "transition", {
    preserve: [
      "full-bleed deep teal paint",
      "large white chapter title",
      "oversized chapter number",
      "directional orange-yellow accent",
    ],
    titleFitLimits: { maxWide: 24, maxAscii: 50, singleWide: 12, singleAscii: 25 },
  });
  slide.variantKey = variantKey;
  // 两个视觉版式覆盖 Content Agent 的四种稳定章节变体，不增加重复页面库存。
  slide.variantAliases = useOrange ? ["stage"] : ["particle"];
  slide.elements.push(
    image(slide, "background", ASSETS.sectionBackground, 0, 0, 1000, 562.5),
    image(slide, useOrange ? "orange-sweep" : "teal-band", useOrange ? ASSETS.orangeBrushSweep : ASSETS.tealBrushBand,
      useOrange ? 575 : -70, useOrange ? 325 : 42, useOrange ? 410 : 590, useOrange ? 115 : 170),
    text(slide, "part-number", "01", 74, 92, 180, 116, {
      font: "Arial", fontSize: 82, color: useOrange ? COLORS.yellow : COLORS.orange,
      bold: true, textType: "partNumber", minimumFontSize: 64, textLineHeight: 1, lineHeight: 1,
    }),
    text(slide, "title", useOrange ? "行动计划与推进路径" : "战略重点与业务方向", 82, 222, 590, 102, {
      fontSize: 46, color: COLORS.white, bold: true, textType: "title",
      minimumFontSize: 44, textLineHeight: 1.1, lineHeight: 1.1,
    }),
    text(slide, "content", "以明确目标统领行动，以可验证结果推动增长。", 86, 348, 565, 78, {
      fontSize: 18, color: COLORS.white, textType: "content", minimumFontSize: 16,
      textLineHeight: 1.35, lineHeight: 1.35,
    }),
  );
  addBarcode(slide, 886, 20, COLORS.white);
  return slide;
}


function contentStatementOne() {
  const slide = createSlide("content-statement-1", "content", {
    preserve: ["white editorial field", "oversized statement", "yellow paint focus", "painted lower edge"],
    allowedItemCounts: [1],
    layoutKind: "statement",
    titleFitLimits: { maxWide: 28, maxAscii: 60, singleWide: 12, singleAscii: 28 },
  });
  const groupId = "content-statement-1-item-1";
  addContentHeader(slide, "核心观点", "TWO");
  slide.elements.push(
    image(slide, "yellow-highlight", ASSETS.yellowHighlight, 215, 155, 570, 124),
    text(slide, "item-title", "聚焦真正重要的问题", 195, 158, 610, 82, {
      fontSize: 34, color: COLORS.black, bold: true, align: "center", textType: "itemTitle",
      minimumFontSize: 26, textLineHeight: 1.1, lineHeight: 1.1, groupId,
    }),
    text(slide, "item", "用清晰判断连接战略与行动，用可验证成果持续创造业务价值。", 190, 285, 620, 112, {
      fontSize: 21, color: COLORS.body, align: "center", textType: "item",
      minimumFontSize: 18, textLineHeight: 1.45, lineHeight: 1.45, groupId,
    }),
    image(slide, "orange-sweep", ASSETS.orangeBrushSweep, 650, 405, 310, 86),
  );
  return slide;
}


function contentText(count) {
  const slide = createSlide(`content-text-${count}`, "content", {
    preserve: [
      "white content canvas",
      "compact paint-backed chapter marker",
      `${count} evenly spaced content groups`,
      "narrow oil-paint bottom strip",
    ],
    allowedItemCounts: [count],
    layoutKind: `${count}-text`,
    titleFitLimits: { maxWide: 28, maxAscii: 60, singleWide: 10, singleAscii: 22 },
  });
  addContentHeader(slide, `${count === 2 ? "双项" : count === 3 ? "三项" : "四项"}工作重点`, "ONE");
  const gap = count === 2 ? 70 : count === 3 ? 42 : 30;
  const itemWidth = (860 - gap * (count - 1)) / count;
  for (let index = 0; index < count; index += 1) {
    const left = 70 + index * (itemWidth + gap);
    const groupId = `content-text-${count}-item-${index + 1}`;
    const accent = index % 2 === 0 ? COLORS.teal : COLORS.orange;
    slide.elements.push(
      shape(slide, "item-accent", left, 180, 52, 52, accent, { groupId }),
      text(slide, "item-number", String(index + 1).padStart(2, "0"), left, 188, 52, 36, {
        font: "Arial",
        fontSize: 16,
        color: COLORS.white,
        bold: true,
        align: "center",
        textType: "itemNumber",
        groupId,
        textLineHeight: 1,
        lineHeight: 1,
      }),
      text(slide, "item-title", `重点工作 ${index + 1}`, left, 250, itemWidth, 58, {
        fontSize: 22,
        color: COLORS.black,
        bold: true,
        textType: "itemTitle",
        // 三栏和四栏需要兑现公共协议的12字/10字标题容量，最低16px仍满足可读性门槛。
        minimumFontSize: count >= 3 ? 16 : 20,
        textLineHeight: 1.15,
        lineHeight: 1.15,
        groupId,
      }),
      line(slide, "item-line", left, 316, 92, accent, 3),
      text(slide, "item", "说明关键行动、执行依据和可验证结果。", left, 335, itemWidth, 122, {
        fontSize: 16,
        color: COLORS.body,
        textType: "item",
        minimumFontSize: 16,
        textLineHeight: 1.35,
        lineHeight: 1.35,
        groupId,
      }),
    );
  }
  return slide;
}


function contentImageOne() {
  const slide = createSlide("content-image-1", "content", {
    preserve: [
      "white content canvas",
      "large right business image",
      "yellow paint title highlight",
      "deep teal text block",
      "narrow oil-paint bottom strip",
    ],
    deviations: ["reference car photograph replaced by an editable business-image slot"],
    allowedItemCounts: [1],
    layoutKind: "1-image-text",
    titleFitLimits: { maxWide: 34, maxAscii: 72, singleWide: 16, singleAscii: 36 },
  });
  const groupId = "content-image-1-item-1";
  addContentHeader(slide, "重点项目展示", "TWO");
  slide.elements.push(
    shape(slide, "title-highlight", 182, 158, 330, 82, COLORS.yellow, { groupId }),
    text(slide, "item-title", "核心成果与业务价值", 195, 166, 305, 66, {
      fontSize: 24,
      color: COLORS.white,
      bold: true,
      align: "center",
      textType: "itemTitle",
      minimumFontSize: 20,
      textLineHeight: 1.1,
      lineHeight: 1.1,
      groupId,
    }),
    shape(slide, "text-panel", 95, 255, 430, 170, COLORS.teal, { groupId }),
    text(slide, "item", "在此说明项目背景、核心动作、成果数据和下一步计划。业务图片可以替换，装饰保持不变。", 122, 280, 376, 122, {
      fontSize: 17,
      color: COLORS.white,
      textType: "item",
      minimumFontSize: 16,
      textLineHeight: 1.4,
      lineHeight: 1.4,
      groupId,
    }),
    shape(slide, "image-backing", 580, 130, 345, 330, COLORS.black, { groupId }),
    image(slide, "content-image", ASSETS.coverBackground, 595, 145, 315, 300, {
      imageType: "content",
      lock: false,
      strictImageCount: true,
      requireSourceDimensions: true,
      originalWidth: 1600,
      originalHeight: 900,
      groupId,
      clip: { shape: "rect", range: [[0, 0], [100, 100]] },
    }),
    image(slide, "paint-corner", ASSETS.paintCorner, 790, 355, 210, 158, { fixedRatio: true }),
  );
  return slide;
}


function contentMetricsFour() {
  const slide = createSlide("content-metrics-4", "content", {
    preserve: ["white content canvas", "four oversized metrics", "yellow focus accents", "painted edge rhythm"],
    allowedItemCounts: [4],
    layoutKind: "metrics",
    titleFitLimits: { maxWide: 28, maxAscii: 60, singleWide: 10, singleAscii: 22 },
  });
  addContentHeader(slide, "关键经营指标", "03");
  slide.elements.push(
    image(slide, "speckles", ASSETS.pigmentSpeckles, 770, 350, 230, 130),
  );
  for (let index = 0; index < 4; index += 1) {
    const left = 65 + index * 226;
    const groupId = `content-metrics-4-item-${index + 1}`;
    const accent = index % 2 ? COLORS.orange : COLORS.teal;
    slide.elements.push(
      image(slide, "yellow-highlight", ASSETS.yellowHighlight, left - 14, 178, 190, 42, { groupId }),
      text(slide, "item-title", `${[28, 46, 72, 91][index]}%`, left, 164, 190, 84, {
        font: "Arial", fontSize: 48, color: COLORS.black, bold: true, textType: "itemTitle",
        minimumFontSize: 38, textLineHeight: 1, lineHeight: 1, groupId,
      }),
      line(slide, "metric-line", left, 264, 86, accent, 4),
      text(slide, "item", `指标说明 ${index + 1}`, left, 286, 185, 92, {
        fontSize: 17, color: COLORS.body, textType: "item", minimumFontSize: 15,
        textLineHeight: 1.3, lineHeight: 1.3, groupId,
      }),
    );
  }
  return slide;
}


function endAbstractPaint() {
  const slide = createSlide("end-abstract-paint", "end", {
    preserve: ["cover-end symmetry", "full-bleed teal oil paint", "large white closing line", "quiet center-left field"],
    allowedItemCounts: [0],
    titleFitLimits: { maxWide: 22, maxAscii: 48, singleWide: 11, singleAscii: 24 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.endBackground, 0, 0, 1000, 562.5),
    text(slide, "title", "感谢聆听", 160, 188, 570, 100, {
      fontSize: 58, color: COLORS.white, bold: true, textType: "title",
      minimumFontSize: 50, textLineHeight: 1.05, lineHeight: 1.05,
    }),
    text(slide, "content", "THANK YOU", 166, 300, 420, 70, {
      font: "Arial", fontSize: 28, color: COLORS.yellow, bold: true, textType: "content",
      minimumFontSize: 22, lineHeight: 1,
    }),
    image(slide, "speckles", ASSETS.pigmentSpeckles, 750, 372, 250, 140),
  );
  addBarcode(slide, 886, 20, COLORS.white);
  return slide;
}


function endAction() {
  const slide = createSlide("end-action", "end", {
    preserve: ["white editorial field", "left closing statement", "up to three action lines", "painted corner ending"],
    allowedItemCounts: [1, 2, 3],
    titleFitLimits: { maxWide: 22, maxAscii: 48, singleWide: 11, singleAscii: 24 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "teal-band", ASSETS.tealBrushBand, -80, 64, 610, 176),
    text(slide, "title", "下一步行动", 72, 112, 440, 86, {
      fontSize: 48, color: COLORS.white, bold: true, textType: "title",
      minimumFontSize: 44, textLineHeight: 1.05, lineHeight: 1.05,
    }),
    text(slide, "content", "让每一项共识都转化为清晰行动。", 74, 256, 430, 62, {
      fontSize: 19, color: COLORS.body, textType: "content", minimumFontSize: 16,
    }),
    image(slide, "paint-corner", ASSETS.paintCorner, 770, 335, 230, 172),
  );
  for (let index = 0; index < 3; index += 1) {
    const top = 126 + index * 112;
    const groupId = `end-action-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "action-number-bg", 585, top, 48, 48, index % 2 ? COLORS.orange : COLORS.teal, { groupId }),
      text(slide, "action-number", String(index + 1).padStart(2, "0"), 585, top + 8, 48, 30, {
        font: "Arial", fontSize: 16, color: COLORS.white, bold: true, align: "center", groupId,
        textLineHeight: 1, lineHeight: 1,
      }),
      text(slide, "item", `行动建议 ${index + 1}`, 652, top - 1, 260, 62, {
        fontSize: 18, color: COLORS.body, textType: "item", minimumFontSize: 16,
        textLineHeight: 1.25, lineHeight: 1.25, groupId,
      }),
    );
  }
  addBarcode(slide);
  return slide;
}


function finalizeSlide(slide) {
  delete slide.__counter;
  return slide;
}


function buildTemplate(stage) {
  const stageIds = {
    probe: PROBE_IDS,
    sample: SAMPLE_IDS,
    mvp: MVP_IDS,
    production: PRODUCTION_IDS,
  };
  if (!stageIds[stage]) {
    throw new Error("stage必须是probe、sample、mvp或production");
  }
  const factories = {
    "cover-abstract-paint": coverAbstractPaint,
    "cover-image": coverImage,
    "contents-2": () => contents(2),
    "contents-3": () => contents(3),
    "contents-4": () => contents(4),
    "contents-5": () => contents(5),
    "contents-6": () => contents(6),
    "contents-10": () => contents(10),
    "transition-teal-paint": () => transitionPaint("transition-teal-paint", "horizon", false),
    "transition-orange-stroke": () => transitionPaint("transition-orange-stroke", "spectrum", true),
    "content-statement-1": contentStatementOne,
    "content-image-1": contentImageOne,
    "content-text-2": () => contentText(2),
    "content-text-3": () => contentText(3),
    "content-text-4": () => contentText(4),
    "content-metrics-4": contentMetricsFour,
    "end-abstract-paint": endAbstractPaint,
    "end-action": endAction,
  };
  const slides = stageIds[stage].map(id => finalizeSlide(factories[id]()));
  return {
    id: "template_20",
    title: "抽象油彩商务汇报",
    width: 1000,
    height: 562.5,
    // 同一主题超过四项时由公共渲染器按原顺序无损拆页，不能在 Worker 预检阶段拒绝。
    supportsLosslessContentPagination: true,
    paginationGrowthPolicy: {
      // 四栏正文槽较紧，允许受控拆页；仍会拦截29页膨胀到62页的真实异常。
      factor: 1.75,
      slack: 5,
    },
    theme: {
      themeColors: [COLORS.teal, COLORS.orange, COLORS.paintTeal, COLORS.paintOrange, COLORS.yellow],
      fontColor: COLORS.body,
      fontName: "微软雅黑",
      backgroundColor: COLORS.background,
      shadow: { h: 2, v: 3, blur: 5, color: COLORS.black, opacity: 0.16 },
      outline: { width: 1, color: COLORS.teal, style: "solid" },
    },
    metadata: {
      aspectRatio: "16:9",
      buildStage: stage,
      sourceReference: "精品系列(36).pptx",
      sourceReferenceSha256: "3F34B2292E389A1FD08E9E4A4B6A3BF24FDCC32EBAADA15A5A722815A8941C81",
      rightsPolicy: "reference-media-excluded",
      sourceFidelity: "must-match-reference-style-composition-color-texture-spacing-rhythm",
      probeSlideIds: PROBE_IDS,
      sampleSlideIds: SAMPLE_IDS,
      mvpSlideIds: MVP_IDS,
      productionSlideIds: PRODUCTION_IDS,
      imageSlotMarker: "imageType=content",
      decorativeImageMarker: "imageType=decoration",
      assetGeneration: "built-in imagegen; GPT Image 2 requested; actual model identifier not exposed",
      assetFiles: Object.values(ASSETS).map(value => value.split("/").at(-1)),
    },
    slides,
  };
}


function parseArgs(argv) {
  let stage = "probe";
  let output = "";
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--stage") {
      stage = argv[index + 1] || "";
      index += 1;
    }
    else if (!output) output = argv[index];
  }
  if (!output) {
    throw new Error("用法: node utils/build_abstract_oil_business_template.mjs --stage <probe|sample|mvp|production> <输出JSON>");
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

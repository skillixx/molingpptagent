#!/usr/bin/env node

/**
 * 确定性构建“水彩绿植轻商务”PPTist 模板。
 *
 * 视觉来源：用户提供的《精品系列(21).pptx》。只复用构图、配色、留白和页面节奏，
 * 不复制参考媒体、特殊字体、音频、动画和原生图表。
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = path.resolve(SCRIPT_DIR, "..");

const COLORS = {
  background: "#F6F7F3",
  eucalyptus: "#79B99B",
  mint: "#CBE5D9",
  ink: "#2F3B37",
  body: "#4A4D4B",
  blush: "#F3D8CF",
  yellow: "#F3D45F",
  white: "#FFFFFF",
};

const ASSETS = {
  coverBackground: "/api/data/template_19_asset_bg_cover_v1.jpg",
  contentBackground: "/api/data/template_19_asset_bg_content_v1.jpg",
  sectionBackground: "/api/data/template_19_asset_bg_section_v1.jpg",
  endBackground: "/api/data/template_19_asset_bg_end_v1.jpg",
  eucalyptusCornerUpper: "/api/data/template_19_asset_eucalyptus_corner_upper_v1.png",
  eucalyptusCorner: "/api/data/template_19_asset_eucalyptus_corner_v1.png",
  eucalyptusSweep: "/api/data/template_19_asset_eucalyptus_sweep_v1.png",
  fernSpray: "/api/data/template_19_asset_fern_spray_v1.png",
  leafMedallion: "/api/data/template_19_asset_leaf_medallion_v1.png",
};

const PROBE_IDS = ["cover-botanical-frame", "content-text-4", "content-image-1"];
const MVP_IDS = [
  "cover-botanical-frame",
  "contents-2",
  "contents-3",
  "contents-4",
  "contents-5",
  "contents-6",
  "contents-10",
  "transition-eucalyptus",
  "content-text-2",
  "content-text-3",
  "content-text-4",
  "end-botanical-frame",
];
const PRODUCTION_IDS = [
  "cover-botanical-frame",
  "cover-image",
  "contents-2",
  "contents-3",
  "contents-4",
  "contents-5",
  "contents-6",
  "contents-10",
  "transition-eucalyptus",
  "transition-fern",
  "content-statement-1",
  "content-image-1",
  "content-text-2",
  "content-text-3",
  "content-text-4",
  "content-metrics-4",
  "end-botanical-frame",
  "end-action",
];
const SAMPLE_IDS = [
  "cover-botanical-frame",
  "contents-4",
  "transition-eucalyptus",
  "content-text-2",
  "end-botanical-frame",
];
const REFERENCE_SLIDES = {
  "cover-botanical-frame": [1],
  "cover-image": [1, 19],
  "contents-2": [2],
  "contents-3": [2],
  "contents-4": [2],
  "contents-5": [2],
  "contents-6": [2],
  "contents-10": [2],
  "transition-eucalyptus": [3, 8],
  "transition-fern": [13, 18],
  "content-statement-1": [17, 19],
  "content-text-2": [9, 19, 23],
  "content-text-3": [5, 14, 15],
  "content-text-4": [4, 10, 11],
  "content-image-1": [19, 23],
  "content-metrics-4": [6, 22],
  "end-botanical-frame": [24],
  "end-action": [21, 24],
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
      "- Visual composition reference: user-provided 精品系列(21).pptx",
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
  return `t19-${slide.id}-${role}-${String(slide.__counter).padStart(3, "0")}`;
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


function line(slide, role, left, top, length, color = COLORS.eucalyptus, width = 2) {
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
    content: `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: ${font};line-height: ${options.lineHeight || 1.35};${weight}">${escapeHtml(value)}</span></p>`,
    ...(options.textType ? { textType: options.textType } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(options.minimumFontSize ? { minimumFontSize: options.minimumFontSize } : {}),
    ...(options.textLineHeight ? { textLineHeight: options.textLineHeight } : {}),
    ...(options.textWidthFactor ? { textWidthFactor: options.textWidthFactor } : {}),
  };
}


function addContentHeader(slide, titleValue, part = "01") {
  slide.elements.push(
    text(slide, "part", part, 54, 24, 74, 50, {
      font: "Arial",
      fontSize: 26,
      color: COLORS.eucalyptus,
      bold: true,
    }),
    text(slide, "title", titleValue, 125, 26, 690, 82, {
      fontSize: 35,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 35,
      textLineHeight: 1.2,
      lineHeight: 1.2,
    }),
    line(slide, "title-line", 126, 112, 660, COLORS.mint, 2),
  );
}


function coverBotanicalFrame() {
  const slide = createSlide("cover-botanical-frame", "cover", {
    preserve: ["watercolor paper texture", "upper-right and lower-left eucalyptus framing", "centered title panel", "large calm whitespace"],
    deviations: ["source media replaced with original generated artwork", "special fonts replaced with stable editable typography"],
    titleFitLimits: { maxWide: 24, maxAscii: 48, singleWide: 12, singleAscii: 24 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.coverBackground, 0, 0, 1000, 562.5),
    shape(slide, "title-panel", 205, 140, 590, 275, "rgba(255,255,255,0.84)", {
      rounded: true,
      outline: COLORS.eucalyptus,
      outlineWidth: 2,
    }),
    text(slide, "title", "水彩绿植轻商务", 250, 165, 500, 138, {
      fontSize: 50,
      color: COLORS.ink,
      bold: true,
      align: "center",
      textType: "title",
      minimumFontSize: 50,
      textLineHeight: 1.1,
      lineHeight: 1.1,
    }),
    line(slide, "accent-line", 355, 310, 290, COLORS.eucalyptus, 2),
    text(slide, "content", "让自然留白承载清晰表达", 275, 325, 450, 88, {
      fontSize: 18,
      color: COLORS.body,
      align: "center",
      textType: "content",
      minimumFontSize: 16,
      textLineHeight: 1.3,
      lineHeight: 1.3,
    }),
  );
  return slide;
}


function coverImage() {
  const slide = createSlide("cover-image", "cover", {
    preserve: ["asymmetric botanical framing", "large left visual", "right title field", "quiet watercolor paper"],
    deviations: ["reference illustration replaced by an explicit business image slot"],
    titleFitLimits: { maxWide: 24, maxAscii: 48, singleWide: 12, singleAscii: 24 },
  });
  const groupId = "cover-image-business-1";
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    shape(slide, "image-backing", 58, 112, 420, 326, COLORS.blush, {
      rounded: true,
      outline: COLORS.blush,
      groupId,
    }),
    image(slide, "content-image", ASSETS.contentBackground, 78, 132, 380, 286, {
      imageType: "content",
      lock: false,
      strictImageCount: true,
      requireSourceDimensions: true,
      originalWidth: 1600,
      originalHeight: 900,
      groupId,
      clip: { shape: "rect", range: [[0, 0], [100, 100]] },
    }),
    image(slide, "corner-upper", ASSETS.eucalyptusCornerUpper, 730, -10, 280, 180, { fixedRatio: true }),
    text(slide, "title", "水彩绿植轻商务", 535, 155, 390, 140, {
      fontSize: 50,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 50,
      textLineHeight: 1.1,
      lineHeight: 1.1,
    }),
    line(slide, "accent", 538, 310, 260, COLORS.eucalyptus, 2),
    text(slide, "content", "用自然气息建立清晰、可信的表达", 538, 337, 345, 88, {
      fontSize: 18,
      textType: "content",
      minimumFontSize: 16,
      textLineHeight: 1.3,
      lineHeight: 1.3,
    }),
  );
  return slide;
}


function contentsSlide(count) {
  const slide = createSlide(`contents-${count}`, "contents", {
    preserve: ["left botanical focal mass", "numbered contents rhythm", "open right content field", "pale paper texture"],
    deviations: ["capacity variants derived from source slide 2"],
    allowedItemCounts: [count],
  });
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "left-foliage", ASSETS.eucalyptusCorner, -35, 175, 355, 228, { fixedRatio: true }),
    text(slide, "contents-title", "目录", 92, 105, 210, 86, {
      fontSize: 44,
      color: COLORS.ink,
      bold: true,
    }),
    text(slide, "contents-en", "CONTENTS", 96, 185, 190, 45, {
      font: "Arial",
      fontSize: 16,
      color: COLORS.eucalyptus,
      bold: true,
    }),
  );
  const columns = count <= 5 ? 1 : 2;
  const rows = Math.ceil(count / columns);
  const lefts = columns === 1 ? [390] : [350, 665];
  const startTop = rows <= 2 ? 190 : rows === 3 ? 145 : 105;
  const rowGap = rows <= 3 ? 105 : 82;
  for (let index = 0; index < count; index += 1) {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const left = lefts[column];
    const top = startTop + row * rowGap;
    const groupId = `contents-${count}-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "number-badge", left, top, 48, 48, index % 2 ? COLORS.blush : COLORS.mint, {
        ellipse: true,
        groupId,
      }),
      text(slide, "number", String(index + 1).padStart(2, "0"), left, top + 5, 48, 38, {
        font: "Arial",
        fontSize: 14,
        color: COLORS.ink,
        bold: true,
        align: "center",
        textType: "itemNumber",
        textLineHeight: 1,
        lineHeight: 1,
        groupId,
      }),
      text(slide, "item", `目录项目 ${index + 1}`, left + 66, top - 2, columns === 1 ? 410 : 230, 58, {
        fontSize: rows >= 5 ? 16 : 18,
        color: COLORS.ink,
        textType: "item",
        minimumFontSize: 16,
        textLineHeight: 1.2,
        lineHeight: 1.2,
        groupId,
      }),
    );
  }
  return slide;
}


function contentTextFour() {
  const slide = createSlide("content-text-4", "content", {
    preserve: ["four-part rhythm", "pastel circular markers", "edge foliage", "flat open content field"],
    deviations: ["source small text enlarged for production readability"],
    allowedItemCounts: [4],
    layoutKind: "text",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "corner", ASSETS.eucalyptusCorner, -10, 335, 260, 167, { fixedRatio: true }),
  );
  addContentHeader(slide, "四项内容结构", "01");
  const positions = [
    [96, 150], [520, 150], [96, 340], [520, 340],
  ];
  const colors = [COLORS.blush, COLORS.mint, COLORS.mint, COLORS.blush];
  for (let index = 0; index < 4; index += 1) {
    const [left, top] = positions[index];
    const groupId = `content-text-4-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "number-badge", left, top, 54, 54, colors[index], { ellipse: true, groupId }),
      text(slide, "number", String(index + 1).padStart(2, "0"), left, top + 6, 54, 42, {
        font: "Arial",
        fontSize: 15,
        color: COLORS.ink,
        bold: true,
        align: "center",
        textType: "itemNumber",
        textLineHeight: 1,
        lineHeight: 1,
        groupId,
      }),
      text(slide, "item-title", `核心要点 ${index + 1}`, left + 72, top - 2, 300, 64, {
        fontSize: 24,
        color: COLORS.ink,
        bold: true,
        textType: "itemTitle",
        minimumFontSize: 20,
        textLineHeight: 1.2,
        lineHeight: 1.2,
        groupId,
      }),
      text(slide, "item", "在此输入完整说明，保持观点、依据与行动之间的清晰关系。", left + 72, top + 62, 302, 92, {
        fontSize: 16,
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
    );
  }
  return slide;
}


function contentTextTwo() {
  const slide = createSlide("content-text-2", "content", {
    preserve: ["two-part horizontal rhythm", "large whitespace", "botanical edge accent"],
    deviations: ["source text enlarged for production readability"],
    allowedItemCounts: [2],
    layoutKind: "text",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "corner-upper", ASSETS.eucalyptusCornerUpper, 748, -12, 262, 168, { fixedRatio: true }),
  );
  addContentHeader(slide, "双项内容结构", "01");
  for (let index = 0; index < 2; index += 1) {
    const left = 90 + index * 450;
    const groupId = `content-text-2-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "accent-rail", left, 170, 8, 245, index ? COLORS.blush : COLORS.eucalyptus, { groupId }),
      text(slide, "number", String(index + 1).padStart(2, "0"), left + 28, 170, 55, 42, {
        font: "Arial",
        fontSize: 17,
        color: COLORS.eucalyptus,
        bold: true,
        textType: "itemNumber",
        textLineHeight: 1,
        lineHeight: 1,
        groupId,
      }),
      text(slide, "item-title", `核心要点 ${index + 1}`, left + 28, 222, 330, 80, {
        fontSize: 26,
        color: COLORS.ink,
        bold: true,
        textType: "itemTitle",
        minimumFontSize: 24,
        textLineHeight: 1.2,
        lineHeight: 1.2,
        groupId,
      }),
      text(slide, "item", "在此输入完整说明，保持信息层级清楚，并为证据和下一步行动留出空间。", left + 28, 315, 340, 150, {
        fontSize: 17,
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
    );
  }
  return slide;
}


function contentTextThree() {
  const slide = createSlide("content-text-3", "content", {
    preserve: ["three-column rhythm", "leaf marker language", "flat horizontal reading"],
    deviations: ["source text enlarged and normalized"],
    allowedItemCounts: [3],
    layoutKind: "text",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  slide.elements.push(image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5));
  addContentHeader(slide, "三项内容结构", "01");
  for (let index = 0; index < 3; index += 1) {
    const left = 60 + index * 305;
    const groupId = `content-text-3-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "leaf-disc", left + 85, 150, 98, 98, index === 1 ? COLORS.blush : COLORS.mint, {
        ellipse: true,
        groupId,
      }),
      text(slide, "number", String(index + 1).padStart(2, "0"), left + 85, 180, 98, 40, {
        font: "Arial",
        fontSize: 18,
        color: COLORS.ink,
        bold: true,
        align: "center",
        textType: "itemNumber",
        textLineHeight: 1,
        lineHeight: 1,
        groupId,
      }),
      text(slide, "item-title", `核心要点 ${index + 1}`, left, 270, 270, 80, {
        fontSize: 24,
        color: COLORS.ink,
        bold: true,
        align: "center",
        textType: "itemTitle",
        minimumFontSize: 20,
        textLineHeight: 1.2,
        lineHeight: 1.2,
        groupId,
      }),
      text(slide, "item", "在此输入完整说明，避免把正文压缩成难以阅读的小字。", left + 12, 360, 246, 130, {
        fontSize: 16,
        align: "center",
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
    );
  }
  slide.elements.push(image(slide, "sweep", ASSETS.eucalyptusSweep, 220, 468, 560, 92, { fixedRatio: true }));
  return slide;
}


function transitionEucalyptus() {
  const slide = createSlide("transition-eucalyptus", "transition", {
    preserve: ["centered section title", "low eucalyptus arc", "large upper whitespace"],
    deviations: ["source media replaced with original generated background"],
    variantMode: "deterministic",
    titleFitLimits: { maxWide: 30, maxAscii: 60, singleWide: 15, singleAscii: 30 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.sectionBackground, 0, 0, 1000, 562.5),
    image(slide, "medallion", ASSETS.leafMedallion, 90, 100, 190, 190, { fixedRatio: true }),
    text(slide, "part-number", "01", 140, 160, 90, 52, {
      font: "Arial",
      fontSize: 26,
      color: COLORS.eucalyptus,
      bold: true,
      align: "center",
      textType: "partNumber",
      textLineHeight: 1,
      lineHeight: 1,
    }),
    text(slide, "title", "章节标题", 320, 145, 550, 115, {
      fontSize: 44,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 44,
      textLineHeight: 1.15,
      lineHeight: 1.15,
    }),
    text(slide, "content", "用简短说明承接上一部分，并建立下一章节的清晰语境。", 324, 285, 470, 105, {
      fontSize: 18,
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  return slide;
}


function transitionFern() {
  const slide = createSlide("transition-fern", "transition", {
    preserve: ["asymmetric section title", "single-side fern spray", "large left whitespace"],
    deviations: ["source media replaced with original generated fern"],
    variantMode: "deterministic",
    titleFitLimits: { maxWide: 30, maxAscii: 60, singleWide: 15, singleAscii: 30 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "fern", ASSETS.fernSpray, 650, 0, 350, 562.5, { fixedRatio: false }),
    text(slide, "part-number", "02", 95, 120, 95, 55, {
      font: "Arial",
      fontSize: 28,
      color: COLORS.eucalyptus,
      bold: true,
      textType: "partNumber",
      textLineHeight: 1,
      lineHeight: 1,
    }),
    line(slide, "part-line", 95, 188, 150, COLORS.blush, 3),
    text(slide, "title", "章节标题", 95, 215, 500, 120, {
      fontSize: 44,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 44,
      textLineHeight: 1.15,
      lineHeight: 1.15,
    }),
    text(slide, "content", "以单侧植物构图转换章节节奏，同时保持标题区域清晰。", 98, 350, 455, 105, {
      fontSize: 18,
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  return slide;
}


function contentImageOne() {
  const slide = createSlide("content-image-1", "content", {
    preserve: ["large left visual", "right text block", "pastel image backing", "corner foliage"],
    deviations: ["left decorative visual replaced by an explicit business image slot"],
    allowedItemCounts: [1],
    layoutKind: "1-image-text",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  slide.elements.push(image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5));
  addContentHeader(slide, "图文内容", "02");
  const groupId = "content-image-1-item-1";
  slide.elements.push(
    shape(slide, "image-backing", 70, 150, 410, 300, COLORS.blush, {
      rounded: true,
      outline: COLORS.blush,
      groupId,
    }),
    image(slide, "content-image", ASSETS.contentBackground, 88, 168, 374, 264, {
      imageType: "content",
      lock: false,
      strictImageCount: true,
      requireSourceDimensions: true,
      originalWidth: 1920,
      originalHeight: 1080,
      groupId,
      clip: { shape: "rect", range: [[0, 0], [100, 100]] },
    }),
    text(slide, "item-number", "01", 555, 166, 58, 42, {
      font: "Arial",
      fontSize: 17,
      color: COLORS.eucalyptus,
      bold: true,
      textType: "itemNumber",
      textLineHeight: 1,
      lineHeight: 1,
      groupId,
    }),
    text(slide, "item-title", "让图片与观点共同完成表达", 555, 215, 365, 86, {
      fontSize: 26,
      color: COLORS.ink,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 24,
      textLineHeight: 1.2,
      lineHeight: 1.2,
      groupId,
    }),
    text(slide, "item", "业务图片保持可替换和稳定裁切，水彩植物只承担固定装饰角色。", 555, 320, 345, 125, {
      fontSize: 17,
      textType: "item",
      minimumFontSize: 16,
      groupId,
    }),
    image(slide, "corner", ASSETS.eucalyptusCorner, 760, 390, 230, 148, { fixedRatio: true }),
  );
  return slide;
}


function statementSlide() {
  const slide = createSlide("content-statement-1", "content", {
    preserve: ["single conclusion focus", "right botanical accent", "large quiet whitespace"],
    deviations: ["source illustration replaced and text enlarged"],
    allowedItemCounts: [1],
    layoutKind: "text",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5),
    image(slide, "fern", ASSETS.fernSpray, 720, 125, 280, 390, { fixedRatio: false }),
  );
  addContentHeader(slide, "核心结论", "03");
  const groupId = "content-statement-1-item-1";
  slide.elements.push(
    shape(slide, "rail", 105, 165, 9, 280, COLORS.eucalyptus, { groupId }),
    text(slide, "item-title", "让一个关键结论成为页面唯一重心", 150, 180, 520, 112, {
      fontSize: 32,
      color: COLORS.ink,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 24,
      textLineHeight: 1.2,
      lineHeight: 1.2,
      groupId,
    }),
    text(slide, "item", "单项页面用于承载结论、引语或摘要。装饰保持克制，正文获得充足的阅读空间。", 154, 315, 485, 140, {
      fontSize: 18,
      textType: "item",
      minimumFontSize: 16,
      groupId,
    }),
  );
  return slide;
}


function metricsSlide() {
  const slide = createSlide("content-metrics-4", "content", {
    preserve: ["four circular metrics", "mint blush alternation", "horizontal data rhythm", "botanical lower edge"],
    deviations: ["source native chart replaced with editable text and shapes"],
    allowedItemCounts: [4],
    layoutKind: "metrics",
    titleFitLimits: { maxWide: 40, maxAscii: 80, singleWide: 20, singleAscii: 44 },
  });
  slide.elements.push(image(slide, "background", ASSETS.contentBackground, 0, 0, 1000, 562.5));
  addContentHeader(slide, "四项核心指标", "04");
  for (let index = 0; index < 4; index += 1) {
    const left = 95 + index * 220;
    const groupId = `content-metrics-4-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "metric-disc", left, 155, 150, 150, index % 2 ? COLORS.blush : COLORS.mint, {
        ellipse: true,
        groupId,
      }),
      text(slide, "metric-value", `${75 + index * 5}%`, left + 15, 205, 120, 55, {
        font: "Arial",
        fontSize: 28,
        color: COLORS.ink,
        bold: true,
        align: "center",
        textType: "itemNumber",
        textLineHeight: 1,
        lineHeight: 1,
        groupId,
      }),
      text(slide, "item-title", `指标 ${index + 1}`, left - 5, 325, 160, 70, {
        fontSize: 24,
        color: COLORS.ink,
        bold: true,
        align: "center",
        textType: "itemTitle",
        minimumFontSize: 20,
        textLineHeight: 1.2,
        lineHeight: 1.2,
        groupId,
      }),
      text(slide, "item", "指标说明", left - 5, 405, 160, 80, {
        fontSize: 16,
        align: "center",
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
    );
  }
  slide.elements.push(image(slide, "sweep", ASSETS.eucalyptusSweep, 260, 475, 480, 82, { fixedRatio: true }));
  return slide;
}


function endBotanicalFrame() {
  const slide = createSlide("end-botanical-frame", "end", {
    preserve: ["cover-end symmetry", "corner eucalyptus", "quiet central closing area"],
    deviations: ["source media and fixed year replaced"],
    titleFitLimits: { maxWide: 24, maxAscii: 48, singleWide: 12, singleAscii: 24 },
  });
  slide.elements.push(
    image(slide, "background", ASSETS.endBackground, 0, 0, 1000, 562.5),
    image(slide, "corner-upper", ASSETS.eucalyptusCornerUpper, 720, -20, 300, 193, { fixedRatio: true }),
    shape(slide, "closing-panel", 225, 170, 550, 230, "rgba(255,255,255,0.86)", {
      rounded: true,
      outline: COLORS.eucalyptus,
      outlineWidth: 2,
    }),
    text(slide, "title", "感谢聆听", 285, 220, 430, 92, {
      fontSize: 50,
      color: COLORS.ink,
      bold: true,
      align: "center",
      textType: "title",
      minimumFontSize: 50,
      textLineHeight: 1.15,
      lineHeight: 1.15,
    }),
    text(slide, "content", "期待下一次交流与行动", 315, 325, 370, 55, {
      fontSize: 18,
      align: "center",
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  return slide;
}


function endAction() {
  const slide = createSlide("end-action", "end", {
    preserve: ["cover-end symmetry", "three-step closing rhythm", "botanical edge framing"],
    deviations: ["action items added as editable semantic groups"],
  });
  slide.elements.push(
    image(slide, "background", ASSETS.endBackground, 0, 0, 1000, 562.5),
    shape(slide, "safe-panel", 85, 85, 830, 405, "rgba(255,255,255,0.88)", {
      rounded: true,
      outline: COLORS.mint,
      outlineWidth: 1,
    }),
    text(slide, "title", "下一步行动", 180, 105, 640, 90, {
      fontSize: 44,
      color: COLORS.ink,
      bold: true,
      align: "center",
      textType: "title",
      minimumFontSize: 44,
    }),
    text(slide, "content", "明确负责人、完成标准和复盘时间", 220, 195, 560, 58, {
      fontSize: 18,
      align: "center",
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  for (let index = 0; index < 3; index += 1) {
    const left = 130 + index * 255;
    const groupId = `end-action-item-${index + 1}`;
    slide.elements.push(
      shape(slide, "action-card", left, 295, 220, 120, "rgba(246,247,243,0.94)", {
        rounded: true,
        outline: index % 2 ? COLORS.blush : COLORS.eucalyptus,
        outlineWidth: 1,
        groupId,
      }),
      shape(slide, "action-node", left + 16, 330, 48, 48, index % 2 ? COLORS.blush : COLORS.mint, {
        ellipse: true,
        groupId,
      }),
      text(slide, "action-number", String(index + 1).padStart(2, "0"), left + 16, 336, 48, 36, {
        font: "Arial",
        fontSize: 14,
        color: COLORS.ink,
        bold: true,
        align: "center",
        textLineHeight: 1,
        lineHeight: 1,
        groupId,
      }),
      text(slide, "action-item", `行动 ${index + 1}`, left + 78, 329, 120, 52, {
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


function buildTemplate(stage) {
  const allSlides = [
    coverBotanicalFrame(),
    coverImage(),
    contentsSlide(2),
    contentsSlide(3),
    contentsSlide(4),
    contentsSlide(5),
    contentsSlide(6),
    contentsSlide(10),
    transitionEucalyptus(),
    transitionFern(),
    statementSlide(),
    contentImageOne(),
    contentTextTwo(),
    contentTextThree(),
    contentTextFour(),
    metricsSlide(),
    endBotanicalFrame(),
    endAction(),
  ].map(finalizeSlide);
  const selectedIds = new Set(
    stage === "probe"
      ? PROBE_IDS
      : stage === "sample"
        ? SAMPLE_IDS
        : stage === "mvp"
          ? MVP_IDS
          : PRODUCTION_IDS,
  );
  const slides = allSlides.filter(slide => selectedIds.has(slide.id));
  const actualIds = new Set(slides.map(slide => slide.id));
  const missing = [...selectedIds].filter(id => !actualIds.has(id));
  if (missing.length) throw new Error(`模板缺少声明版式: ${missing.join(", ")}`);
  return {
    id: "template_19",
    title: "水彩绿植轻商务",
    width: 1000,
    height: 562.5,
    theme: {
      themeColors: [COLORS.eucalyptus, COLORS.mint, COLORS.ink, COLORS.blush, COLORS.yellow],
      fontColor: COLORS.body,
      fontName: "微软雅黑",
      backgroundColor: COLORS.background,
      shadow: { h: 2, v: 3, blur: 5, color: "#000000", opacity: 0.12 },
      outline: { width: 1, color: COLORS.mint, style: "solid" },
    },
    metadata: {
      aspectRatio: "16:9",
      buildStage: stage,
      sourceReference: "精品系列(21).pptx",
      sourceReferenceSha256: "E80BFD5543B8C18F79181463E54D8FF6843C8DA13E6BD4D84141BA4E26A0211D",
      rightsPolicy: "reference-media-excluded",
      sourceFidelity: "high-composition-color-spacing-rhythm",
      probeSlideIds: PROBE_IDS,
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
  if (!new Set(["probe", "sample", "mvp", "production"]).has(stage)) {
    throw new Error("--stage 只能是 probe、sample、mvp 或 production");
  }
  if (!output) {
    throw new Error("用法: node utils/build_watercolor_botanical_template.mjs [--stage probe|sample|mvp|production] <输出JSON>");
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

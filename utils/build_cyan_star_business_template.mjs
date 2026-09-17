#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, "..");
const TEMPLATE_DIR = path.join(ROOT, "backend", "main_api", "template");

const COLORS = {
  deepSpace: "#020814",
  midnight: "#071A2F",
  cyan: "#00DCEB",
  teal: "#0A8E99",
  white: "#F4FBFF",
  body: "#A8BBCB",
  grid: "#1A3955",
};

const ASSETS = {
  cover: "template_23_asset_bg_cover_v1.jpg",
  content: "template_23_asset_bg_content_v1.jpg",
  section: "template_23_asset_bg_section_v1.jpg",
  end: "template_23_asset_bg_end_v1.jpg",
  particles: "template_23_asset_particle_field_v1.png",
  horizon: "template_23_asset_horizon_glow_v1.png",
  titleFlare: "template_23_asset_title_flare_v1.png",
  imageHalo: "template_23_asset_image_halo_v1.png",
  gridArc: "template_23_asset_grid_arc_v1.png",
};

const REFERENCE = {
  filename: "星空风格(1).pptx",
  sha256: "22BA3CA2A866D7064A3FF568122FF3635BC758F9D5E87CDC5F41F23E05CF882B",
};


function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}


function createSlide(id, type, options = {}) {
  return {
    id,
    type,
    elements: [],
    background: { type: "solid", color: options.background || COLORS.deepSpace },
    ...(options.variantKey ? { variantKey: options.variantKey } : {}),
    ...(options.variantAliases ? { variantAliases: options.variantAliases } : {}),
    ...(options.variantMode ? { variantMode: options.variantMode } : {}),
    ...(options.allowedItemCounts ? { allowedItemCounts: options.allowedItemCounts } : {}),
    ...(options.layoutKind ? { layoutKind: options.layoutKind } : {}),
    ...(options.metricValueField ? { metricValueField: options.metricValueField } : {}),
    ...(options.preserveEndItemBody ? { preserveEndItemBody: true } : {}),
    ...(options.titleFitLimits ? { titleFitLimits: options.titleFitLimits } : {}),
  };
}


function nextId(slide, role) {
  return `t23-${slide.id}-${role}-${String(slide.elements.length + 1).padStart(3, "0")}`;
}


function assetUrl(filename) {
  return `/api/data/${filename}`;
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
    ...(options.lock === false ? {} : { lock: true }),
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(options.clip ? { clip: options.clip } : {}),
    ...(options.strictImageCount ? { strictImageCount: true } : {}),
    ...(options.requireSourceDimensions ? { requireSourceDimensions: true } : {}),
  };
}


function text(slide, role, value, left, top, width, height, options = {}) {
  const align = options.align || "left";
  const fontSize = options.fontSize || 18;
  const color = options.color || COLORS.body;
  const fontFamily = options.fontFamily || "微软雅黑";
  const weight = options.bold ? 700 : 400;
  const lineHeight = options.lineHeight || 1.35;
  return {
    type: "text",
    id: nextId(slide, role),
    left,
    top,
    width,
    height,
    rotate: 0,
    defaultFontName: fontFamily,
    defaultColor: color,
    content: `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: ${fontFamily};line-height: ${lineHeight};font-weight: ${weight};">${escapeHtml(value)}</span></p>`,
    ...(options.textType ? { textType: options.textType } : {}),
    ...(options.minimumFontSize ? { minimumFontSize: options.minimumFontSize } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
    textLineHeight: lineHeight,
  };
}


function shape(slide, role, left, top, width, height, options = {}) {
  const ellipse = options.geometry === "ellipse";
  return {
    type: "shape",
    id: nextId(slide, role),
    left,
    top,
    width,
    height,
    viewBox: [200, 200],
    path: ellipse
      ? "M 100 0 A 100 100 0 1 1 99.9 0 Z"
      : "M 0 0 L 200 0 L 200 200 L 0 200 Z",
    fill: options.fill || COLORS.midnight,
    fixedRatio: false,
    rotate: 0,
    outline: {
      color: options.outlineColor || COLORS.grid,
      width: options.outlineWidth ?? 1,
      style: "solid",
    },
    ...(options.lock ? { lock: true } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
  };
}


function line(slide, role, left, top, endX, endY = 0, options = {}) {
  return {
    type: "line",
    id: nextId(slide, role),
    left,
    top,
    start: [0, 0],
    end: [endX, endY],
    points: ["", ""],
    color: options.color || COLORS.grid,
    style: "solid",
    width: options.width || 1,
    rotate: 0,
    ...(options.lock ? { lock: true } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
  };
}


function addBackground(slide, filename) {
  slide.elements.push(image(slide, "background", assetUrl(filename), 0, 0, 1000, 562.5));
}


function addHeader(slide, label = "页面标题") {
  slide.elements.push(
    text(slide, "title", label, 68, 42, 720, 66, {
      fontSize: 34,
      color: COLORS.white,
      bold: true,
      textType: "title",
      minimumFontSize: 30,
      lineHeight: 1.12,
    }),
    image(slide, "title-flare", assetUrl(ASSETS.titleFlare), 63, 112, 380, 38, {
      fixedRatio: true,
    }),
  );
}


function cover(id, visual = false) {
  const slide = createSlide(id, "cover", {
    variantMode: "deterministic",
    titleFitLimits: { maxWide: 20, maxAscii: 42, singleWide: 10, singleAscii: 22 },
  });
  addBackground(slide, visual ? ASSETS.content : ASSETS.cover);
  if (visual) {
    slide.elements.push(
      image(slide, "grid-arc", assetUrl(ASSETS.gridArc), 520, 25, 480, 270, { fixedRatio: true }),
      image(slide, "particles", assetUrl(ASSETS.particles), 600, 120, 400, 360, { fixedRatio: true }),
      image(slide, "horizon", assetUrl(ASSETS.horizon), 80, 350, 840, 210, { fixedRatio: true }),
    );
  } else {
    slide.elements.push(image(slide, "horizon", assetUrl(ASSETS.horizon), 40, 355, 920, 245, {
      fixedRatio: true,
    }));
  }
  slide.elements.push(
    text(slide, "title", "蓝曜星幕商务汇报", visual ? 96 : 88, 145, visual ? 650 : 700, 145, {
      fontSize: 54,
      color: COLORS.white,
      bold: true,
      textType: "title",
      minimumFontSize: 46,
      lineHeight: 1.08,
    }),
    text(slide, "content", "洞察趋势 · 聚焦增长 · 共创未来", visual ? 101 : 93, 310, 590, 64, {
      fontSize: 20,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  return slide;
}


function contents(count) {
  const slide = createSlide(`contents-${count}`, "contents");
  addBackground(slide, ASSETS.content);
  addHeader(slide, "目录");
  const columns = 2;
  const rows = Math.ceil(count / columns);
  const rowHeight = rows >= 5 ? 68 : rows === 4 ? 78 : 98;
  const top = rows >= 5 ? 150 : 165;
  for (let index = 0; index < count; index += 1) {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const left = 78 + column * 452;
    const itemTop = top + row * rowHeight;
    const groupId = `${slide.id}-item-${index + 1}`;
    slide.elements.push(
      text(slide, "item-number", String(index + 1).padStart(2, "0"), left, itemTop, 60, 42, {
        fontSize: 23,
        fontFamily: "Arial",
        color: COLORS.cyan,
        bold: true,
        textType: "itemNumber",
        minimumFontSize: 20,
        lineHeight: 1.05,
        groupId,
      }),
      text(slide, "item", `目录项目${index + 1}`, left + 72, itemTop + 1, 322, 44, {
        fontSize: rows >= 5 ? 17 : 19,
        color: COLORS.white,
        textType: "item",
        minimumFontSize: 15,
        groupId,
      }),
      line(slide, "item-rule", left + 72, itemTop + 47, 318, 0, {
        color: COLORS.grid,
        width: 1,
        groupId,
      }),
    );
  }
  slide.elements.push(image(slide, "grid-arc", assetUrl(ASSETS.gridArc), 720, 300, 280, 158, {
    fixedRatio: true,
  }));
  return slide;
}


function transition(id, mode) {
  const aliases = mode === "particle" ? ["particle", "stage"] : [];
  const slide = createSlide(id, "transition", {
    variantKey: mode === "particle" ? "horizon" : "spectrum",
    variantAliases: aliases,
  });
  addBackground(slide, ASSETS.section);
  if (mode === "particle") {
    slide.elements.push(image(slide, "particles", assetUrl(ASSETS.particles), 585, 45, 415, 372, {
      fixedRatio: true,
    }));
  } else {
    slide.elements.push(
      image(slide, "horizon", assetUrl(ASSETS.horizon), 135, 310, 730, 205, { fixedRatio: true }),
      image(slide, "grid-arc", assetUrl(ASSETS.gridArc), 700, 255, 300, 169, { fixedRatio: true }),
    );
  }
  slide.elements.push(
    text(slide, "part-number", "01", 82, 142, 180, 120, {
      fontSize: 76,
      fontFamily: "Arial",
      color: COLORS.cyan,
      bold: true,
      textType: "partNumber",
      minimumFontSize: 64,
      lineHeight: 1,
    }),
    line(slide, "number-rule", 90, 278, 180, 0, { color: COLORS.cyan, width: 2, lock: true }),
    text(slide, "title", "章节标题", 315, 165, 570, 96, {
      fontSize: 46,
      color: COLORS.white,
      bold: true,
      textType: "title",
      minimumFontSize: 40,
      lineHeight: 1.08,
    }),
    text(slide, "content", "章节说明文字", 320, 285, 500, 72, {
      fontSize: 18,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 15,
    }),
  );
  return slide;
}


function contentFocus() {
  const slide = createSlide("content-focus-1", "content", { allowedItemCounts: [1] });
  addBackground(slide, ASSETS.content);
  addHeader(slide, "核心结论");
  const groupId = `${slide.id}-item-1`;
  slide.elements.push(
    shape(slide, "focus-panel", 105, 175, 790, 270, {
      fill: COLORS.midnight,
      outlineColor: COLORS.grid,
      outlineWidth: 2,
      groupId,
    }),
    image(slide, "horizon", assetUrl(ASSETS.horizon), 180, 270, 640, 170, {
      fixedRatio: true,
      groupId,
    }),
    text(slide, "item-title", "核心结论标题", 175, 205, 650, 72, {
      fontSize: 30,
      color: COLORS.white,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 25,
      align: "center",
      groupId,
    }),
    text(slide, "item", "用完整说明解释结论，并保留必要的业务上下文。", 180, 322, 640, 86, {
      fontSize: 18,
      color: COLORS.body,
      textType: "item",
      minimumFontSize: 15,
      align: "center",
      groupId,
    }),
  );
  return slide;
}


function contentText(count) {
  const slide = createSlide(`content-text-${count}`, "content", {
    allowedItemCounts: [count],
    titleFitLimits: { maxWide: 24, maxAscii: 48, singleWide: 20, singleAscii: 40 },
  });
  addBackground(slide, ASSETS.content);
  addHeader(slide);
  const grid = {
    2: { left: 74, top: 165, width: 402, height: 300, gapX: 450, columns: 2 },
    3: { left: 54, top: 172, width: 280, height: 295, gapX: 306, columns: 3 },
    4: { left: 58, top: 160, width: 420, height: 150, gapX: 454, gapY: 174, columns: 2 },
  }[count];
  for (let index = 0; index < count; index += 1) {
    const column = index % grid.columns;
    const row = Math.floor(index / grid.columns);
    const left = grid.left + column * grid.gapX;
    const top = grid.top + row * (grid.gapY || 0);
    const groupId = `${slide.id}-item-${index + 1}`;
    const titleHeight = count === 2 ? 74 : count === 3 ? 68 : 46;
    const ruleTop = count === 2 ? 100 : count === 3 ? 94 : 69;
    const bodyTop = count === 2 ? 118 : count === 3 ? 112 : 82;
    const bodyHeight = count === 2 ? 132 : count === 3 ? 138 : 52;
    slide.elements.push(
      shape(slide, "item-panel", left, top, grid.width, grid.height, {
        fill: COLORS.midnight,
        outlineColor: COLORS.grid,
        outlineWidth: 1,
        groupId,
      }),
      text(slide, "item-number", String(index + 1).padStart(2, "0"), left + 22, top + 18, 52, 46, {
        fontSize: 22,
        fontFamily: "Arial",
        color: COLORS.cyan,
        bold: true,
        textType: "itemNumber",
        minimumFontSize: 19,
        lineHeight: 1.05,
        groupId,
      }),
      text(slide, "item-title", `内容标题${index + 1}`, left + 82, top + 18, grid.width - 108, titleHeight, {
        fontSize: count >= 3 ? 18 : 22,
        color: COLORS.white,
        bold: true,
        textType: "itemTitle",
        minimumFontSize: count >= 3 ? 16 : 19,
        lineHeight: count === 4 ? 1.05 : 1.25,
        groupId,
      }),
      line(slide, "item-rule", left + 22, top + ruleTop, grid.width - 44, 0, {
        color: COLORS.teal,
        width: 1,
        groupId,
      }),
      text(slide, "item", "正文信息完整展示，并保持清晰的阅读层级。", left + 22, top + bodyTop, grid.width - 44, bodyHeight, {
        fontSize: count === 4 ? 14 : 16,
        color: COLORS.body,
        textType: "item",
        minimumFontSize: count === 4 ? 12 : 14,
        lineHeight: 1.3,
        groupId,
      }),
    );
  }
  return slide;
}


function contentImage() {
  const slide = createSlide("content-image-1", "content", {
    allowedItemCounts: [1],
    variantKey: "left",
  });
  addBackground(slide, ASSETS.content);
  addHeader(slide, "图文内容");
  const groupId = `${slide.id}-item-1`;
  slide.elements.push(
    image(slide, "content-image", assetUrl(ASSETS.cover), 72, 165, 430, 322, {
      imageType: "content",
      lock: false,
      groupId,
      strictImageCount: true,
      requireSourceDimensions: true,
      clip: { shape: "rect", range: [[0, 0], [100, 100]] },
    }),
    image(slide, "image-halo", assetUrl(ASSETS.imageHalo), 54, 145, 466, 350, {
      fixedRatio: true,
      groupId,
    }),
    text(slide, "item-title", "图文标题", 565, 205, 350, 68, {
      fontSize: 24,
      color: COLORS.white,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 20,
      groupId,
    }),
    line(slide, "item-rule", 565, 286, 120, 0, { color: COLORS.cyan, width: 2, groupId }),
    text(slide, "item", "正文围绕业务图片展开，并保持内容与图片的语义对应。", 565, 318, 350, 145, {
      fontSize: 17,
      color: COLORS.body,
      textType: "item",
      minimumFontSize: 14,
      groupId,
    }),
  );
  return slide;
}


function metrics(count) {
  const slide = createSlide(`content-metrics-${count}`, "content", {
    allowedItemCounts: [count],
    layoutKind: "metrics",
    metricValueField: "value",
  });
  addBackground(slide, ASSETS.content);
  addHeader(slide, "关键业务指标");
  const gap = count === 3 ? 292 : count === 4 ? 224 : 178;
  const width = count === 3 ? 240 : count === 4 ? 190 : 150;
  const leftStart = count === 3 ? 92 : count === 4 ? 52 : 46;
  for (let index = 0; index < count; index += 1) {
    const left = leftStart + index * gap;
    const groupId = `${slide.id}-metric-${index + 1}`;
    const circleSize = count === 5 ? 118 : 138;
    const circleLeft = left + (width - circleSize) / 2;
    slide.elements.push(
      shape(slide, "metric-orbit", circleLeft, 180, circleSize, circleSize, {
        geometry: "ellipse",
        fill: COLORS.midnight,
        outlineColor: COLORS.cyan,
        outlineWidth: 2,
        groupId,
      }),
      text(slide, "metric-value", `${(index + 1) * 20}%`, circleLeft + 8, 222, circleSize - 16, 50, {
        fontSize: count === 5 ? 24 : 28,
        fontFamily: "Arial",
        color: COLORS.cyan,
        bold: true,
        textType: "itemNumber",
        minimumFontSize: count === 5 ? 20 : 24,
        align: "center",
        lineHeight: 1.05,
        groupId,
      }),
      text(slide, "metric-title", `指标${index + 1}`, left, 350, width, 50, {
        fontSize: count === 5 ? 16 : 18,
        color: COLORS.white,
        bold: true,
        textType: "itemTitle",
        minimumFontSize: count === 5 ? 14 : 16,
        align: "center",
        groupId,
      }),
      text(slide, "metric-body", "指标说明", left, 410, width, 62, {
        fontSize: count === 5 ? 13 : 15,
        color: COLORS.body,
        textType: "item",
        minimumFontSize: 12,
        align: "center",
        groupId,
      }),
    );
  }
  slide.elements.push(image(slide, "grid-arc", assetUrl(ASSETS.gridArc), 760, 350, 240, 135, {
    fixedRatio: true,
  }));
  return slide;
}


function end(id, action = false) {
  const slide = createSlide(id, "end", { preserveEndItemBody: action });
  addBackground(slide, ASSETS.end);
  slide.elements.push(
    image(slide, "horizon", assetUrl(ASSETS.horizon), 70, 335, 860, 225, { fixedRatio: true }),
    text(slide, "title", action ? "下一步行动" : "感谢观看", 92, action ? 70 : 152, 620, 110, {
      fontSize: action ? 42 : 54,
      color: COLORS.white,
      bold: true,
      textType: "title",
      minimumFontSize: action ? 36 : 48,
      lineHeight: 1.08,
    }),
    text(slide, "content", action ? "把共识转化为可执行的下一步" : "期待与您继续交流", 98, action ? 155 : 285, 530, 68, {
      fontSize: 19,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  if (action) {
    for (let index = 0; index < 3; index += 1) {
      const groupId = `${slide.id}-action-${index + 1}`;
      slide.elements.push(
        text(slide, "item-number", String(index + 1).padStart(2, "0"), 105, 235 + index * 70, 54, 40, {
          fontSize: 21,
          fontFamily: "Arial",
          color: COLORS.cyan,
          bold: true,
          minimumFontSize: 18,
          groupId,
        }),
        text(slide, "item", `行动项目${index + 1}`, 170, 232 + index * 70, 430, 52, {
          fontSize: 17,
          color: COLORS.white,
          textType: "item",
          minimumFontSize: 14,
          groupId,
        }),
      );
    }
  }
  return slide;
}


function buildProductionSlides() {
  return [
    cover("cover-horizon"),
    cover("cover-visual", true),
    ...[2, 3, 4, 5, 6, 10].map(contents),
    transition("transition-particle-number", "particle"),
    transition("transition-lightline", "lightline"),
    contentFocus(),
    contentText(2),
    contentText(3),
    contentText(4),
    contentImage(),
    metrics(3),
    metrics(4),
    metrics(5),
    end("end-horizon"),
    end("end-action", true),
  ];
}


function build(stage) {
  const production = buildProductionSlides();
  const byId = new Map(production.map((slide) => [slide.id, slide]));
  const probeIds = ["cover-horizon", "content-image-1", "content-metrics-4"];
  const selectedIds = stage === "probe" ? probeIds : production.map((slide) => slide.id);
  return {
    id: "template_23",
    title: "蓝曜星幕商务汇报",
    width: 1000,
    height: 562.5,
    supportsLosslessContentPagination: true,
    paginationGrowthPolicy: { factor: 1.75, slack: 5 },
    theme: {
      themeColors: [COLORS.cyan, COLORS.teal, COLORS.grid],
      fontColor: COLORS.body,
      fontName: "微软雅黑",
      backgroundColor: COLORS.deepSpace,
    },
    metadata: {
      aspectRatio: "16:9",
      buildStage: stage,
      sourceReference: REFERENCE.filename,
      sourceReferenceSha256: REFERENCE.sha256,
      rightsPolicy: "reference-media-excluded",
      sourceFidelity: "cyan-horizon-starfield-business-language",
      probeSlideIds: probeIds,
      productionSlideIds: production.map((slide) => slide.id),
      imageSlotMarker: "imageType=content",
      decorativeImageMarker: "imageType=decoration",
      assetGeneration: "GPT2 图片模板；实际模型工具未暴露",
      assetFiles: Object.values(ASSETS),
    },
    slides: selectedIds.map((id) => byId.get(id)),
  };
}


function parseArgs(argv) {
  const stageIndex = argv.indexOf("--stage");
  const stage = stageIndex >= 0 ? argv[stageIndex + 1] : "production";
  const output = argv.find(
    (value, index) => index !== stageIndex && index !== stageIndex + 1 && value.endsWith(".json"),
  ) || path.join(TEMPLATE_DIR, "template_23.json");
  if (!["probe", "production"].includes(stage)) {
    throw new Error("--stage 必须是 probe 或 production");
  }
  return { stage, output: path.resolve(output) };
}


const { stage, output } = parseArgs(process.argv.slice(2));
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, `${JSON.stringify(build(stage), null, 2)}\n`, "utf8");
process.stdout.write(`${output}\n`);

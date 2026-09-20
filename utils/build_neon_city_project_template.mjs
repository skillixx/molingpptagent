#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, "..");
const TEMPLATE_DIR = path.join(ROOT, "backend", "main_api", "template");

const COLORS = {
  deepSpace: "#0B1830",
  midnight: "#273957",
  cyan: "#47CCD4",
  teal: "#56BDB5",
  white: "#F4F8FC",
  body: "#B8C8DA",
  grid: "#273957",
};

const ASSETS = {
  cover: "template_24_asset_bg_cover_v1.jpg",
  content: "template_24_asset_bg_content_v1.jpg",
  section: "template_24_asset_bg_section_v1.jpg",
  end: "template_24_asset_bg_end_v1.jpg",
  particles: "template_24_asset_skyline_corner_v1.png",
  horizon: "template_24_asset_route_light_v1.png",
  titleFlare: "template_24_asset_edge_beam_v1.png",
  imageHalo: "template_24_asset_city_glow_purple_v1.jpg",
  gridArc: "template_24_asset_city_grid_blue_v1.jpg",
};

// 说明：探针和生产版均使用本模板独立构建器，不直接修改源 PPTX。
const REFERENCE = {
  filename: "项目策划(1).pptx",
  sha256: "56CF0EA80E781D55DF1D4EE565DFA8858A0F9F61B2F88E88617166EBEFBAA0E5",
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
  return `t24-${slide.id}-${role}-${String(slide.elements.length + 1).padStart(3, "0")}`;
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
    ...(Number.isFinite(options.minimumSourceWidth) && options.minimumSourceWidth > 0
      ? { minimumSourceWidth: options.minimumSourceWidth }
      : {}),
    ...(Number.isFinite(options.minimumSourceHeight) && options.minimumSourceHeight > 0
      ? { minimumSourceHeight: options.minimumSourceHeight }
      : {}),
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
    // 正文、说明和目录采用同一可读下限，不继承相邻模板的 12px 正文规则。
    ...(options.minimumFontSize ? { minimumFontSize: ["item", "content"].includes(options.textType) ? Math.max(16, options.minimumFontSize) : options.minimumFontSize } : {}),
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
    // 竖向光束不能横向拉伸成标题装饰，标题下使用可编辑细线。
    line(slide, "title-rule", 68, 118, 115, 0, { color: COLORS.cyan, width: 2 }),
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
      image(slide, "particles", assetUrl(ASSETS.particles), 700, 295, 300, 225, { fixedRatio: true }),
      image(slide, "horizon", assetUrl(ASSETS.horizon), 80, 460, 840, 100),
    );
  } else {
    // 光轨保持在画布底部，编辑器不会自动裁掉越界图片。
    slide.elements.push(image(slide, "horizon", assetUrl(ASSETS.horizon), 40, 462, 920, 100));
  }
  slide.elements.push(
    text(slide, "title", "深蓝霓虹城市项目策划", visual ? 96 : 88, 145, visual ? 650 : 700, 145, {
      fontSize: 54,
      color: COLORS.white,
      bold: true,
      textType: "title",
      minimumFontSize: 46,
      lineHeight: 1.08,
    }),
    text(slide, "content", "项目背景、实施路径与行动安排", visual ? 101 : 93, 310, 590, 64, {
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
  slide.elements.push(image(slide, "grid-texture", assetUrl(ASSETS.gridArc), 870, 526, 110, 30));
  return slide;
}


function transition(id, mode) {
  const cityOnLeft = mode === "particle";
  const slide = createSlide(id, "transition", {
    variantKey: cityOnLeft ? "left" : "right",
    // 公共章节轮换使用四个稳定别名，将其映射到两种城市方向，不修改公共选版规则。
    variantAliases: cityOnLeft ? ["horizon", "particle"] : ["spectrum", "stage"],
  });
  addBackground(slide, ASSETS.section);
  // 仅镜像无文字城市背景；编号与标题放在另一侧的安静区域。
  if (!cityOnLeft) slide.elements[0].flipH = true;
  const textLeft = cityOnLeft ? 480 : 72;
  slide.elements.push(
    text(slide, "part-number", "01", textLeft, 115, 180, 100, {
      fontSize: 76,
      fontFamily: "Arial",
      color: COLORS.cyan,
      bold: true,
      textType: "partNumber",
      minimumFontSize: 64,
      lineHeight: 1,
    }),
    line(slide, "number-rule", textLeft, 228, 130, 0, { color: COLORS.cyan, width: 2, lock: true }),
    text(slide, "title", "章节标题", textLeft, 255, 445, 110, {
      fontSize: 46,
      color: COLORS.white,
      bold: true,
      textType: "title",
      minimumFontSize: 40,
      lineHeight: 1.08,
    }),
    text(slide, "content", "章节说明文字", textLeft, 383, 445, 78, {
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
    image(slide, "city-corner", assetUrl(ASSETS.particles), 760, 450, 140, 105),
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
    4: { left: 58, top: 150, width: 420, height: 174, gapX: 454, gapY: 188, columns: 2 },
  }[count];
  for (let index = 0; index < count; index += 1) {
    const column = index % grid.columns;
    const row = Math.floor(index / grid.columns);
    const left = grid.left + column * grid.gapX;
    const top = grid.top + row * (grid.gapY || 0);
    const groupId = `${slide.id}-item-${index + 1}`;
    const titleHeight = count === 2 ? 74 : count === 3 ? 68 : 46;
    const ruleTop = count === 2 ? 100 : count === 3 ? 94 : 62;
    const bodyTop = count === 2 ? 118 : count === 3 ? 112 : 73;
    const bodyHeight = count === 2 ? 132 : count === 3 ? 138 : 92;
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
        fontSize: 16,
        color: COLORS.body,
        textType: "item",
        minimumFontSize: 16,
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
      // 三组正式换图样本的共同下限，兼顾横图、竖图和方图的清晰裁切。
      minimumSourceWidth: 600,
      minimumSourceHeight: 450,
      clip: { shape: "rect", range: [[0, 0], [100, 100]] },
    }),
    // 边饰独立于业务分组并位于最外侧，不能覆盖可替换照片。
    image(slide, "edge-beam", assetUrl(ASSETS.titleFlare), 938, 145, 60, 360),
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
      minimumFontSize: 16,
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
        fontSize: 16,
        color: COLORS.body,
        textType: "item",
        minimumFontSize: 12,
        align: "center",
        groupId,
      }),
    );
  }
  slide.elements.push(image(slide, "city-glow", assetUrl(ASSETS.imageHalo), 818, 490, 160, 65));
  return slide;
}


function end(id, action = false) {
  const slide = createSlide(id, "end", { preserveEndItemBody: action });
  addBackground(slide, ASSETS.end);
  slide.elements.push(
    image(slide, "horizon", assetUrl(ASSETS.horizon), 70, 465, 860, 94),
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
  // 生产库存固定为 18 个版式，G2 只通过 probe 阶段选择其中 3 页。
  return [
    cover("cover-city"),
    cover("cover-city-minimal", true),
    ...[2, 3, 4, 5, 6, 10].map(contents),
    transition("transition-city-left", "particle"),
    transition("transition-city-right", "lightline"),
    contentFocus(),
    contentText(2),
    contentText(3),
    contentText(4),
    contentImage(),
    metrics(4),
    end("end-city"),
    end("end-action", true),
  ];
}

function build(stage) {
  const production = buildProductionSlides();
  const byId = new Map(production.map((slide) => [slide.id, slide]));
  const probeIds = ["cover-city", "content-text-4", "content-image-1"];
  const mvpIds = ["cover-city", "contents-2", "contents-3", "contents-4", "contents-5", "contents-6", "contents-10", "transition-city-left", "content-text-2", "content-text-3", "content-text-4", "end-city"];
  const selectedIds = stage === "probe" ? probeIds : stage === "mvp" ? mvpIds : production.map((slide) => slide.id);
  return {
    id: "template_24",
    title: "深蓝霓虹城市项目策划",
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
      sourceFidelity: "deep-blue-neon-city-project-planning-language",
      probeSlideIds: probeIds,
      mvpSlideIds: mvpIds,
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
    // 未传 --stage 时首个参数就是输出文件，不能因 -1 + 1 而错误跳过。
    (value, index) => (stageIndex < 0 || (index !== stageIndex && index !== stageIndex + 1)) && value.endsWith(".json"),
  ) || path.join(TEMPLATE_DIR, "template_24.json");
  if (!["probe", "mvp", "production"].includes(stage)) {
    throw new Error("--stage 必须是 probe、mvp 或 production");
  }
  return { stage, output: path.resolve(output) };
}


const { stage, output } = parseArgs(process.argv.slice(2));
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, `${JSON.stringify(build(stage), null, 2)}\n`, "utf8");
process.stdout.write(`${output}\n`);

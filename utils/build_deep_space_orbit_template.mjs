#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = path.resolve(SCRIPT_DIR, "..");
const SOURCE_TEMPLATE = path.join(
  REPOSITORY_ROOT,
  "backend",
  "main_api",
  "template",
  "template_8.json",
);

const COLORS = {
  background: "#04131F",
  surface: "#0A2942",
  cyan: "#19C7D9",
  blue: "#4E7FFF",
  purple: "#8B5CFF",
  orange: "#F3A846",
  text: "#F7FBFF",
  muted: "#B7C6D4",
  border: "#224A66",
};

const ASSETS = {
  background: "/api/data/template_16_asset_bg_space_dark_v1.jpg",
  ring: "/api/data/template_16_asset_orbital_ring_v1.png",
  constellation: "/api/data/template_16_asset_constellation_edge_v1.png",
  glow: "/api/data/template_16_asset_nebula_glow_v1.png",
};

const SLIDE_ID_MAP = new Map([
  ["cover-geometric", "cover-orbit"],
  ["cover-visual", "cover-image"],
  ["transition-standard", "transition-orbit"],
  ["transition-graphic", "transition-nebula"],
  ["content-conclusion-1", "content-focus-1"],
  ["end-minimal", "end-orbit"],
  ["end-geometric", "end-action"],
]);

const MVP_IDS = [
  "cover-orbit",
  "contents-2",
  "contents-3",
  "contents-4",
  "contents-5",
  "contents-6",
  "contents-10",
  "transition-orbit",
  "content-text-2",
  "content-text-3",
  "content-text-4",
  "end-orbit",
];

const PRODUCTION_IDS = [
  ...MVP_IDS,
  "cover-image",
  "transition-nebula",
  "content-focus-1",
  "content-image-1",
  "content-image-2",
  "end-action",
];

const SOURCE_REFERENCE_SLIDES = {
  "cover-orbit": [1],
  "cover-image": [1, 20],
  "contents-2": [2],
  "contents-3": [2],
  "contents-4": [2],
  "contents-5": [2],
  "contents-6": [2],
  "contents-10": [2],
  "transition-orbit": [3, 9, 14, 19],
  "transition-nebula": [3, 9, 14, 19],
  "content-focus-1": [4, 15],
  "content-text-2": [4, 5, 10],
  "content-text-3": [6, 8, 12],
  "content-text-4": [5, 7, 11],
  "content-image-1": [8, 17, 20, 21],
  "content-image-2": [22, 24],
  "end-orbit": [25],
  "end-action": [25],
};


function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}


function replaceColorValue(value) {
  if (typeof value !== "string") return value;
  const replacements = new Map([
    ["#17191D", COLORS.background],
    ["#0E1A25", COLORS.background],
    ["#22384B", COLORS.surface],
    ["#365B73", COLORS.border],
    ["#28A7CF", COLORS.cyan],
    ["#46A4DB", COLORS.blue],
    ["#237FB5", COLORS.purple],
    ["#FFFFFF", COLORS.text],
    ["#B9C9D8", COLORS.muted],
  ]);
  let result = value;
  for (const [source, target] of replacements) {
    result = result.replaceAll(source, target);
  }
  result = result.replaceAll("rgba(34,56,75,0.88)", "rgba(10,41,66,0.88)");
  result = result.replaceAll("rgba(34,56,75,0.9)", "rgba(10,41,66,0.90)");
  return result;
}


function rethemeValue(value) {
  if (Array.isArray(value)) return value.map(rethemeValue);
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      value[key] = rethemeValue(child);
    }
    return value;
  }
  return replaceColorValue(value);
}


function assetForSource(source) {
  if (typeof source !== "string") return source;
  if (source.includes("network_mesh")) return ASSETS.constellation;
  if (source.includes("tech_glow")) return ASSETS.glow;
  if (source.includes("bg_dark")) return ASSETS.background;
  return source;
}


function nextId(slide, role) {
  slide.__counter = (slide.__counter || 0) + 1;
  return `t16-${slide.id}-${role}-${String(slide.__counter).padStart(3, "0")}`;
}


function image(slide, role, src, left, top, width, height, options = {}) {
  return {
    type: "image",
    id: nextId(slide, role),
    left,
    top,
    width,
    height,
    src,
    fixedRatio: false,
    rotate: options.rotate || 0,
    imageType: options.imageType || "decoration",
    lock: options.lock ?? true,
    ...(options.strictImageCount ? { strictImageCount: true } : {}),
    ...(options.requireSourceDimensions ? { requireSourceDimensions: true } : {}),
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
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(!ellipse && options.rounded
      ? { pathFormula: "roundRect", keypoints: [0.08] }
      : {}),
  };
}


function text(slide, role, value, left, top, width, height, options = {}) {
  const fontSize = options.fontSize || 18;
  const color = options.color || COLORS.text;
  const font = options.font || "微软雅黑";
  const align = options.align || "left";
  const strongOpen = options.bold ? "<strong>" : "";
  const strongClose = options.bold ? "</strong>" : "";
  return {
    type: "text",
    id: nextId(slide, role),
    left,
    top,
    width,
    height,
    rotate: 0,
    defaultFontName: font,
    defaultColor: color,
    vertical: false,
    content: `<p style="text-align: ${align};"><span style="color: ${color};font-size: ${fontSize}px;font-family: ${font};line-height: 1.35;">${strongOpen}${value}${strongClose}</span></p>`,
    ...(options.textType ? { textType: options.textType } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
    ...(options.minimumFontSize ? { minimumFontSize: options.minimumFontSize } : {}),
    ...(options.textLineHeight ? { textLineHeight: options.textLineHeight } : {}),
    ...(options.textWidthFactor ? { textWidthFactor: options.textWidthFactor } : {}),
  };
}


function normalizeElement(element) {
  element.id = String(element.id || "element").replace(/^t8-/, "t16-");
  if (element.src) element.src = assetForSource(element.src);
  const slotType = element.textType || element.text?.type;
  if (slotType === "title") element.minimumFontSize = Math.max(35, element.minimumFontSize || 0);
  if (slotType === "itemTitle") element.minimumFontSize = Math.max(24, element.minimumFontSize || 0);
  if (["content", "item"].includes(slotType)) element.minimumFontSize = Math.max(16, element.minimumFontSize || 0);
  if (element.type === "image" && element.imageType === "content") {
    element.strictImageCount = true;
    element.requireSourceDimensions = true;
    element.lock = false;
  }
  return rethemeValue(element);
}


function addRing(slide, placement) {
  slide.elements.push(
    image(
      slide,
      "orbital-ring",
      ASSETS.ring,
      placement.left,
      placement.top,
      placement.width,
      placement.height,
    ),
  );
}


function keepElementInsideCanvas(element) {
  "use strict";
  // PPTist 编辑器不会替幻灯片裁切越界元素，固定装饰必须在模板数据层收回画布。
  if (element.type === "line") return element;
  if (![element.left, element.top, element.width, element.height].every(Number.isFinite)) return element;
  if (element.left < 0) {
    element.width = Math.max(1, element.width + element.left);
    element.left = 0;
  }
  if (element.top < 0) {
    element.height = Math.max(1, element.height + element.top);
    element.top = 0;
  }
  if (element.left + element.width > 1000) {
    element.width = Math.max(1, 1000 - element.left);
  }
  if (element.top + element.height > 562.5) {
    element.height = Math.max(1, 562.5 - element.top);
  }
  return element;
}


function configureMultiItemCapacity(slide) {
  if (!["content-text-2", "content-text-3", "content-text-4"].includes(slide.id)) return;
  for (const element of slide.elements) {
    const slotType = element.textType || element.text?.type;
    if (slotType === "itemTitle") {
      // 多项标题允许两行，并保持 20px 可读下限；完整长句由上游语义压缩协议保存到正文。
      element.minimumFontSize = 20;
      element.textLineHeight = 1.2;
      element.height = Math.max(70, element.height || 0);
      if (typeof element.content === "string") {
        element.content = element.content.replace(/line-height:\s*[0-9.]+;/g, "line-height: 1.2;");
      }
    }
    if (slide.id === "content-text-4" && slotType === "item") {
      // 原始标题会进入正文开头，四项正文框需容纳至少三行 16px 文本。
      element.height = Math.max(100, element.height || 0);
    }
  }
}


function configureSlide(slide) {
  const oldId = slide.id;
  slide.id = SLIDE_ID_MAP.get(oldId) || oldId;
  slide.__counter = 0;
  slide.elements = slide.elements.map(normalizeElement);
  slide.background = { type: "solid", color: COLORS.background };
  slide.remark = [
    "[Sources]",
    "- Visual composition reference: user-provided 扁平风格(32).pptx",
    "- Reference media excluded; original project assets generated for template_16",
  ].join("\n");
  slide.sourceReferenceSlides = SOURCE_REFERENCE_SLIDES[slide.id] || [];

  if (slide.id.startsWith("contents-")) {
    const count = Number.parseInt(slide.id.split("-").at(-1), 10);
    slide.allowedItemCounts = [count];
  }

  if (slide.type === "content") {
    const allowed = {
      "content-focus-1": [1],
      "content-text-2": [2],
      "content-text-3": [3],
      "content-text-4": [4],
      "content-image-1": [1],
      "content-image-2": [2],
    }[slide.id];
    slide.allowedItemCounts = allowed || slide.allowedItemCounts;
    slide.titleFitLimits = {
      maxWide: 40,
      maxAscii: 80,
      singleWide: 20,
      singleAscii: 44,
    };
    configureMultiItemCapacity(slide);
  }

  if (slide.type === "cover") {
    slide.titleFitLimits = {
      maxWide: slide.id === "cover-image" ? 24 : 36,
      maxAscii: slide.id === "cover-image" ? 48 : 72,
      singleWide: slide.id === "cover-image" ? 15 : 9,
      singleAscii: slide.id === "cover-image" ? 30 : 20,
    };
  }

  if (slide.type === "transition") slide.variantMode = "deterministic";

  if (slide.id === "cover-orbit") {
    for (const element of slide.elements) {
      if (element.textType === "title") {
        Object.assign(element, { left: 86, top: 158, width: 500, height: 160 });
        element.content = element.content
          .replaceAll("font-size: 58px", "font-size: 50px")
          .replaceAll("让复杂信息清晰呈现", "让关键洞察穿越 信息星海");
      }
      if (element.textType === "content") Object.assign(element, { left: 90, top: 336, width: 500, height: 86 });
    }
    addRing(slide, { left: 610, top: 90, width: 315, height: 315 });
  }

  if (slide.id === "cover-image") {
    for (const element of slide.elements) {
      if (element.textType === "content") element.height = Math.max(86, element.height || 0);
    }
    addRing(slide, { left: 622, top: 118, width: 280, height: 280 });
  }

  if (slide.id === "transition-orbit") {
    addRing(slide, { left: 342, top: 70, width: 316, height: 316 });
  }

  if (slide.id === "transition-nebula") {
    slide.elements.push(image(slide, "nebula", ASSETS.glow, 560, 95, 430, 315));
  }

  if (slide.id === "end-orbit") {
    addRing(slide, { left: 350, top: 52, width: 300, height: 300 });
  }

  if (slide.id === "end-action") {
    addRing(slide, { left: 708, top: 40, width: 220, height: 220 });
    const actionLabels = ["确认下一步", "明确负责人", "约定复盘点"];
    for (let index = 0; index < actionLabels.length; index += 1) {
      const groupId = `end-action-item-${index + 1}`;
      const left = 105 + index * 280;
      slide.elements.push(
        shape(slide, "action-card", left, 385, 235, 82, "rgba(10,41,66,0.90)", {
          rounded: true,
          outline: COLORS.border,
          outlineWidth: 1,
          groupId,
        }),
        shape(slide, "action-node", left + 14, 405, 42, 42, COLORS.cyan, {
          ellipse: true,
          groupId,
        }),
        text(slide, "action-number", String(index + 1).padStart(2, "0"), left + 14, 408, 42, 34, {
          font: "Arial",
          fontSize: 14,
          align: "center",
          bold: true,
          groupId,
        }),
        text(slide, "action-item", actionLabels[index], left + 70, 403, 145, 44, {
          fontSize: 17,
          textType: "item",
          minimumFontSize: 16,
          groupId,
        }),
      );
    }
  }

  for (const element of slide.elements) {
    if (element.type === "text" && typeof element.content === "string") {
      element.content = element.content
        .replaceAll("科技蓝扁平演示模板", "深空星环科技演示模板")
        .replaceAll("TECHNOLOGY PRESENTATION", "DEEP SPACE TECHNOLOGY")
        .replaceAll("让复杂信息清晰呈现", "让关键洞察穿越 信息星海")
        .replaceAll("期待下一次交流", "让下一步行动清晰可见")
        .replaceAll("让每一次表达都更清晰、更有影响力", "以清晰结构连接洞察、决策与行动");
    }
    keepElementInsideCanvas(element);
  }

  delete slide.__counter;
  return slide;
}


function buildTemplate(stage) {
  const source = JSON.parse(fs.readFileSync(SOURCE_TEMPLATE, "utf8"));
  const slides = source.slides.map((slide) => configureSlide(deepClone(slide)));
  const selectedIds = stage === "mvp" ? new Set(MVP_IDS) : new Set(PRODUCTION_IDS);
  const selectedSlides = slides.filter((slide) => selectedIds.has(slide.id));
  const actualIds = new Set(selectedSlides.map((slide) => slide.id));
  const missing = [...selectedIds].filter((id) => !actualIds.has(id));
  if (missing.length) throw new Error(`模板缺少声明版式: ${missing.join(", ")}`);

  return {
    id: "template_16",
    title: "深空星环科技",
    width: 1000,
    height: 562.5,
    theme: {
      themeColors: [COLORS.cyan, COLORS.blue, COLORS.purple, COLORS.background, COLORS.surface, COLORS.text],
      fontColor: COLORS.text,
      fontName: "微软雅黑",
      backgroundColor: COLORS.background,
      shadow: { h: 2, v: 3, blur: 5, color: "#000000", opacity: 0.24 },
      outline: { width: 1, color: COLORS.blue, style: "solid" },
    },
    metadata: {
      aspectRatio: "16:9",
      buildStage: stage,
      sourceReference: "扁平风格(32).pptx",
      sourceReferenceSha256: "8ea531f1b9582374f7e79cb5515738d20d5e96c3df1642bed8e9532f036a98ce",
      rightsPolicy: "reference-media-excluded",
      mvpSlideIds: MVP_IDS,
      productionSlideIds: PRODUCTION_IDS,
      imageSlotMarker: "imageType=content",
      decorativeImageMarker: "imageType=decoration",
      assetFiles: Object.values(ASSETS).map((value) => value.split("/").at(-1)),
    },
    slides: selectedSlides,
  };
}


function parseArgs(argv) {
  let stage = "production";
  let output = "";
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--stage") {
      stage = argv[index + 1] || "";
      index += 1;
    } else if (!output) {
      output = argv[index];
    }
  }
  if (!new Set(["mvp", "production"]).has(stage)) {
    throw new Error("--stage 只能是 mvp 或 production");
  }
  if (!output) {
    throw new Error("用法: node utils/build_deep_space_orbit_template.mjs [--stage mvp|production] <输出JSON>");
  }
  return { stage, output: path.resolve(REPOSITORY_ROOT, output) };
}


try {
  const { stage, output } = parseArgs(process.argv.slice(2));
  const template = buildTemplate(stage);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(template, null, 2)}\n`, "utf8");
  process.stdout.write(`${output}\n`);
} catch (error) {
  process.stderr.write(`${error.message || error}\n`);
  process.exit(1);
}

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
  background: "#F4F6F9",
  surface: "#FFFFFF",
  cyan: "#34A7C8",
  blue: "#0877C9",
  deepBlue: "#0648A9",
  paleBlue: "#93BCE8",
  text: "#4B5158",
  muted: "#7B838C",
  border: "#D8DDE3",
};

const ASSETS = {
  background: "/api/data/template_17_asset_bg_light_v1.jpg",
  map: "/api/data/template_17_asset_world_map_dots_v1.png",
  cover: "/api/data/template_17_asset_cover_diamond_cluster_v1.png",
  footer: "/api/data/template_17_asset_diamond_footer_v1.png",
  corner: "/api/data/template_17_asset_diamond_corner_v1.png",
};

const SLIDE_ID_MAP = new Map([
  ["cover-geometric", "cover-diamond"],
  ["cover-visual", "cover-image"],
  ["transition-standard", "transition-banner"],
  ["transition-graphic", "transition-side"],
  ["content-conclusion-1", "content-focus-1"],
  ["end-minimal", "end-diamond"],
  ["end-geometric", "end-action"],
]);

const MVP_IDS = [
  "cover-diamond",
  "contents-2",
  "contents-3",
  "contents-4",
  "contents-5",
  "contents-6",
  "contents-10",
  "transition-banner",
  "content-text-2",
  "content-text-3",
  "content-text-4",
  "end-diamond",
];

const PRODUCTION_IDS = [
  ...MVP_IDS,
  "cover-image",
  "transition-side",
  "content-focus-1",
  "content-image-1",
  "content-image-2",
  "end-action",
];

const SOURCE_REFERENCE_SLIDES = {
  "cover-diamond": [1],
  "cover-image": [1, 20],
  "contents-2": [3],
  "contents-3": [3],
  "contents-4": [3],
  "contents-5": [3],
  "contents-6": [3],
  "contents-10": [3],
  "transition-banner": [4, 10, 17, 24, 31],
  "transition-side": [4, 10, 17, 24, 31],
  "content-focus-1": [5, 15],
  "content-text-2": [6, 16],
  "content-text-3": [7, 9],
  "content-text-4": [8, 15],
  "content-image-1": [11, 34],
  "content-image-2": [38],
  "end-diamond": [40],
  "end-action": [39],
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
    ["#237FB5", COLORS.deepBlue],
    ["#FFFFFF", COLORS.text],
    ["#B9C9D8", COLORS.muted],
  ]);
  let result = value;
  for (const [source, target] of replacements) {
    result = result.replaceAll(source, target);
  }
  result = result.replaceAll("rgba(34,56,75,0.88)", "rgba(255,255,255,0.90)");
  result = result.replaceAll("rgba(34,56,75,0.9)", "rgba(255,255,255,0.92)");
  result = result.replaceAll("rgba(34,56,75,0.92)", "rgba(255,255,255,0.94)");
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
  if (source.includes("network_mesh")) return ASSETS.map;
  if (source.includes("tech_glow")) return ASSETS.corner;
  if (source.includes("bg_dark")) return ASSETS.background;
  return source;
}


function nextId(slide, role) {
  slide.__counter = (slide.__counter || 0) + 1;
  return `t17-${slide.id}-${role}-${String(slide.__counter).padStart(3, "0")}`;
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
  element.id = String(element.id || "element").replace(/^t8-/, "t17-");
  if (element.src) element.src = assetForSource(element.src);
  const slotType = element.textType || element.text?.type;
  if (slotType === "title") element.minimumFontSize = Math.max(35, element.minimumFontSize || 0);
  if (slotType === "itemTitle") element.minimumFontSize = Math.max(24, element.minimumFontSize || 0);
  if (["content", "item"].includes(slotType)) element.minimumFontSize = Math.max(16, element.minimumFontSize || 0);
  if (element.type === "image" && element.imageType === "content") {
    element.src = ASSETS.background;
    element.strictImageCount = true;
    element.requireSourceDimensions = true;
    element.lock = false;
  }
  return rethemeValue(element);
}


function addDecoration(slide, role, src, placement) {
  slide.elements.push(
    image(slide, role, src, placement.left, placement.top, placement.width, placement.height),
  );
}


function annotateContentImageSlots(slide, elements) {
  "use strict";
  // 内容图继承包围卡片的业务分组；占位图尺寸用于模板自检，渲染时会被真实源图尺寸覆盖。
  const contentImages = elements.filter(
    (element) => element.type === "image" && element.imageType === "content",
  );
  for (const [index, contentImage] of contentImages.entries()) {
    const centerX = contentImage.left + contentImage.width / 2;
    const centerY = contentImage.top + contentImage.height / 2;
    const owner = elements.find(
      (element) => element.groupId
        && Number.isFinite(element.left)
        && Number.isFinite(element.top)
        && Number.isFinite(element.width)
        && Number.isFinite(element.height)
        && centerX >= element.left
        && centerX <= element.left + element.width
        && centerY >= element.top
        && centerY <= element.top + element.height,
    );
    contentImage.groupId = owner?.groupId || `${slide.id}-content-image-${index + 1}`;
    contentImage.originalWidth = 1920;
    contentImage.originalHeight = 1080;
  }
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
    "- Visual composition reference: user-provided 动态动画(12).pptx",
    "- Reference media excluded; original project assets generated for template_17",
  ].join("\n");
  slide.sourceReferenceSlides = SOURCE_REFERENCE_SLIDES[slide.id] || [];

  // 参考稿位图全部排除，只保留内容图片槽，并使用本模板素材作为安全占位图。
  const semanticElements = slide.elements.filter(
    (element) => {
      if (element.type === "image") return element.imageType === "content";
      // 来源模板的底部三角形不属于蓝菱视觉，避免和透明菱形素材叠加。
      if (element.type === "shape" && element.path === "M 0 100 L 50 0 L 100 100 Z") return false;
      return true;
    },
  );
  annotateContentImageSlots(slide, semanticElements);
  slide.elements = [
    image(slide, "background", ASSETS.background, 0, 0, 1000, 562.5),
    ...semanticElements,
  ];
  if (["contents", "content"].includes(slide.type)) {
    addDecoration(slide, "world-map", ASSETS.map, { left: 70, top: 90, width: 860, height: 390 });
  }
  if (["content", "end"].includes(slide.type)) {
    addDecoration(slide, "diamond-footer", ASSETS.footer, { left: 0, top: 380, width: 1000, height: 182.5 });
  }

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

  if (slide.id === "cover-diamond") {
    for (const element of slide.elements) {
      if (element.textType === "title") {
        Object.assign(element, { left: 505, top: 150, width: 410, height: 150 });
        element.content = element.content
          .replaceAll("font-size: 58px", "font-size: 50px")
          .replaceAll("让复杂信息清晰呈现", "让商务表达更清晰");
      }
      if (element.textType === "content") Object.assign(element, { left: 510, top: 316, width: 390, height: 86 });
    }
    addDecoration(slide, "cover-cluster", ASSETS.cover, { left: 0, top: 0, width: 1000, height: 562.5 });
  }

  if (slide.id === "cover-image") {
    for (const element of slide.elements) {
      if (element.textType === "content") element.height = Math.max(86, element.height || 0);
    }
    addDecoration(slide, "diamond-corner", ASSETS.corner, { left: 0, top: 0, width: 355, height: 355 });
  }

  if (slide.id === "transition-banner") {
    addDecoration(slide, "diamond-corner", ASSETS.corner, { left: 0, top: 0, width: 390, height: 390 });
    slide.elements.splice(
      1,
      0,
      shape(slide, "section-banner", 160, 150, 840, 130, "rgba(216,221,227,0.82)", {
        outline: COLORS.border,
        outlineWidth: 0,
      }),
    );
  }

  if (slide.id === "transition-side") {
    addDecoration(slide, "diamond-corner", ASSETS.corner, { left: 0, top: 0, width: 330, height: 330 });
    addDecoration(slide, "world-map", ASSETS.map, { left: 230, top: 75, width: 720, height: 405 });
  }

  if (slide.id === "end-diamond") {
    addDecoration(slide, "world-map", ASSETS.map, { left: 120, top: 60, width: 760, height: 430 });
  }

  if (slide.id === "end-action") {
    addDecoration(slide, "diamond-corner", ASSETS.corner, { left: 0, top: 0, width: 300, height: 300 });
    for (const element of slide.elements) {
      if (element.textType === "content") {
        Object.assign(element, { left: 100, top: 310, width: 800, height: 54 });
      }
    }
    const actionLabels = ["确认下一步", "明确负责人", "约定复盘点"];
    for (let index = 0; index < actionLabels.length; index += 1) {
      const groupId = `end-action-item-${index + 1}`;
      const left = 105 + index * 280;
      slide.elements.push(
        shape(slide, "action-card", left, 385, 235, 82, "rgba(255,255,255,0.92)", {
          rounded: true,
          outline: COLORS.border,
          outlineWidth: 1,
          groupId,
        }),
        shape(slide, "action-node", left + 14, 405, 42, 42, COLORS.blue, {
          ellipse: true,
          groupId,
        }),
        text(slide, "action-number", String(index + 1).padStart(2, "0"), left + 14, 408, 42, 34, {
          font: "Arial",
          fontSize: 14,
          color: "#FFFFFF",
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

  // 图片装饰统一置于语义文字、形状和内容图片之后的底层，避免地图覆盖正文。
  const backgroundLayers = slide.elements.filter(
    (element) => element.type === "image" && element.imageType === "decoration" && element.src === ASSETS.background,
  );
  const decorationLayers = slide.elements.filter(
    (element) => element.type === "image" && element.imageType === "decoration" && element.src !== ASSETS.background,
  );
  const foregroundLayers = slide.elements.filter(
    (element) => element.type !== "image" || element.imageType !== "decoration",
  );
  slide.elements = [...backgroundLayers, ...decorationLayers, ...foregroundLayers];

  for (const element of slide.elements) {
    if (element.type === "text" && typeof element.content === "string") {
      element.content = element.content
        .replaceAll("科技蓝扁平演示模板", "蓝菱商务汇报演示模板")
        .replaceAll("TECHNOLOGY PRESENTATION", "BLUE DIAMOND BUSINESS")
        .replaceAll("让复杂信息清晰呈现", "让商务表达更清晰")
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
    id: "template_17",
    title: "蓝菱商务汇报",
    width: 1000,
    height: 562.5,
    theme: {
      themeColors: [COLORS.blue, COLORS.deepBlue, COLORS.paleBlue, COLORS.cyan, COLORS.background, COLORS.text],
      fontColor: COLORS.text,
      fontName: "微软雅黑",
      backgroundColor: COLORS.background,
      shadow: { h: 2, v: 3, blur: 5, color: "#000000", opacity: 0.24 },
      outline: { width: 1, color: COLORS.blue, style: "solid" },
    },
    metadata: {
      aspectRatio: "16:9",
      buildStage: stage,
      sourceReference: "动态动画(12).pptx",
      sourceReferenceSha256: "80a91226e145d048f60a649a5c6460e91ca9a5962c4a0980715451a972099944",
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
    throw new Error("用法: node utils/build_blue_diamond_business_template.mjs [--stage mvp|production] <输出JSON>");
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

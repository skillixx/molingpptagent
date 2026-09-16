#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, "..");
const TEMPLATE_DIR = path.join(ROOT, "backend", "main_api", "template");

const COLORS = {
  ivory: "#F7EFE8",
  paleRose: "#E7C8D0",
  blossom: "#DF8FA5",
  dustyRose: "#B56F7D",
  burgundy: "#7B334D",
  ink: "#211B1C",
  body: "#4A3F40",
  white: "#FFFFFF",
};

const PROBE_ASSETS = {
  background: "template_22_probe_bg.jpg",
  decoration: "template_22_probe_decoration.png",
  content: "template_22_probe_content.jpg",
};

const ASSETS = {
  cover: "template_22_asset_bg_cover_v1.jpg",
  content: "template_22_asset_bg_content_v1.jpg",
  section: "template_22_asset_bg_section_v1.jpg",
  end: "template_22_asset_bg_end_v1.jpg",
  scroll: "template_22_asset_scroll_roll_v1.png",
  titleFrame: "template_22_asset_ink_title_frame_v1.png",
  circle: "template_22_asset_ink_circle_frame_v1.png",
  brush: "template_22_asset_ink_brush_band_v1.png",
  petals: "template_22_asset_petal_sweep_v1.png",
};

const REFERENCE = {
  sha256: "17CBC63F0D9D77B9D8B78018047FEB10D0D284C150A5E761208CF4E0B683460E",
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
    background: { type: "solid", color: options.background || COLORS.ivory },
    ...(options.variantKey ? { variantKey: options.variantKey } : {}),
    ...(options.variantMode ? { variantMode: options.variantMode } : {}),
    ...(options.allowedItemCounts ? { allowedItemCounts: options.allowedItemCounts } : {}),
    ...(options.layoutKind ? { layoutKind: options.layoutKind } : {}),
    ...(options.metricValueField ? { metricValueField: options.metricValueField } : {}),
    ...(options.preserveEndItemBody ? { preserveEndItemBody: true } : {}),
    ...(options.titleFitLimits ? { titleFitLimits: options.titleFitLimits } : {}),
  };
}


function nextId(slide, role) {
  return `t22-${slide.id}-${role}-${String(slide.elements.length + 1).padStart(3, "0")}`;
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
    rotate: 0,
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
    fill: options.fill || "transparent",
    fixedRatio: false,
    rotate: 0,
    outline: {
      color: options.outlineColor || COLORS.dustyRose,
      width: options.outlineWidth ?? 1,
      style: "solid",
    },
    ...(options.lock ? { lock: true } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
  };
}


function line(slide, role, left, top, length, options = {}) {
  return {
    type: "line",
    id: nextId(slide, role),
    left,
    top,
    start: [0, 0],
    end: [length, 0],
    points: ["", ""],
    color: options.color || COLORS.dustyRose,
    style: "solid",
    width: options.width || 1,
    rotate: 0,
    ...(options.lock ? { lock: true } : {}),
    ...(options.groupId ? { groupId: options.groupId } : {}),
  };
}


function addProbeBackground(slide) {
  slide.elements.push(
    image(slide, "background", assetUrl(PROBE_ASSETS.background), 0, 0, 1000, 562.5),
    image(slide, "corner-decoration", assetUrl(PROBE_ASSETS.decoration), 760, 0, 240, 240, {
      fixedRatio: true,
    }),
  );
}


function coverProbe() {
  const slide = createSlide("cover-scroll-blossom", "cover", {
    titleFitLimits: { maxWide: 20, maxAscii: 42, singleWide: 10, singleAscii: 22 },
  });
  addProbeBackground(slide);
  slide.elements.push(
    text(slide, "title", "桃夭墨韵商务汇报", 110, 150, 640, 130, {
      fontSize: 54,
      color: COLORS.burgundy,
      bold: true,
      textType: "title",
      minimumFontSize: 48,
      lineHeight: 1.1,
    }),
    text(slide, "content", "以清晰结构承载东方意境", 115, 305, 520, 62, {
      fontSize: 20,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 16,
    }),
  );
  return slide;
}


function contentImageProbe({ circle = false } = {}) {
  const slide = createSlide(
    circle ? "probe-image-circle-1" : "content-image-1",
    "content",
    {
      variantKey: circle ? "circle" : "left",
      allowedItemCounts: [1],
      titleFitLimits: { maxWide: 22, maxAscii: 44, singleWide: 18, singleAscii: 34 },
    },
  );
  addProbeBackground(slide);
  slide.elements.push(
    text(slide, "title", circle ? "圆形图片验证" : "图文内容验证", 72, 52, 700, 74, {
      fontSize: 34,
      color: COLORS.burgundy,
      bold: true,
      textType: "title",
      minimumFontSize: 30,
      lineHeight: 1.15,
    }),
  );
  const groupId = `${slide.id}-${circle ? "circle-item-1" : "image-item-1"}`;
  slide.elements.push(
    image(
      slide,
      "content-image",
      assetUrl(PROBE_ASSETS.content),
      80,
      155,
      circle ? 285 : 390,
      285,
      {
        imageType: "content",
        lock: false,
        groupId,
        strictImageCount: true,
        requireSourceDimensions: true,
        clip: { shape: circle ? "ellipse" : "rect", range: [[0, 0], [100, 100]] },
      },
    ),
    text(slide, "item-title", "完整标题", circle ? 435 : 525, 195, circle ? 430 : 380, 64, {
      fontSize: 24,
      color: COLORS.ink,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 20,
      groupId,
    }),
    text(slide, "item", "正文编辑和换图后必须完整保留。", circle ? 435 : 525, 285, circle ? 430 : 380, 130, {
      fontSize: 18,
      color: COLORS.body,
      textType: "item",
      minimumFontSize: 16,
      groupId,
    }),
  );
  return slide;
}


function buildProbe() {
  const slides = [coverProbe(), contentImageProbe(), contentImageProbe({ circle: true })];
  return {
    id: "template_22",
    title: "桃夭墨韵商务汇报",
    width: 1000,
    height: 562.5,
    supportsLosslessContentPagination: true,
    paginationGrowthPolicy: { factor: 1.75, slack: 5 },
    theme: {
      themeColors: [COLORS.burgundy, COLORS.blossom, COLORS.ink],
      fontColor: COLORS.body,
      fontName: "微软雅黑",
      backgroundColor: COLORS.ivory,
    },
    metadata: {
      aspectRatio: "16:9",
      buildStage: "probe",
      sourceReference: "中国风格(5).pptx",
      sourceReferenceSha256: REFERENCE.sha256,
      rightsPolicy: "reference-media-excluded",
      probeSlideIds: slides.map((slide) => slide.id),
      probeAssetFiles: Object.values(PROBE_ASSETS),
      imageSlotMarker: "imageType=content",
      decorativeImageMarker: "imageType=decoration",
    },
    slides,
  };
}


function addBackground(slide, filename) {
  slide.elements.push(image(slide, "background", assetUrl(filename), 0, 0, 1000, 562.5));
}


function addHeader(slide, label = "页面标题") {
  slide.elements.push(
    text(slide, "title", label, 72, 46, 720, 72, {
      fontSize: 34,
      color: COLORS.burgundy,
      bold: true,
      textType: "title",
      minimumFontSize: 30,
      lineHeight: 1.15,
    }),
    line(slide, "header-rule", 72, 124, 160, { color: COLORS.dustyRose, width: 2, lock: true }),
  );
}


function cover(id = "cover-scroll-blossom", minimal = false) {
  const slide = createSlide(id, "cover", {
    variantMode: "deterministic",
    titleFitLimits: { maxWide: 20, maxAscii: 42, singleWide: 10, singleAscii: 22 },
  });
  addBackground(slide, minimal ? ASSETS.content : ASSETS.cover);
  if (minimal) {
    slide.elements.push(image(slide, "petals", assetUrl(ASSETS.petals), 590, 0, 410, 310, {
      fixedRatio: true,
    }));
  } else {
    slide.elements.push(image(slide, "scroll", assetUrl(ASSETS.scroll), -40, 330, 450, 270, {
      fixedRatio: true,
    }));
  }
  slide.elements.push(
    text(slide, "title", "桃夭墨韵商务汇报", minimal ? 160 : 320, 150, minimal ? 680 : 600, 145, {
      fontSize: 54,
      color: COLORS.burgundy,
      bold: true,
      textType: "title",
      minimumFontSize: 48,
      align: "center",
      lineHeight: 1.08,
    }),
    text(slide, "content", "以清晰结构承载东方意境", minimal ? 240 : 440, 315, minimal ? 520 : 420, 68, {
      fontSize: 20,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 16,
      align: "center",
    }),
  );
  return slide;
}


function contents(count) {
  const slide = createSlide(`contents-${count}`, "contents");
  addBackground(slide, ASSETS.content);
  slide.elements.push(
    image(slide, "title-frame", assetUrl(ASSETS.titleFrame), 62, 42, 270, 72, { fixedRatio: true }),
    text(slide, "static-title", "目录", 98, 57, 195, 42, {
      fontSize: 28,
      color: COLORS.burgundy,
      bold: true,
      align: "center",
    }),
  );
  const columns = 2;
  const rows = Math.ceil(count / columns);
  const rowHeight = rows >= 5 ? 68 : rows === 4 ? 78 : 96;
  const top = rows >= 5 ? 145 : 160;
  for (let index = 0; index < count; index += 1) {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const left = 92 + column * 440;
    const itemTop = top + row * rowHeight;
    const groupId = `${slide.id}-item-${index + 1}`;
    slide.elements.push(
      text(slide, "item-number", String(index + 1).padStart(2, "0"), left, itemTop, 54, 42, {
        fontSize: 24,
        color: COLORS.blossom,
        bold: true,
        textType: "itemNumber",
        minimumFontSize: 20,
        groupId,
        lineHeight: 1.05,
      }),
      text(slide, "item", `目录项目${index + 1}`, left + 68, itemTop + 1, 315, 44, {
        fontSize: rows >= 5 ? 17 : 19,
        color: COLORS.ink,
        textType: "item",
        minimumFontSize: 16,
        groupId,
      }),
      line(slide, "item-rule", left + 68, itemTop + 47, 300, {
        color: COLORS.paleRose,
        width: 1,
        groupId,
      }),
    );
  }
  return slide;
}


function transition(id, circle = false) {
  const slide = createSlide(id, "transition", { variantMode: "deterministic" });
  addBackground(slide, ASSETS.section);
  if (circle) {
    slide.elements.push(image(slide, "ink-circle", assetUrl(ASSETS.circle), 75, 130, 280, 280, {
      fixedRatio: true,
    }));
  } else {
    slide.elements.push(image(slide, "petals", assetUrl(ASSETS.petals), 625, 15, 350, 260, {
      fixedRatio: true,
    }));
  }
  slide.elements.push(
    text(slide, "part-number", "01", circle ? 125 : 90, circle ? 205 : 165, circle ? 180 : 150, 115, {
      fontSize: circle ? 60 : 76,
      color: COLORS.burgundy,
      bold: true,
      textType: "partNumber",
      minimumFontSize: circle ? 52 : 64,
      align: "center",
      lineHeight: 1,
    }),
    // 墨圈变体为 11 字生产标题保留单行容量，并与左侧墨圈保持 25px 间距。
    text(slide, "title", "章节标题", circle ? 380 : 285, 190, circle ? 540 : 560, 90, {
      fontSize: 46,
      color: COLORS.ink,
      bold: true,
      textType: "title",
      minimumFontSize: 42,
      lineHeight: 1.1,
    }),
    text(slide, "content", "章节说明文字", circle ? 414 : 290, 300, circle ? 430 : 500, 72, {
      fontSize: 18,
      color: COLORS.body,
      textType: "content",
      minimumFontSize: 16,
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
  const positions = {
    2: { left: 100, gap: 440, width: 350 },
    3: { left: 65, gap: 305, width: 255 },
    4: { left: 50, gap: 230, width: 195 },
  }[count];
  for (let index = 0; index < count; index += 1) {
    const left = positions.left + index * positions.gap;
    const groupId = `${slide.id}-item-${index + 1}`;
    slide.elements.push(
      text(slide, "item-number", String(index + 1).padStart(2, "0"), left, 160, 62, 46, {
        fontSize: 28,
        color: COLORS.blossom,
        bold: true,
        textType: "itemNumber",
        minimumFontSize: 24,
        groupId,
        lineHeight: 1.05,
      }),
      text(slide, "item-title", `内容标题${index + 1}`, left, 214, positions.width, 54, {
        fontSize: count >= 3 ? 18 : 22,
        color: COLORS.ink,
        bold: true,
        textType: "itemTitle",
        minimumFontSize: count >= 3 ? 16 : 20,
        groupId,
        // 四项页允许 10 个中文字；紧凑行高让两行标题在 16px 最小字号下完整进入 54px 槽位。
        lineHeight: count === 4 ? 1.05 : 1.35,
      }),
      line(slide, "item-rule", left, 275, positions.width, {
        color: COLORS.dustyRose,
        width: 2,
        groupId,
      }),
      text(slide, "item", "正文信息完整展示，并保持清晰的阅读层级。", left, 296, positions.width, 180, {
        fontSize: 16,
        color: COLORS.body,
        textType: "item",
        minimumFontSize: 14,
        groupId,
      }),
    );
  }
  return slide;
}


function contentStatement() {
  const slide = createSlide("content-statement-1", "content", {
    allowedItemCounts: [1],
  });
  addBackground(slide, ASSETS.content);
  addHeader(slide, "核心结论");
  const groupId = `${slide.id}-item-1`;
  slide.elements.push(
    image(slide, "brush-band", assetUrl(ASSETS.brush), 145, 185, 710, 135, { fixedRatio: true }),
    text(slide, "item-title", "核心结论标题", 210, 218, 580, 68, {
      fontSize: 32,
      color: COLORS.white,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 26,
      align: "center",
      groupId,
    }),
    text(slide, "item", "用一段完整说明解释结论，并保留必要的上下文。", 180, 355, 640, 100, {
      fontSize: 20,
      color: COLORS.body,
      textType: "item",
      minimumFontSize: 16,
      align: "center",
      groupId,
    }),
  );
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
    image(slide, "content-image", assetUrl(ASSETS.cover), 75, 165, 420, 315, {
      imageType: "content",
      lock: false,
      groupId,
      strictImageCount: true,
      requireSourceDimensions: true,
      clip: { shape: "rect", range: [[0, 0], [100, 100]] },
    }),
    text(slide, "item-title", "图文标题", 555, 210, 340, 64, {
      fontSize: 24,
      color: COLORS.ink,
      bold: true,
      textType: "itemTitle",
      minimumFontSize: 20,
      groupId,
    }),
    text(slide, "item", "正文围绕业务图片展开，并保持内容与图片的语义对应。", 555, 300, 340, 155, {
      fontSize: 17,
      color: COLORS.body,
      textType: "item",
      minimumFontSize: 15,
      groupId,
    }),
  );
  return slide;
}


function metrics() {
  const slide = createSlide("content-metrics-4", "content", {
    allowedItemCounts: [4],
    layoutKind: "metrics",
    metricValueField: "value",
  });
  addBackground(slide, ASSETS.content);
  addHeader(slide, "关键业务指标");
  slide.elements.push(image(slide, "brush-band", assetUrl(ASSETS.brush), 120, 145, 760, 80, {
    fixedRatio: true,
  }));
  for (let index = 0; index < 4; index += 1) {
    const left = 62 + index * 230;
    const groupId = `${slide.id}-metric-${index + 1}`;
    slide.elements.push(
      shape(slide, "metric-circle", left + 25, 205, 135, 135, {
        geometry: "ellipse",
        fill: "#FFF9F5",
        outlineColor: COLORS.dustyRose,
        outlineWidth: 3,
        groupId,
      }),
      text(slide, "metric-value", `${(index + 1) * 20}%`, left + 37, 248, 112, 50, {
        fontSize: 28,
        color: COLORS.burgundy,
        bold: true,
        textType: "itemNumber",
        minimumFontSize: 24,
        align: "center",
        groupId,
        lineHeight: 1.05,
      }),
      text(slide, "metric-title", `指标${index + 1}`, left, 365, 185, 48, {
        fontSize: 18,
        color: COLORS.ink,
        bold: true,
        textType: "itemTitle",
        minimumFontSize: 16,
        align: "center",
        groupId,
      }),
      text(slide, "metric-body", "指标说明", left, 420, 185, 62, {
        fontSize: 15,
        color: COLORS.body,
        textType: "item",
        minimumFontSize: 13,
        align: "center",
        groupId,
      }),
    );
  }
  return slide;
}


function end(id = "end-blossom-mountain", action = false) {
  const slide = createSlide(id, "end", {
    preserveEndItemBody: action,
  });
  addBackground(slide, ASSETS.end);
  slide.elements.push(
    text(slide, "title", action ? "下一步行动" : "感谢观看", 105, action ? 78 : 170, 600, 110, {
      fontSize: action ? 42 : 54,
      color: COLORS.burgundy,
      bold: true,
      textType: "title",
      minimumFontSize: action ? 36 : 48,
      lineHeight: 1.1,
    }),
    text(slide, "content", action ? "请按计划推进并持续复盘" : "期待与您继续交流", 110, action ? 165 : 300, 520, 70, {
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
        text(slide, "item-number", String(index + 1).padStart(2, "0"), 115, 255 + index * 78, 54, 44, {
          fontSize: 22,
          color: COLORS.blossom,
          bold: true,
          minimumFontSize: 18,
          groupId,
        }),
        text(slide, "item", `行动项目${index + 1}`, 180, 252 + index * 78, 420, 56, {
          fontSize: 17,
          color: COLORS.ink,
          textType: "item",
          minimumFontSize: 15,
          groupId,
        }),
      );
    }
  }
  return slide;
}


function buildRelease(stage) {
  const production = [
    cover(),
    cover("cover-blossom-minimal", true),
    ...[2, 3, 4, 5, 6, 10].map(contents),
    transition("transition-petal-number"),
    transition("transition-ink-circle", true),
    contentStatement(),
    contentImage(),
    contentText(2),
    contentText(3),
    contentText(4),
    metrics(),
    end(),
    end("end-action", true),
  ];
  const byId = new Map(production.map((slide) => [slide.id, slide]));
  const mvpIds = [
    "cover-scroll-blossom",
    "contents-2",
    "contents-3",
    "contents-4",
    "contents-5",
    "contents-6",
    "contents-10",
    "transition-petal-number",
    "content-text-2",
    "content-text-3",
    "content-text-4",
    "end-blossom-mountain",
  ];
  const sampleIds = [
    "cover-scroll-blossom",
    "contents-4",
    "transition-petal-number",
    "content-text-4",
    "content-metrics-4",
    "content-image-1",
    "end-blossom-mountain",
  ];
  const selectedIds = stage === "sample" ? sampleIds : stage === "mvp" ? mvpIds : production.map((slide) => slide.id);
  return {
    id: "template_22",
    title: "桃夭墨韵商务汇报",
    width: 1000,
    height: 562.5,
    supportsLosslessContentPagination: true,
    paginationGrowthPolicy: { factor: 1.75, slack: 5 },
    theme: {
      themeColors: [COLORS.burgundy, COLORS.blossom, COLORS.ink],
      fontColor: COLORS.body,
      fontName: "微软雅黑",
      backgroundColor: COLORS.ivory,
    },
    metadata: {
      aspectRatio: "16:9",
      buildStage: stage,
      sourceReference: "中国风格(5).pptx",
      sourceReferenceSha256: REFERENCE.sha256,
      rightsPolicy: "reference-media-excluded",
      sourceFidelity: "peach-blossom-xuan-paper-scroll-ink-language",
      probeSlideIds: ["cover-scroll-blossom", "content-image-1", "probe-image-circle-1"],
      sampleSlideIds: sampleIds,
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


function build(stage) {
  return stage === "probe" ? buildProbe() : buildRelease(stage);
}


function parseArgs(argv) {
  const stageIndex = argv.indexOf("--stage");
  const stage = stageIndex >= 0 ? argv[stageIndex + 1] : "production";
  const output = argv.find(
    (value, index) => index !== stageIndex && index !== stageIndex + 1 && value.endsWith(".json"),
  ) || path.join(TEMPLATE_DIR, "template_22.json");
  if (!["probe", "sample", "mvp", "production"].includes(stage)) {
    throw new Error("--stage 必须是 probe、sample、mvp 或 production");
  }
  return { stage, output: path.resolve(output) };
}


const { stage, output } = parseArgs(process.argv.slice(2));
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, `${JSON.stringify(build(stage), null, 2)}\n`, "utf8");
process.stdout.write(`${output}\n`);

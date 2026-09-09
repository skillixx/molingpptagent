#!/usr/bin/env node

/**
 * 使用前端同款 pptxtojson 解析 template_19 导出文件，生成可复核的往返摘要。
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { parse } from "../frontend/node_modules/pptxtojson/dist/index.js";


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = path.resolve(SCRIPT_DIR, "..");
const PROFILE_CONTRACTS = {
  probe: {
    expectedSlideCount: 3,
    minimumElementCount: 30,
    minimumImageCount: 6,
    requireEditedTitle: false,
  },
  "probe-edited": {
    expectedSlideCount: 3,
    minimumElementCount: 30,
    minimumImageCount: 6,
    requireEditedTitle: true,
  },
  production: {
    expectedSlideCount: 18,
    minimumElementCount: 200,
    minimumImageCount: 18,
    requireEditedTitle: true,
  },
};


function flattenElements(elements) {
  const flattened = [];
  for (const element of elements || []) {
    flattened.push(element);
    if (Array.isArray(element.elements)) flattened.push(...flattenElements(element.elements));
  }
  return flattened;
}


function stripHtml(value) {
  return String(value || "")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replaceAll("&nbsp;", " ")
    .replaceAll("&amp;", "&")
    .trim();
}


function parseArgs(argv) {
  let profile = "production";
  const positional = [];
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--profile") {
      profile = argv[index + 1] || "";
      index += 1;
    }
    else positional.push(argv[index]);
  }
  if (!Object.hasOwn(PROFILE_CONTRACTS, profile)) {
    throw new Error("--profile 只能是 probe、probe-edited 或 production");
  }
  if (positional.length < 2) {
    throw new Error("用法: node utils/verify_template_19_pptx_roundtrip.mjs [--profile probe|probe-edited|production] <输入PPTX> <输出JSON>");
  }
  return {
    profile,
    input: path.resolve(REPOSITORY_ROOT, positional[0]),
    output: path.resolve(REPOSITORY_ROOT, positional[1]),
  };
}


function portableInputPath(input) {
  const relative = path.relative(REPOSITORY_ROOT, input);
  if (relative && !relative.startsWith("..") && !path.isAbsolute(relative)) {
    return relative.split(path.sep).join("/");
  }
  return path.basename(input);
}


async function main() {
  const { profile, input, output } = parseArgs(process.argv.slice(2));
  const contract = PROFILE_CONTRACTS[profile];
  const bytes = await fs.readFile(input);
  const arrayBuffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const parsed = await parse(arrayBuffer);
  const slides = parsed.slides || [];
  const perSlide = slides.map((slide, index) => {
    const elements = flattenElements([...(slide.elements || []), ...(slide.layoutElements || [])]);
    const text = elements
      .filter(element => element.type === "text" || element.type === "shape")
      .map(element => stripHtml(element.content))
      .filter(Boolean);
    const images = elements
      .filter(element => element.type === "image")
      .map(element => ({
        width: element.width,
        height: element.height,
        geom: element.geom || null,
        hasCrop: Boolean(element.rect),
      }));
    return {
      slide: index + 1,
      elementCount: elements.length,
      text,
      imageCount: images.length,
      images,
    };
  });
  const totalElements = perSlide.reduce((sum, slide) => sum + slide.elementCount, 0);
  const totalImages = perSlide.reduce((sum, slide) => sum + slide.imageCount, 0);
  const containsEditedTitle = perSlide.some(slide => slide.text.some(value => value.includes("编辑验收")));
  const containsCroppedImage = perSlide.some(slide => slide.images.some(image => image.hasCrop));
  const failures = [];
  if (slides.length !== contract.expectedSlideCount) failures.push("SLIDE_COUNT_MISMATCH");
  if (perSlide.some(slide => slide.elementCount === 0)) failures.push("EMPTY_SLIDE");
  if (totalElements < contract.minimumElementCount) failures.push("ELEMENT_INVENTORY_TOO_SMALL");
  if (totalImages < contract.minimumImageCount) failures.push("IMAGE_INVENTORY_TOO_SMALL");
  if (contract.requireEditedTitle && !containsEditedTitle) failures.push("EDITED_TITLE_MISSING");
  if (!containsCroppedImage) failures.push("CROPPED_IMAGE_MISSING");
  const summary = {
    schemaVersion: 1,
    profile,
    contract,
    input: portableInputPath(input),
    bytes: bytes.length,
    size: parsed.size,
    slideCount: slides.length,
    totalElements,
    totalImages,
    containsEditedTitle,
    containsCroppedImage,
    failures,
    perSlide,
    status: failures.length === 0 ? "PASS" : "FAIL",
  };
  await fs.mkdir(path.dirname(output), { recursive: true });
  await fs.writeFile(output, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(summary)}\n`);
  if (failures.length > 0) process.exitCode = 1;
}


main().catch(error => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exit(1);
});

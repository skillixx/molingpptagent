#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const JSZip = require("jszip");


function decodeXml(value) {
  return value
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'")
    .replaceAll("&amp;", "&");
}


function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex").toUpperCase();
}


async function inspectPptx(filename) {
  const bytes = fs.readFileSync(filename);
  const archive = await JSZip.loadAsync(bytes);
  const slideNames = Object.keys(archive.files)
    .filter(name => /^ppt\/slides\/slide\d+\.xml$/u.test(name))
    .sort((left, right) => Number(left.match(/\d+/u)[0]) - Number(right.match(/\d+/u)[0]));
  const slides = [];
  const fonts = new Set();
  for (const name of slideNames) {
    const xml = await archive.file(name).async("string");
    const texts = [...xml.matchAll(/<a:t(?:\s[^>]*)?>([\s\S]*?)<\/a:t>/gu)]
      .map(match => decodeXml(match[1]));
    for (const match of xml.matchAll(/typeface="([^"]+)"/gu)) fonts.add(decodeXml(match[1]));
    slides.push({
      name,
      texts,
      text: texts.join(" | "),
      textJoined: texts.join(""),
      pictureCount: (xml.match(/<p:pic\b/gu) || []).length,
      editableShapeCount: (xml.match(/<p:sp\b/gu) || []).length,
      groupCount: (xml.match(/<p:grpSp\b/gu) || []).length,
    });
  }
  return {
    filename: path.basename(filename),
    bytes: bytes.length,
    sha256: sha256(bytes),
    slideCount: slides.length,
    mediaCount: Object.keys(archive.files).filter(name => name.startsWith("ppt/media/") && !name.endsWith("/")).length,
    fonts: [...fonts].sort(),
    macroFree: !Object.keys(archive.files).some(name => /vbaProject\.bin$/iu.test(name)),
    slides,
  };
}


function verifyExpectedTexts(document, expectedTextBySlide) {
  if (document.slideCount !== expectedTextBySlide.length) {
    throw new Error(`${document.filename} 页数 ${document.slideCount} 与预期 ${expectedTextBySlide.length} 不一致`);
  }
  const missing = [];
  const orderFailures = [];
  expectedTextBySlide.forEach((expectedTexts, index) => {
    const actual = document.slides[index];
    const positions = expectedTexts.map(value => {
      const separated = actual.text.indexOf(value);
      return separated >= 0 ? separated : actual.textJoined.indexOf(value);
    });
    expectedTexts.forEach((value, textIndex) => {
      if (positions[textIndex] < 0) missing.push(`slide-${index + 1}:${value}`);
    });
    if (positions.some((value, textIndex) => textIndex > 0 && value < positions[textIndex - 1])) {
      orderFailures.push(index + 1);
    }
  });
  if (missing.length) throw new Error(`${document.filename} 缺少文本：${missing.join(", ")}`);
  if (orderFailures.length) throw new Error(`${document.filename} 文本顺序变化：${orderFailures.join(", ")}`);
  return { missing, orderFailures };
}


async function main() {
  const [sourceArg, savedArg, outputArg, browserSummaryArg] = process.argv.slice(2);
  if (!sourceArg || !savedArg || !outputArg || !browserSummaryArg) {
    throw new Error("用法: node utils/verify_template_23_pptx_roundtrip.mjs <导出PPTX> <PowerPoint保存副本> <输出JSON> <浏览器摘要JSON>");
  }
  const sourcePath = path.resolve(sourceArg);
  const savedPath = path.resolve(savedArg);
  const outputPath = path.resolve(outputArg);
  const browserSummary = JSON.parse(fs.readFileSync(path.resolve(browserSummaryArg), "utf8"));
  const expectedTextBySlide = browserSummary.expectedTextBySlide;
  if (!Array.isArray(expectedTextBySlide) || expectedTextBySlide.length === 0) {
    throw new Error("浏览器摘要缺少 expectedTextBySlide");
  }

  const source = await inspectPptx(sourcePath);
  const saved = await inspectPptx(savedPath);
  verifyExpectedTexts(source, expectedTextBySlide);
  verifyExpectedTexts(saved, expectedTextBySlide);
  if (source.slideCount !== saved.slideCount) throw new Error("PowerPoint 保存前后页数变化");
  if (source.slides.some((slide, index) => slide.pictureCount !== saved.slides[index].pictureCount)) {
    throw new Error("PowerPoint 保存前后图片数量变化");
  }
  if (source.slides.some((slide, index) => slide.editableShapeCount !== saved.slides[index].editableShapeCount)) {
    throw new Error("PowerPoint 保存前后可编辑形状数量变化");
  }

  const summary = {
    schemaVersion: 1,
    templateId: "template_23",
    status: "PASS",
    powerPointOpenedAndSaved: true,
    source,
    saved,
    checks: {
      slideCountRetained: true,
      allExpectedTextsRetained: true,
      textOrderRetained: true,
      pictureCountRetainedBySlide: true,
      editableShapeCountRetainedBySlide: true,
      macroFree: source.macroFree && saved.macroFree,
    },
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({
    status: summary.status,
    sourceSlides: source.slideCount,
    savedSlides: saved.slideCount,
    sourceMedia: source.mediaCount,
    savedMedia: saved.mediaCount,
    sourceSha256: source.sha256,
    savedSha256: saved.sha256,
  })}\n`);
}


await main();

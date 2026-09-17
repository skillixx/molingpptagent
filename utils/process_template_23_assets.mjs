#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";


const require = createRequire(import.meta.url);
const sharp = require("sharp");


const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, "..");
const ORIGINALS = path.join(ROOT, "doc", "assets", "template_23_qa", "originals");
const SAMPLES = path.join(ROOT, "doc", "assets", "template_23_qa", "samples");
const PUBLISHED = path.join(ROOT, "backend", "main_api", "template");
const SUMMARY = path.join(ROOT, "doc", "assets", "template_23_qa", "asset-summary.json");

const CONTRACT = [
  { filename: "template_23_asset_bg_cover_v1.jpg", width: 1920, height: 1080, mode: "RGB", maxBytes: 450000 },
  { filename: "template_23_asset_bg_content_v1.jpg", width: 1920, height: 1080, mode: "RGB", maxBytes: 300000 },
  { filename: "template_23_asset_bg_section_v1.jpg", width: 1920, height: 1080, mode: "RGB", maxBytes: 380000 },
  { filename: "template_23_asset_bg_end_v1.jpg", width: 1920, height: 1080, mode: "RGB", maxBytes: 420000 },
  { filename: "template_23_asset_particle_field_v1.png", width: 1600, height: 900, mode: "RGBA", maxBytes: 800000 },
  { filename: "template_23_asset_horizon_glow_v1.png", width: 1800, height: 600, mode: "RGBA", maxBytes: 600000 },
  { filename: "template_23_asset_title_flare_v1.png", width: 1800, height: 180, mode: "RGBA", maxBytes: 350000 },
  { filename: "template_23_asset_image_halo_v1.png", width: 1200, height: 900, mode: "RGBA", maxBytes: 700000 },
  { filename: "template_23_asset_grid_arc_v1.png", width: 1600, height: 900, mode: "RGBA", maxBytes: 650000 },
];


function originalPath(filename) {
  return path.join(ORIGINALS, filename.replace(/\.(jpg|png)$/u, "_original.png"));
}


function sha256(filename) {
  return crypto.createHash("sha256").update(fs.readFileSync(filename)).digest("hex").toUpperCase();
}


async function encodeJpeg(source, destination, spec) {
  // 从高质量开始逐级收敛到体积合同，避免直接用低质量破坏星点和细光线。
  for (const quality of [92, 88, 84, 80, 76, 72, 68, 64, 60, 56, 52]) {
    await sharp(source)
      .resize(spec.width, spec.height, { fit: "cover", position: "centre" })
      .flatten({ background: "#020814" })
      .jpeg({ quality, chromaSubsampling: "4:2:0", mozjpeg: true })
      .toFile(destination);
    if (fs.statSync(destination).size <= spec.maxBytes) return quality;
  }
  throw new Error(`${spec.filename} 无法在允许质量范围内满足体积上限`);
}


async function encodePng(source, destination, spec) {
  // contain 只做机械归一化，保留生成素材的真实透明像素与完整构图。
  const normalized = await sharp(source)
    .ensureAlpha()
    .resize(spec.width, spec.height, {
      fit: "contain",
      position: "centre",
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    })
    .raw()
    .toBuffer({ resolveWithObject: true });
  for (const colors of [0, 256, 128, 64]) {
    let input = sharp(normalized.data, { raw: normalized.info });
    if (colors > 0) {
      // 先量化颜色，再展开回真彩 RGBA；既满足模式合同，也降低星尘渐变的熵。
      const quantized = await input.png({ palette: true, colors, dither: 0.6 }).toBuffer();
      input = sharp(quantized).ensureAlpha();
    }
    await input.png({ compressionLevel: 9, adaptiveFiltering: true, palette: false }).toFile(destination);
    if (fs.statSync(destination).size <= spec.maxBytes) return colors || null;
  }
  throw new Error(`${spec.filename} 超出体积上限 ${spec.maxBytes}`);
}


async function build() {
  fs.mkdirSync(SAMPLES, { recursive: true });
  fs.mkdirSync(PUBLISHED, { recursive: true });
  const assets = [];
  for (const spec of CONTRACT) {
    const source = originalPath(spec.filename);
    const destination = path.join(PUBLISHED, spec.filename);
    const quality = spec.mode === "RGB"
      ? await encodeJpeg(source, destination, spec)
      : await encodePng(source, destination, spec);
    fs.copyFileSync(destination, path.join(SAMPLES, spec.filename));
    const metadata = await sharp(destination).metadata();
    const stats = await sharp(destination).stats();
    const alpha = stats.channels.length >= 4
      ? [stats.channels[3].min, stats.channels[3].max]
      : null;
    assets.push({
      filename: spec.filename,
      source: path.relative(ROOT, source).replaceAll("\\", "/"),
      size: [metadata.width, metadata.height],
      mode: spec.mode,
      bytes: fs.statSync(destination).size,
      maxBytes: spec.maxBytes,
      jpegQuality: spec.mode === "RGB" ? quality : null,
      pngQuantizedColors: spec.mode === "RGBA" ? quality : null,
      alphaRange: alpha,
      sha256: sha256(destination),
    });
  }

  const selector = path.join(PUBLISHED, "template_23.jpg");
  await sharp(path.join(PUBLISHED, "template_23_asset_bg_cover_v1.jpg"))
    .resize(960, 540, { fit: "cover" })
    .jpeg({ quality: 88, chromaSubsampling: "4:2:0", mozjpeg: true })
    .toFile(selector);
  if (fs.statSync(selector).size > 150000) {
    await sharp(path.join(PUBLISHED, "template_23_asset_bg_cover_v1.jpg"))
      .resize(960, 540, { fit: "cover" })
      .jpeg({ quality: 78, chromaSubsampling: "4:2:0", mozjpeg: true })
      .toFile(selector);
  }

  const output = {
    schemaVersion: 1,
    templateId: "template_23",
    status: "PASS",
    generationTool: "built-in image generation",
    requestedGenerator: "GPT2 图片模板",
    actualModel: "工具未暴露",
    assets,
    selectorCover: {
      filename: "template_23.jpg",
      size: [960, 540],
      mode: "RGB",
      bytes: fs.statSync(selector).size,
      maxBytes: 150000,
      sha256: sha256(selector),
    },
  };
  fs.writeFileSync(SUMMARY, `${JSON.stringify(output, null, 2)}\n`, "utf8");
  process.stdout.write(`${SUMMARY}\n`);
}


await build();

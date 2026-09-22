#!/usr/bin/env node
/** 机械转换生成素材的尺寸和文件格式，保留原稿及透明通道，不重绘画面。 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const sharp = require(process.env.SHARP_PACKAGE_PATH || 'sharp');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const qa = path.join(root, 'doc/assets/template_26_qa');
const targets = {
  A1: ['bg_cover_v1.jpg', 2560, 1440], A2: ['bg_content_v1.jpg', 2560, 1440],
  A3: ['bg_section_v1.jpg', 2560, 1440], A4: ['bg_end_v1.jpg', 2560, 1440],
  A5: ['lock_v1.png', 1254, 1254], A6: ['circuit_upper_right_v1.png', 1600, 1600],
  A7: ['circuit_lower_left_v1.png', 1600, 1600], A8: ['network_sphere_v1.png', 1254, 1254],
};
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const assets = [];
for (const [id, [suffix, width, height]] of Object.entries(targets)) {
  const record = JSON.parse(fs.readFileSync(path.join(qa, 'asset-prompts', `${id}.json`), 'utf8'));
  const match = record.outputHint.match(/as (C:.*?\.png) by default/);
  if (!match) throw new Error(`${id} 缺少生成工具原始文件路径`);
  const source = match[1], input = fs.readFileSync(source), original = await sharp(input).metadata();
  const transparent = suffix.endsWith('.png');
  if (transparent && !original.hasAlpha) throw new Error(`${id} 缺少真实透明通道`);
  const filename = `template_26_asset_${suffix}`, output = path.join(root, 'backend/main_api/template', filename);
  // 背景只做等比微裁切及尺寸规范化；透明素材为同一比例缩放，保留全部轮廓。
  const pipeline = sharp(input).resize(width, height, { fit: 'cover', position: 'centre' });
  const bytes = await (transparent ? pipeline.png() : pipeline.jpeg({ quality: 94, chromaSubsampling: '4:4:4' })).toBuffer();
  if (transparent) {
    const alpha = await sharp(bytes).extractChannel('alpha').stats();
    if (alpha.channels[0].min !== 0 || alpha.channels[0].max === 0) throw new Error(`${id} 透明区域或可见内容无效`);
  }
  fs.writeFileSync(output, bytes);
  assets.push({ id, filename, source, sourceSha256: digest(input), sourceDimensions: [original.width, original.height],
    dimensions: [width, height], sha256: digest(bytes), hasAlpha: transparent,
    processing: '仅尺寸与格式规范化；未生成或重绘像素内容', visualInspection: '生成结果已查看；实际页面检查待完成',
    promptFile: `asset-prompts/${id}.json`, actualModel: '工具未暴露', tool: 'image_gen.imagegen' });
}
fs.writeFileSync(path.join(qa, 'asset-generation.json'), JSON.stringify({ templateId: 'template_26', requestedMethod: 'GPT2 图片模板', assets }, null, 2) + '\n');
console.log(JSON.stringify({ assets: assets.length, backgrounds: assets.filter(a => !a.hasAlpha).length, transparent: assets.filter(a => a.hasAlpha).length }));

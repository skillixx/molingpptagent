#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";


function parseArgs(argv) {
  if (argv.length < 2) {
    throw new Error("用法: node utils/render_pptist_template_preview.mjs <模板JSON> <输出HTML>");
  }
  return { input: path.resolve(argv[0]), output: path.resolve(argv[1]) };
}


function dataUrlForAsset(source, templateDir) {
  if (typeof source !== "string" || !source.startsWith("/api/data/")) return source;
  const filename = source.rsplit?.("/", 1)?.at?.(-1) || source.split("/").at(-1);
  const filePath = path.join(templateDir, filename);
  const extension = path.extname(filename).toLowerCase();
  const mime = extension === ".jpg" || extension === ".jpeg" ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${fs.readFileSync(filePath).toString("base64")}`;
}


function embedAssets(template, templateDir) {
  for (const slide of template.slides || []) {
    for (const element of slide.elements || []) {
      if (element.type === "image") element.src = dataUrlForAsset(element.src, templateDir);
    }
  }
  return template;
}


function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}


function buildHtml(template) {
  // 任何模板字段都可能包含 HTML；统一转义“<”可阻断 script 结束标签穿透。
  const serialized = JSON.stringify(template).replaceAll("<", "\\u003c");
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(template.title)} 预览</title>
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; background: #dfe7ee; font-family: "Microsoft YaHei", Arial, sans-serif; }
    #single { width: 1000px; height: 562.5px; overflow: hidden; background: #04131f; }
    #grid { display: grid; grid-template-columns: repeat(3, 320px); gap: 26px 22px; padding: 24px; }
    .preview-item { width: 320px; }
    .preview-label { margin: 0 0 6px; color: #263746; font-size: 13px; font-weight: 700; }
    .preview-viewport { position: relative; width: 320px; height: 180px; overflow: hidden; background: #04131f; box-shadow: 0 3px 12px rgba(18, 37, 52, .2); }
    .slide { position: relative; width: 1000px; height: 562.5px; overflow: hidden; transform-origin: 0 0; }
    .preview-viewport > .slide { transform: scale(.32); }
    .element { position: absolute; transform-origin: center center; }
    .element-text { overflow: hidden; }
    .element-text p { margin: 0; }
    .element-image img { width: 100%; height: 100%; display: block; object-fit: cover; }
    .element-svg svg { width: 100%; height: 100%; display: block; overflow: visible; }
  </style>
</head>
<body>
  <div id="single" hidden></div>
  <main id="grid"></main>
  <script>
    const template = ${serialized};

    const SAFE_TEXT_TAGS = new Set(['P', 'BR', 'SPAN', 'STRONG', 'B', 'EM', 'I', 'U', 'UL', 'OL', 'LI']);
    const SAFE_TEXT_STYLES = [
      'color', 'font-size', 'font-family', 'font-weight', 'font-style',
      'line-height', 'text-align', 'text-decoration',
    ];

    function appendSafeText(target, source) {
      const parsed = new DOMParser().parseFromString(String(source || ''), 'text/html');

      function cloneSafe(node) {
        if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.textContent || '');
        if (node.nodeType !== Node.ELEMENT_NODE) return document.createDocumentFragment();

        const fragment = document.createDocumentFragment();
        if (!SAFE_TEXT_TAGS.has(node.tagName)) {
          for (const child of node.childNodes) fragment.appendChild(cloneSafe(child));
          return fragment;
        }

        const safe = document.createElement(node.tagName.toLowerCase());
        for (const property of SAFE_TEXT_STYLES) {
          const value = node.style.getPropertyValue(property);
          if (value && !/url\\s*\\(/i.test(value)) safe.style.setProperty(property, value);
        }
        for (const child of node.childNodes) safe.appendChild(cloneSafe(child));
        return safe;
      }

      for (const child of parsed.body.childNodes) target.appendChild(cloneSafe(child));
    }

    function safeColor(value, fallback = 'transparent') {
      const candidate = String(value || '');
      return !/url\\s*\\(/i.test(candidate) && CSS.supports('color', candidate)
        ? candidate
        : fallback;
    }

    function makeSvg(element) {
      const holder = document.createElement("div");
      holder.className = "element element-svg";
      const viewBox = element.viewBox || [200, 200];
      const outline = element.outline || {};
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 ' + Number(viewBox[0] || 200) + ' ' + Number(viewBox[1] || 200));
      svg.setAttribute('preserveAspectRatio', 'none');
      let graphic;
      if (element.pathFormula === "roundRect") {
        graphic = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        graphic.setAttribute('x', '0');
        graphic.setAttribute('y', '0');
        graphic.setAttribute('width', Number(viewBox[0] || 200));
        graphic.setAttribute('height', Number(viewBox[1] || 200));
        graphic.setAttribute('rx', '16');
        graphic.setAttribute('ry', '16');
      } else {
        graphic = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        graphic.setAttribute('d', String(element.path || ''));
      }
      graphic.setAttribute('fill', safeColor(element.fill));
      graphic.setAttribute('stroke', safeColor(outline.color));
      graphic.setAttribute('stroke-width', Number(outline.width || 0));
      svg.appendChild(graphic);
      holder.appendChild(svg);
      return holder;
    }

    function renderElement(element) {
      let node;
      if (element.type === "text") {
        node = document.createElement("div");
        node.className = "element element-text";
        appendSafeText(node, element.content);
      } else if (element.type === "image") {
        node = document.createElement("div");
        node.className = "element element-image";
        const image = document.createElement("img");
        image.src = element.src;
        image.alt = element.alt || "";
        node.appendChild(image);
      } else if (element.type === "shape") {
        node = makeSvg(element);
      } else if (element.type === "line") {
        node = document.createElement("div");
        node.className = "element element-svg";
        const length = Math.max(1, Number(element.end?.[0] || 1));
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 ' + length + ' 10');
        svg.setAttribute('preserveAspectRatio', 'none');
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', '0');
        line.setAttribute('y1', '5');
        line.setAttribute('x2', length);
        line.setAttribute('y2', '5');
        line.setAttribute('stroke', safeColor(element.color, '#fff'));
        line.setAttribute('stroke-width', Number(element.width || 1));
        svg.appendChild(line);
        node.appendChild(svg);
      } else {
        node = document.createElement("div");
        node.className = "element";
      }
      Object.assign(node.style, {
        left: (element.left || 0) + 'px',
        top: (element.top || 0) + 'px',
        width: (element.width || element.end?.[0] || 0) + 'px',
        height: (element.height || (element.type === 'line' ? 10 : 0)) + 'px',
        transform: 'rotate(' + (element.rotate || 0) + 'deg)',
      });
      return node;
    }

    function renderSlide(slide) {
      const canvas = document.createElement("section");
      canvas.className = "slide";
      canvas.dataset.slideId = slide.id;
      canvas.style.background = slide.background?.color || template.theme?.backgroundColor || '#04131f';
      for (const element of slide.elements || []) canvas.appendChild(renderElement(element));
      return canvas;
    }

    const requested = new URLSearchParams(location.search).get('slide');
    if (requested) {
      const slide = template.slides.find(candidate => candidate.id === requested);
      if (!slide) throw new Error('未知页面: ' + requested);
      const single = document.getElementById('single');
      single.hidden = false;
      single.appendChild(renderSlide(slide));
      document.getElementById('grid').hidden = true;
    } else {
      const grid = document.getElementById('grid');
      for (const slide of template.slides) {
        const item = document.createElement('section');
        item.className = 'preview-item';
        const label = document.createElement('div');
        label.className = 'preview-label';
        label.textContent = slide.id;
        const viewport = document.createElement('div');
        viewport.className = 'preview-viewport';
        viewport.appendChild(renderSlide(slide));
        item.append(label, viewport);
        grid.appendChild(item);
      }
    }
  </script>
</body>
</html>`;
}


try {
  const { input, output } = parseArgs(process.argv.slice(2));
  const template = embedAssets(
    JSON.parse(fs.readFileSync(input, "utf8")),
    path.dirname(input),
  );
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, buildHtml(template), "utf8");
  process.stdout.write(`${output}\n`);
} catch (error) {
  process.stderr.write(`${error.message || error}\n`);
  process.exit(1);
}

// 在本地编辑器中验证 template_23 四视口、编辑换图、JSON 与 PPTX 往返。
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');

const evidenceRoot = path.resolve(process.argv[2]);
const templateRoot = path.resolve(process.argv[3]);
const documentData = JSON.parse(
  fs.readFileSync(path.join(evidenceRoot, 'real-handler-document.json'), 'utf8'),
);
const viewportRoot = path.join(evidenceRoot, 'viewports');
const editorRoot = path.join(evidenceRoot, 'editor-renders');
fs.mkdirSync(viewportRoot, { recursive: true });
fs.mkdirSync(editorRoot, { recursive: true });

const viewports = [
  ['desktop', 1920, 1080],
  ['laptop', 1366, 768],
  ['tablet', 768, 1024],
  ['mobile', 390, 844],
];
const representativeSlides = [3, 6];
const replacementInputs = [
  ['landscape', 'template_23_probe_landscape.jpeg', 600, 450],
  ['portrait', 'template_23_probe_portrait.jpeg', 600, 900],
  ['square', 'template_23_probe_square.jpeg', 600, 600],
];

function templateAssetPath(urlPath) {
  const basename = path.basename(decodeURIComponent(urlPath));
  const candidate = path.join(templateRoot, basename);
  return fs.existsSync(candidate) && path.dirname(candidate) === templateRoot ? candidate : null;
}

function toDataUrl(filename) {
  const bytes = fs.readFileSync(path.join(evidenceRoot, 'probe-assets', filename));
  return `data:image/jpeg;base64,${bytes.toString('base64')}`;
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const blockedWrites = [];
  const screenshots = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await page.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.protocol === 'data:' || url.protocol === 'blob:') return route.continue();
      if (url.origin !== 'http://127.0.0.1:5778') return route.abort();
      if (request.method() !== 'GET') {
        blockedWrites.push(`${request.method()} ${url.pathname}`);
        return route.abort();
      }
      if (url.pathname === '/api/auth/me') {
        return route.fulfill({ json: { user_id: 1, app_id: 1, product_id: 1 } });
      }
      if (url.pathname.startsWith('/api/data/')) {
        const assetPath = templateAssetPath(url.pathname);
        if (!assetPath) return route.fulfill({ status: 404, body: 'missing QA asset' });
        return route.fulfill({
          contentType: assetPath.endsWith('.png') ? 'image/png' : 'image/jpeg',
          body: fs.readFileSync(assetPath),
        });
      }
      if (url.pathname.startsWith('/api/')) {
        return route.fulfill({ status: 404, json: { code: 'QA_ONLY' } });
      }
      return route.continue();
    });

    await page.goto('http://127.0.0.1:5778/editor');
    const canvas = page.locator('.viewport-wrapper').first();
    await canvas.waitFor({ state: 'visible', timeout: 60000 });
    await page.evaluate(async data => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        store.clearPresentationContext();
        store.setTitle('template23-g6-qa');
        store.setTheme(data.theme);
        store.setViewportSize(data.viewport_size);
        store.setViewportRatio(data.viewport_ratio);
        store.setSlides(data.slides);
      });
    }, documentData);

    for (const [name, width, height] of viewports) {
      await page.setViewportSize({ width, height });
      for (const index of representativeSlides) {
        await page.evaluate(async slideIndex => {
          const { useSlidesStore } = await import('/src/store/index.ts');
          document.querySelector('#app').__vue_app__.runWithContext(() => {
            useSlidesStore().updateSlideIndex(slideIndex);
          });
          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        }, index);
        await canvas.locator('img').evaluateAll(images => Promise.all(
          images.map(image => image.decode().catch(() => undefined)),
        ));
        await page.evaluate(() => document.fonts.ready);
        const screenshotPath = path.join(viewportRoot, `${name}-${index}.png`);
        if (name === 'mobile') {
          await page.locator('.mobile-thumbnails .thumbnail-item').nth(index).screenshot({ path: screenshotPath });
        } else {
          await page.screenshot({ path: screenshotPath, fullPage: false });
        }
        screenshots.push(path.relative(evidenceRoot, screenshotPath).replaceAll('\\', '/'));
      }
    }

    await page.setViewportSize({ width: 1920, height: 1080 });
    const editResult = await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        const cover = store.slides[0];
        const coverTitle = cover.elements.find(element => element.textType === 'title');
        store.updateElement({
          id: coverTitle.id,
          slideId: cover.id,
          props: { content: '蓝曜星幕编辑验收' },
        });
        const textSlide = store.slides[3];
        const body = textSlide.elements.find(element => element.textType === 'item');
        store.updateElement({
          id: body.id,
          slideId: textSlide.id,
          props: { content: '正文编辑验收：内容保持可修改并可保存。' },
        });
        return { titleEdited: true, bodyEdited: true, slideCount: store.slides.length };
      });
    });

    const replacementResults = [];
    for (const [name, filename, width, height] of replacementInputs) {
      const result = await page.evaluate(async ({ replacement, width: inputWidth, height: inputHeight }) => {
        const { useSlidesStore } = await import('/src/store/index.ts');
        return document.querySelector('#app').__vue_app__.runWithContext(() => {
          const store = useSlidesStore();
          const imageSlide = store.slides[6];
          const image = imageSlide.elements.find(element => element.imageType === 'content');
          const beforeDecorations = JSON.stringify(
            imageSlide.elements.filter(element => element.imageType === 'decoration'),
          );
          const beforeClip = JSON.stringify(image.clip);
          store.updateElement({
            id: image.id,
            slideId: imageSlide.id,
            props: { src: replacement, originalWidth: inputWidth, originalHeight: inputHeight },
          });
          const updated = imageSlide.elements.find(element => element.id === image.id);
          if (beforeDecorations !== JSON.stringify(
            imageSlide.elements.filter(element => element.imageType === 'decoration'),
          )) throw new Error('图片替换改变了固定装饰');
          if (beforeClip !== JSON.stringify(updated.clip)) throw new Error('图片替换改变了裁切协议');
          store.updateSlideIndex(6);
          return {
            decorationProtected: true,
            contentImageReplaced: updated.src === replacement,
            originalWidth: updated.originalWidth,
            originalHeight: updated.originalHeight,
          };
        });
      }, { replacement: toDataUrl(filename), width, height });
      await new Promise(resolve => setTimeout(resolve, 80));
      const screenshotPath = path.join(editorRoot, `image-after-${name}.png`);
      await canvas.screenshot({ path: screenshotPath });
      replacementResults.push({ name, filename, width, height, ...result });
    }

    const jsonDownload = page.waitForEvent('download');
    await page.evaluate(async () => {
      const { default: useExport } = await import('/src/hooks/useExport.ts');
      document.querySelector('#app').__vue_app__.runWithContext(() => useExport().exportJSON());
    });
    const jsonPath = path.join(evidenceRoot, 'editor-saved.json');
    await (await jsonDownload).saveAs(jsonPath);

    await page.reload();
    await canvas.waitFor({ state: 'visible', timeout: 60000 });
    await page.evaluate(async raw => {
      const { default: useImport } = await import('/src/hooks/useImport.ts');
      const transfer = new DataTransfer();
      transfer.items.add(new File([raw], 'template-23-saved.json', { type: 'application/json' }));
      document.querySelector('#app').__vue_app__.runWithContext(() => useImport().importJSON(transfer.files, true));
    }, fs.readFileSync(jsonPath, 'utf8'));
    await page.waitForFunction(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const serialized = JSON.stringify(useSlidesStore().slides);
        return useSlidesStore().slides.length === 8
          && serialized.includes('蓝曜星幕编辑验收')
          && serialized.includes('正文编辑验收：内容保持可修改并可保存。');
      });
    }, null, { timeout: 60000 });

    const expectedState = await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      const plainText = raw => {
        const container = document.createElement('div');
        container.innerHTML = typeof raw === 'string' ? raw : '';
        return (container.textContent || '').replace(/\s+/g, ' ').trim();
      };
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const slides = useSlidesStore().slides;
        const contentImage = slides[6].elements.find(element => element.imageType === 'content');
        return {
          textBySlide: slides.map(slide => slide.elements
            .map(element => plainText(element.content || element.text?.content || ''))
            .filter(Boolean)),
          imageCountBySlide: slides.map(slide => slide.elements.filter(element => element.type === 'image').length),
          contentImageGeometry: contentImage
            ? { left: contentImage.left, top: contentImage.top, width: contentImage.width, height: contentImage.height }
            : null,
        };
      });
    });

    const pptxDownload = page.waitForEvent('download');
    await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      const { default: useExport } = await import('/src/hooks/useExport.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        return useExport().exportPPTX(store.slides, true, true);
      });
    });
    const pptxPath = path.join(evidenceRoot, 'template_23_g6_roundtrip.pptx');
    await (await pptxDownload).saveAs(pptxPath);

    await page.evaluate(async bytes => {
      const { default: useImport } = await import('/src/hooks/useImport.ts');
      const transfer = new DataTransfer();
      transfer.items.add(new File([new Uint8Array(bytes)], 'template-23-roundtrip.pptx'));
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        useImport().importPPTXFile(transfer.files, { cover: true, fixedViewport: true });
      });
    }, [...fs.readFileSync(pptxPath)]);
    await page.waitForFunction(async expectedCount => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(
        () => useSlidesStore().slides.length === expectedCount,
      );
    }, expectedState.textBySlide.length, { timeout: 90000 });

    const roundtripState = await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      const plainText = raw => {
        const container = document.createElement('div');
        container.innerHTML = typeof raw === 'string' ? raw : '';
        return (container.textContent || '').replace(/\s+/g, ' ').trim();
      };
      return document.querySelector('#app').__vue_app__.runWithContext(() => ({
        slideCount: useSlidesStore().slides.length,
        textBySlide: useSlidesStore().slides.map(slide => slide.elements
          .map(element => plainText(element.content || element.text?.content || ''))
          .filter(Boolean)),
        imageCountBySlide: useSlidesStore().slides.map(
          slide => slide.elements.filter(element => element.type === 'image').length,
        ),
        imageGeometryBySlide: useSlidesStore().slides.map(slide => slide.elements
          .filter(element => element.type === 'image')
          .map(element => ({ left: element.left, top: element.top, width: element.width, height: element.height }))),
      }));
    });

    const missingTexts = [];
    expectedState.textBySlide.forEach((texts, slideIndex) => {
      const actual = roundtripState.textBySlide[slideIndex].join(' | ');
      texts.forEach(expected => {
        if (!actual.includes(expected)) missingTexts.push(`slide-${slideIndex + 1}:${expected}`);
      });
    });
    if (missingTexts.length) throw new Error(`PPTX 往返丢失文本: ${missingTexts.join(', ')}`);
    const orderedTextChecks = {
      1: ['项目背景', '关键成果', '业务指标', '后续计划'],
      3: ['统一视觉规范', '完善页面库存', '保留编辑能力', '建立验收证据'],
      4: ['页面库存', '页面类型', '素材库存'],
      5: ['质量项1', '质量项2', '质量项3', '质量项4', '质量项5'],
      7: ['确认候选', '进入后续交付'],
    };
    for (const [indexText, orderedTexts] of Object.entries(orderedTextChecks)) {
      const actual = roundtripState.textBySlide[Number(indexText)].join(' | ');
      const positions = orderedTexts.map(value => actual.indexOf(value));
      if (positions.some(value => value < 0)
        || positions.some((value, index) => index > 0 && value < positions[index - 1])) {
        throw new Error(`PPTX 往返改变第 ${Number(indexText) + 1} 页项目顺序`);
      }
    }
    if (expectedState.imageCountBySlide[6] !== roundtripState.imageCountBySlide[6]) {
      throw new Error('PPTX 往返没有保留图文页图片数量');
    }
    const geometryRetained = expectedState.contentImageGeometry
      && roundtripState.imageGeometryBySlide[6].some(geometry => (
        Math.abs(geometry.left - expectedState.contentImageGeometry.left) < 2
        && Math.abs(geometry.top - expectedState.contentImageGeometry.top) < 2
        && Math.abs(geometry.width - expectedState.contentImageGeometry.width) < 2
        && Math.abs(geometry.height - expectedState.contentImageGeometry.height) < 2
      ));
    if (!geometryRetained) throw new Error('PPTX 往返没有保留业务图片槽位几何位置');
    if (blockedWrites.length) throw new Error(`检测到非预期写请求: ${blockedWrites.join(', ')}`);

    const summary = {
      schemaVersion: 1,
      templateId: 'template_23',
      status: 'PASS',
      frontendUrl: 'http://127.0.0.1:5778/editor',
      sourceSlideCount: documentData.slides.length,
      viewports: viewports.map(([name, width, height]) => ({ name, width, height })),
      representativeSlideIndexes: representativeSlides,
      screenshots,
      ...editResult,
      replacementInputs: replacementResults,
      decorationProtected: replacementResults.every(item => item.decorationProtected),
      jsonSaveReload: true,
      pptxExportReimport: true,
      roundtripSlideCount: roundtripState.slideCount,
      expectedTextCount: expectedState.textBySlide.reduce((total, texts) => total + texts.length, 0),
      expectedTextBySlide: expectedState.textBySlide,
      missingTexts,
      orderedTextChecks,
      imageCountBeforeExportBySlide: expectedState.imageCountBySlide,
      roundtripImageCountBySlide: roundtripState.imageCountBySlide,
      contentImageGeometryRetained: geometryRetained,
      unexpectedApiWrites: blockedWrites,
      pptxFile: path.basename(pptxPath),
    };
    fs.writeFileSync(
      path.join(evidenceRoot, 'browser-g6-summary.json'),
      `${JSON.stringify(summary, null, 2)}\n`,
      'utf8',
    );
    console.log(JSON.stringify(summary));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exit(1);
});

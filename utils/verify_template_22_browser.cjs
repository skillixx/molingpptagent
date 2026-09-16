// 在本地编辑器中验证 template_22 四视口、编辑换图、JSON 与 PPTX 往返。
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');

const evidenceRoot = path.resolve(process.argv[2]);
const templateRoot = path.resolve(process.argv[3]);
const documentData = JSON.parse(
  fs.readFileSync(path.join(evidenceRoot, 'real-handler-document.json'), 'utf8'),
);
const replacementBytes = fs.readFileSync(
  path.join(evidenceRoot, 'probe-assets', 'template_22_probe_content.jpg'),
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
const representativeSlides = [3, 5];

function templateAssetPath(urlPath) {
  const basename = path.basename(decodeURIComponent(urlPath));
  const candidate = path.join(templateRoot, basename);
  return fs.existsSync(candidate) && path.dirname(candidate) === templateRoot
    ? candidate
    : null;
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const blockedWrites = [];
  const screenshots = [];
  let expectedTextBySlide = [];
  let expectedContentImageCount = 0;
  let expectedImageCountBySlide = [];
  let expectedContentImageGeometry = null;
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
        const contentType = assetPath.endsWith('.png') ? 'image/png' : 'image/jpeg';
        return route.fulfill({ contentType, body: fs.readFileSync(assetPath) });
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
        store.setTitle('template22-g8-qa');
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
        if (name === 'mobile') {
          const title = index === 3 ? '本阶段四项成果' : '模板应用示例';
          const matches = page.getByText(title, { exact: true });
          for (let matchIndex = 0; matchIndex < await matches.count(); matchIndex += 1) {
            if (await matches.nth(matchIndex).isVisible()) {
              await matches.nth(matchIndex).scrollIntoViewIfNeeded();
              break;
            }
          }
        }
        const screenshotPath = path.join(viewportRoot, `${name}-${index}.png`);
        if (name === 'mobile') {
          await page.locator('.mobile-thumbnails .thumbnail-item').nth(index).screenshot({
            path: screenshotPath,
          });
        } else {
          await page.screenshot({ path: screenshotPath, fullPage: false });
        }
        screenshots.push(path.relative(evidenceRoot, screenshotPath).replaceAll('\\', '/'));
      }
    }

    await page.setViewportSize({ width: 1920, height: 1080 });
    const replacementDataUrl = `data:image/jpeg;base64,${replacementBytes.toString('base64')}`;
    const editResult = await page.evaluate(async replacement => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        const cover = store.slides[0];
        const coverTitle = cover.elements.find(element => element.textType === 'title');
        store.updateElement({
          id: coverTitle.id,
          slideId: cover.id,
          props: { content: '桃夭墨韵编辑验收' },
        });

        const textSlide = store.slides[3];
        const body = textSlide.elements.find(element => element.textType === 'item');
        store.updateElement({
          id: body.id,
          slideId: textSlide.id,
          props: { content: '正文编辑验收：内容保持可修改并可保存。' },
        });

        const imageSlide = store.slides[5];
        const image = imageSlide.elements.find(element => element.imageType === 'content');
        const beforeDecorations = JSON.stringify(
          imageSlide.elements.filter(element => element.imageType === 'decoration'),
        );
        const beforeClip = JSON.stringify(image.clip);
        store.updateElement({ id: image.id, slideId: imageSlide.id, props: { src: replacement } });
        const updatedImage = store.slides[5].elements.find(
          element => element.id === image.id && element.imageType === 'content',
        );
        const afterDecorations = JSON.stringify(
          store.slides[5].elements.filter(element => element.imageType === 'decoration'),
        );
        if (beforeDecorations !== afterDecorations) throw new Error('图片替换改变了固定装饰');
        if (beforeClip !== JSON.stringify(updatedImage.clip)) throw new Error('图片替换改变了裁切协议');
        if (updatedImage.src !== replacement) throw new Error('业务图片没有完成替换');
        store.updateSlideIndex(5);
        return {
          slideCount: store.slides.length,
          decorationProtected: true,
          contentImageReplaced: true,
        };
      });
    }, replacementDataUrl);
    await canvas.screenshot({ path: path.join(editorRoot, 'image-after-replacement.png') });

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
      transfer.items.add(new File([raw], 'template-22-saved.json', { type: 'application/json' }));
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        useImport().importJSON(transfer.files, true);
      });
    }, fs.readFileSync(jsonPath, 'utf8'));
    await page.waitForFunction(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const serialized = JSON.stringify(useSlidesStore().slides);
        return useSlidesStore().slides.length === 7
          && serialized.includes('桃夭墨韵编辑验收')
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
        return {
          textBySlide: slides.map(slide => slide.elements
            .map(element => plainText(element.content || element.text?.content || ''))
            .filter(Boolean)),
          contentImageCount: slides.reduce(
            (total, slide) => total + slide.elements.filter(
              element => element.type === 'image' && element.imageType === 'content',
            ).length,
            0,
          ),
          imageCountBySlide: slides.map(slide => slide.elements.filter(
            element => element.type === 'image',
          ).length),
          contentImageGeometry: (() => {
            const image = slides[5].elements.find(
              element => element.type === 'image' && element.imageType === 'content',
            );
            return image
              ? { left: image.left, top: image.top, width: image.width, height: image.height }
              : null;
          })(),
        };
      });
    });
    expectedTextBySlide = expectedState.textBySlide;
    expectedContentImageCount = expectedState.contentImageCount;
    expectedImageCountBySlide = expectedState.imageCountBySlide;
    expectedContentImageGeometry = expectedState.contentImageGeometry;

    const pptxDownload = page.waitForEvent('download');
    await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      const { default: useExport } = await import('/src/hooks/useExport.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        return useExport().exportPPTX(store.slides, true, true);
      });
    });
    const pptxPath = path.join(evidenceRoot, 'template_22_g8_roundtrip.pptx');
    await (await pptxDownload).saveAs(pptxPath);

    await page.evaluate(async bytes => {
      const { default: useImport } = await import('/src/hooks/useImport.ts');
      const transfer = new DataTransfer();
      transfer.items.add(new File([new Uint8Array(bytes)], 'template-22-roundtrip.pptx'));
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        useImport().importPPTXFile(transfer.files, { cover: true, fixedViewport: true });
      });
    }, [...fs.readFileSync(pptxPath)]);
    await page.waitForFunction(async expectedBySlide => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        return store.slides.length === expectedBySlide.length;
      });
    }, expectedTextBySlide, { timeout: 90000 });

    const roundtripState = await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      const plainText = raw => {
        const container = document.createElement('div');
        container.innerHTML = typeof raw === 'string' ? raw : '';
        return (container.textContent || '').replace(/\s+/g, ' ').trim();
      };
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const slides = useSlidesStore().slides;
        return {
          slideCount: slides.length,
          textBySlide: slides.map(slide => slide.elements
            .map(element => plainText(element.content || element.text?.content || ''))
            .filter(Boolean)),
          imageCountBySlide: slides.map(slide => slide.elements.filter(
            element => element.type === 'image',
          ).length),
          imageGeometryBySlide: slides.map(slide => slide.elements
            .filter(element => element.type === 'image')
            .map(element => ({
              left: element.left,
              top: element.top,
              width: element.width,
              height: element.height,
            }))),
        };
      });
    });
    const missingTexts = [];
    for (let slideIndex = 0; slideIndex < expectedTextBySlide.length; slideIndex += 1) {
      const actualText = roundtripState.textBySlide[slideIndex].join(' | ');
      for (const expectedText of expectedTextBySlide[slideIndex]) {
        const position = actualText.indexOf(expectedText);
        if (position < 0) {
          missingTexts.push(`slide-${slideIndex + 1}:${expectedText}`);
        }
      }
    }
    if (missingTexts.length) throw new Error(`PPTX 往返丢失文本: ${missingTexts.join(', ')}`);
    const orderedTextChecks = {
      1: ['项目背景', '关键成果', '实施路径', '后续计划'],
      3: ['统一视觉规范', '完善模板库存', '保留编辑能力', '建立验收证据'],
      4: ['页面库存', '页面类型', '业务图片', '验收视口'],
      6: ['确认候选版本', '进入后续交付'],
    };
    for (const [indexText, orderedTexts] of Object.entries(orderedTextChecks)) {
      const slideIndex = Number(indexText);
      const actualText = roundtripState.textBySlide[slideIndex].join(' | ');
      const positions = orderedTexts.map(text => actualText.indexOf(text));
      if (positions.some(position => position < 0)
        || positions.some((position, index) => index > 0 && position < positions[index - 1])) {
        throw new Error(`PPTX 往返改变第 ${slideIndex + 1} 页项目顺序: ${orderedTexts.join(', ')}`);
      }
    }
    if (expectedContentImageCount < 1
      || expectedImageCountBySlide[5] !== roundtripState.imageCountBySlide[5]) {
      throw new Error('PPTX 往返没有保留业务图片元素');
    }
    const geometryRetained = expectedContentImageGeometry
      && roundtripState.imageGeometryBySlide[5].some(geometry => (
        Math.abs(geometry.left - expectedContentImageGeometry.left) < 2
        && Math.abs(geometry.top - expectedContentImageGeometry.top) < 2
        && Math.abs(geometry.width - expectedContentImageGeometry.width) < 2
        && Math.abs(geometry.height - expectedContentImageGeometry.height) < 2
      ));
    if (!geometryRetained) throw new Error('PPTX 往返没有保留业务图片槽位几何位置');
    if (blockedWrites.length) throw new Error(`检测到非预期写请求: ${blockedWrites.join(', ')}`);

    const summary = {
      schemaVersion: 1,
      templateId: 'template_22',
      status: 'PASS',
      frontendUrl: 'http://127.0.0.1:5778/editor',
      sourceSlideCount: documentData.slides.length,
      viewports: viewports.map(([name, width, height]) => ({ name, width, height })),
      representativeSlideIndexes: representativeSlides,
      screenshots,
      titleEdited: true,
      bodyEdited: true,
      contentImageReplaced: editResult.contentImageReplaced,
      decorationProtected: editResult.decorationProtected,
      jsonSaveReload: true,
      pptxExportReimport: true,
      roundtripSlideCount: roundtripState.slideCount,
      expectedTextCount: expectedTextBySlide.reduce((total, texts) => total + texts.length, 0),
      expectedTextBySlide,
      missingTexts,
      orderedTextChecks,
      contentImageBeforeExport: expectedContentImageCount,
      imageCountBeforeExportBySlide: expectedImageCountBySlide,
      contentImageGeometryBeforeExport: expectedContentImageGeometry,
      roundtripImageCountBySlide: roundtripState.imageCountBySlide,
      contentImageGeometryRetained: geometryRetained,
      unexpectedApiWrites: blockedWrites,
      pptxFile: path.basename(pptxPath),
    };
    fs.writeFileSync(
      path.join(evidenceRoot, 'browser-g8-summary.json'),
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

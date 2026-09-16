// 在本地编辑器中验证 template_22 探针的编辑、换图、保存和 PPTX 往返。
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');

const directory = path.resolve(process.argv[2]);
const documentData = JSON.parse(fs.readFileSync(path.join(directory, 'probe-document.json'), 'utf8'));
const replacementImages = [
  ['landscape', 'template_22_probe_content.jpg', 600, 450],
  ['portrait', 'template_22_probe_portrait.jpeg', 600, 900],
  ['square', 'template_22_probe_square.jpeg', 600, 600],
].map(([name, filename, width, height]) => ({
  name,
  width,
  height,
  src: `data:image/jpeg;base64,${fs.readFileSync(path.join(directory, filename)).toString('base64')}`,
}));

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const blockedWrites = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
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
        store.setTitle('template22-probe-qa');
        store.setTheme(data.theme);
        store.setViewportSize(data.viewport_size);
        store.setViewportRatio(data.viewport_ratio);
        store.setSlides(data.slides);
      });
    }, documentData);

    await page.evaluate(async replacements => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        const cover = store.slides[0];
        const title = cover.elements.find(element => element.textType === 'title');
        store.updateElement({
          id: title.id,
          slideId: cover.id,
          props: { content: title.content.replace('桃夭墨韵商务汇报', '桃夭墨韵编辑验证') },
        });

        const rectSlide = store.slides[1];
        const rectImage = rectSlide.elements.find(element => element.imageType === 'content');
        const rectDecorations = JSON.stringify(
          rectSlide.elements.filter(element => element.imageType === 'decoration'),
        );
        // 依次换入真实横图、竖图和方图，确保三种输入都走过编辑器更新路径。
        for (const replacement of replacements) {
          store.updateElement({
            id: rectImage.id,
            slideId: rectSlide.id,
            props: {
              src: replacement.src,
              originalWidth: replacement.width,
              originalHeight: replacement.height,
            },
          });
          const updated = store.slides[1].elements.find(element => element.id === rectImage.id);
          if (updated.src !== replacement.src) throw new Error(`${replacement.name} 图片没有完成替换`);
          if (updated.originalWidth !== replacement.width || updated.originalHeight !== replacement.height) {
            throw new Error(`${replacement.name} 图片尺寸没有保留`);
          }
        }
        const rectAfterDecorations = JSON.stringify(
          store.slides[1].elements.filter(element => element.imageType === 'decoration'),
        );
        if (rectDecorations !== rectAfterDecorations) throw new Error('矩形换图改变了固定装饰');

        const circleSlide = store.slides[2];
        const circleImage = circleSlide.elements.find(element => element.imageType === 'content');
        const circleDecorations = JSON.stringify(
          circleSlide.elements.filter(element => element.imageType === 'decoration'),
        );
        const circleShape = circleImage.clip?.shape;
        store.updateElement({
          id: circleImage.id,
          slideId: circleSlide.id,
          props: {
            src: replacements[1].src,
            originalWidth: replacements[1].width,
            originalHeight: replacements[1].height,
          },
        });
        const updatedCircle = store.slides[2].elements.find(element => element.id === circleImage.id);
        if (updatedCircle.clip?.shape !== circleShape) throw new Error('圆形换图改变了裁切形状');
        const circleAfterDecorations = JSON.stringify(
          store.slides[2].elements.filter(element => element.imageType === 'decoration'),
        );
        if (circleDecorations !== circleAfterDecorations) throw new Error('圆形换图改变了固定装饰');
      });
    }, replacementImages);

    await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      const store = document.querySelector('#app').__vue_app__.runWithContext(() => useSlidesStore());
      const circle = store.slides[2].elements.find(element => element.imageType === 'content');
      if (circle.clip?.shape !== 'ellipse') throw new Error('圆形探针没有保留 ellipse 裁切');
      store.updateSlideIndex(2);
    });
    await page.locator('.viewport-wrapper').first().screenshot({
      path: path.join(directory, 'editor-circle-after-replacement.png'),
    });

    const jsonDownload = page.waitForEvent('download');
    await page.evaluate(async () => {
      const { default: useExport } = await import('/src/hooks/useExport.ts');
      document.querySelector('#app').__vue_app__.runWithContext(() => useExport().exportJSON());
    });
    const jsonPath = path.join(directory, 'editor-saved.json');
    await (await jsonDownload).saveAs(jsonPath);

    await page.reload();
    await canvas.waitFor({ state: 'visible' });
    await page.evaluate(async raw => {
      const { default: useImport } = await import('/src/hooks/useImport.ts');
      const transfer = new DataTransfer();
      transfer.items.add(new File([raw], 'saved.json', { type: 'application/json' }));
      document.querySelector('#app').__vue_app__.runWithContext(() => useImport().importJSON(transfer.files, true));
    }, fs.readFileSync(jsonPath, 'utf8'));
    await page.waitForFunction(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const slides = useSlidesStore().slides;
        return slides.length === 3 && JSON.stringify(slides).includes('桃夭墨韵编辑验证');
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
    const pptxPath = path.join(directory, 'template_22_probe_editor_roundtrip.pptx');
    await (await pptxDownload).saveAs(pptxPath);

    await page.evaluate(async bytes => {
      const { default: useImport } = await import('/src/hooks/useImport.ts');
      const transfer = new DataTransfer();
      transfer.items.add(new File([new Uint8Array(bytes)], 'roundtrip.pptx'));
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        useImport().importPPTXFile(transfer.files, { cover: true, fixedViewport: true });
      });
    }, [...fs.readFileSync(pptxPath)]);
    await page.waitForFunction(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const slides = useSlidesStore().slides;
        const content = JSON.stringify(slides);
        return slides.length === 3
          && content.includes('桃夭墨韵编辑验证')
          && content.includes('普通图文正文必须完整保留')
          && content.includes('圆形换图和往返后仍需保持裁切');
      });
    }, null, { timeout: 60000 });

    if (blockedWrites.length) {
      throw new Error(`检测到非预期写请求: ${blockedWrites.join(', ')}`);
    }
    fs.writeFileSync(
      path.join(directory, 'probe-browser-summary.json'),
      `${JSON.stringify({
        schemaVersion: 1,
        templateId: 'template_22',
        status: 'PASS',
        replacementInputs: replacementImages.map(({ name, width, height }) => ({ name, width, height })),
        jsonEdit: true,
        decorationProtection: true,
        circleCrop: true,
        jsonSaveReload: true,
        pptxExportReimport: true,
        unexpectedApiWrites: blockedWrites,
      }, null, 2)}\n`,
      'utf8',
    );
    console.log('PASS: probe JSON edit, image replacement, decoration protection, JSON reload, PPTX export and reimport');
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exit(1);
});

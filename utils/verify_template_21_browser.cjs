// 在独立浏览器中验证固定样本、四视口和项目原生导出；不写真实作品或触发生成。
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');
const directory = path.resolve(process.argv[2]);
const document = JSON.parse(fs.readFileSync(path.join(directory, 'document.json'), 'utf8'));

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const blockedWrites = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await page.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.protocol === 'data:' || url.protocol === 'blob:') return route.continue();
      if (url.origin !== 'http://127.0.0.1:5778') return route.abort();
      if (request.method() !== 'GET') { blockedWrites.push(url.pathname); return route.abort(); }
      if (url.pathname === '/api/auth/me') return route.fulfill({ json: { user_id: 1, app_id: 1, product_id: 1 } });
      if (url.pathname.startsWith('/api/') && !url.pathname.startsWith('/api/data/') && url.pathname !== '/api/templates') {
        return route.fulfill({ status: 404, json: { code: 'QA_ONLY' } });
      }
      return route.continue();
    });
    await page.goto('http://127.0.0.1:5778/editor');
    await page.locator('.viewport-wrapper').first().waitFor({ state: 'visible', timeout: 60000 });
    await page.evaluate(async data => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      const app = document.querySelector('#app').__vue_app__;
      app.runWithContext(() => {
        const store = useSlidesStore();
        store.clearPresentationContext();
        store.setTitle('template21-fixed-qa');
        store.setTheme(data.theme);
        store.setViewportSize(data.viewport_size);
        store.setViewportRatio(data.viewport_ratio);
        store.setSlides(data.slides);
      });
    }, document);
    const canvas = page.locator('.viewport-wrapper').first();
    for (const [name, width, height] of [['desktop',1920,1080],['laptop',1366,768],['tablet',768,1024],['mobile',390,844]]) {
      await page.setViewportSize({ width, height });
      for (const index of [4, 6]) {
        await page.evaluate(async index => {
          const { useSlidesStore } = await import('/src/store/index.ts');
          document.querySelector('#app').__vue_app__.runWithContext(() => useSlidesStore().updateSlideIndex(index));
          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        }, index);
        await canvas.locator('img').evaluateAll(imgs => Promise.all(imgs.map(i => i.decode())));
        await page.evaluate(() => document.fonts.ready);
        if (name === 'mobile') {
          // 手机端为纵向作品预览，滚动到真实目标卡片，不能把首屏误作指标页验收。
          const matches = page.getByText(index === 4 ? '关键业务指标' : '下一步行动', { exact: true });
          for (let i = 0; i < await matches.count(); i++) {
            if (await matches.nth(i).isVisible()) { await matches.nth(i).scrollIntoViewIfNeeded(); break; }
          }
        }
        if (name === 'mobile') {
          await page.locator('.mobile-thumbnails .thumbnail-item').nth(index).screenshot({ path: path.join(directory, `${name}-${index}.png`) });
        } else {
          await page.screenshot({ path: path.join(directory, `${name}-${index}.png`) });
        }
        if (name === 'desktop') await canvas.screenshot({ path: path.join(directory, `slide-${index}.png`) });
      }
    }
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        const cover = store.slides[0];
        const title = cover.elements.find(e => e.textType === 'title');
        store.updateElement({ id: title.id, slideId: cover.id, props: { content: title.content.replace('业务汇报', '编辑换图验收') } });
        const slide = store.slides[5];
        const image = slide.elements.find(e => e.imageType === 'content');
        const decorations = JSON.stringify(slide.elements.filter(e => e.imageType === 'decoration'));
        store.updateElement({ id: image.id, slideId: slide.id, props: { src: '/api/data/template_21_asset_marble_tile_ivory_v1.jpg' } });
        if (decorations !== JSON.stringify(slide.elements.filter(e => e.imageType === 'decoration'))) throw new Error('Decoration changed');
      });
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
        const store = useSlidesStore();
        return store.slides.length === 8 && JSON.stringify(store.slides).includes('编辑换图验收');
      });
    });
    const download = page.waitForEvent('download');
    await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      const { default: useExport } = await import('/src/hooks/useExport.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const store = useSlidesStore();
        return useExport().exportPPTX(store.slides, true, true);
      });
    });
    const pptxPath = path.join(directory, 'editor-export.pptx');
    await (await download).saveAs(pptxPath);
    await page.evaluate(async bytes => {
      const { default: useImport } = await import('/src/hooks/useImport.ts');
      const transfer = new DataTransfer();
      transfer.items.add(new File([new Uint8Array(bytes)], 'roundtrip.pptx'));
      document.querySelector('#app').__vue_app__.runWithContext(() => useImport().importPPTXFile(transfer.files, { cover: true, fixedViewport: true }));
    }, [...fs.readFileSync(pptxPath)]);
    await page.waitForFunction(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => {
        const slides = useSlidesStore().slides;
        return slides.length === 8 && !slides[0].templateSlideId && JSON.stringify(slides).includes('编辑换图验收');
      });
    });
    const expected = JSON.parse(fs.readFileSync(path.join(directory, 'expected.json'), 'utf8'));
    const roundtrip = await page.evaluate(async () => {
      const { useSlidesStore } = await import('/src/store/index.ts');
      return document.querySelector('#app').__vue_app__.runWithContext(() => JSON.stringify(useSlidesStore().slides));
    });
    if (expected.some(text => !roundtrip.includes(text))) throw new Error('Roundtrip lost expected text');
    if (blockedWrites.length) throw new Error('Unexpected writes blocked: ' + blockedWrites.join(','));
    console.log('PASS: four viewports, edit/image replacement, JSON save/reload, native PPTX export/reimport, expected text retained; no API writes');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });

// 使用当前分支真实前后端验证模板列表、封面、选择状态和编辑器入口。
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE_PATH || 'playwright');

const evidenceRoot = path.resolve(process.argv[2]);
fs.mkdirSync(evidenceRoot, { recursive: true });

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    // 仅模拟隔离验收身份；模板列表、JSON 和图片仍由当前主 API 实际返回。
    await page.route('**/api/auth/me', route => route.fulfill({json:{user_id:1,app_id:1,product_id:1}}));
    const failedResponses = [];
    page.on('response', response => {
      const url = response.url();
      if (response.status() >= 400 && !url.endsWith('/api/auth/me')) {
        failedResponses.push({ url, status: response.status() });
      }
    });

    await page.goto('http://127.0.0.1:5778/app', { waitUntil: 'networkidle' });
    const card = page.locator('.template-card').filter({
      has: page.getByText('蓝黑城市·融资路演', { exact: true }),
    });
    await card.waitFor({ state: 'visible', timeout: 30000 }).catch(async error => {
      await page.screenshot({path:path.join(evidenceRoot,'selector-failure.png')});
      fs.writeFileSync(path.join(evidenceRoot,'selector-failure.json'), JSON.stringify({url:page.url(),body:await page.locator('body').innerText(),failedResponses},null,2));
      throw error;
    });
    await card.locator('img').evaluate(image => image.decode());
    await card.click();
    if (!(await card.evaluate(element => element.classList.contains('selected')))) {
      throw new Error('template_25 点击后没有进入选择状态');
    }
    const cover = card.locator('img');
    const coverState = await cover.evaluate(image => ({
      src: image.getAttribute('src'),
      complete: image.complete,
      naturalWidth: image.naturalWidth,
      naturalHeight: image.naturalHeight,
    }));
    if (!coverState.complete || coverState.naturalWidth <= 0 || coverState.naturalHeight <= 0) {
      throw new Error(`模板封面尺寸或加载状态异常: ${JSON.stringify(coverState)}`);
    }
    const selectorScreenshot = path.join(evidenceRoot, 'runtime-template-selected.png');
    await card.screenshot({ path: selectorScreenshot });

    await page.goto('http://127.0.0.1:5778/editor', { waitUntil: 'networkidle' });
    await page.locator('.viewport-wrapper').first().waitFor({ state: 'visible', timeout: 30000 });
    const editorScreenshot = path.join(evidenceRoot, 'runtime-editor-entry.png');
    await page.screenshot({ path: editorScreenshot, fullPage: false });

    const templateResponse = await page.request.get('http://127.0.0.1:5778/api/templates');
    const templatePayload = await templateResponse.json();
    const entries = templatePayload.data.filter(item => item.id === 'template_25');
    if (entries.length !== 1 || entries[0].name !== '蓝黑城市·融资路演') {
      throw new Error(`真实模板列表注册异常: ${JSON.stringify(entries)}`);
    }
    const assetResponse = await page.request.get(
      'http://127.0.0.1:5778/api/data/template_25.jpg',
    );
    if (!assetResponse.ok()) throw new Error(`模板封面接口失败: ${assetResponse.status()}`);
    if (failedResponses.length) {
      throw new Error(`运行入口包含失败请求: ${JSON.stringify(failedResponses)}`);
    }

    const summary = {
      schemaVersion: 1,
      templateId: 'template_25',
      status: 'PASS',
      branchFrontendUrl: 'http://127.0.0.1:5778',
      branchApiUrl: 'http://127.0.0.1:6800',
      selectorUrl: 'http://127.0.0.1:5778/app',
      editorUrl: 'http://127.0.0.1:5778/editor',
      registrationCount: entries.length,
      registeredName: entries[0].name,
      cover: coverState,
      templateSelected: true,
      authenticationMode: 'browser-fixture-only',
      backendMode: 'local-project-api-auth-fixture-only',
      editorEntryVisible: true,
      screenshots: [path.basename(selectorScreenshot), path.basename(editorScreenshot)],
      failedResponses,
    };
    fs.writeFileSync(
      path.join(evidenceRoot, 'runtime-summary.json'),
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

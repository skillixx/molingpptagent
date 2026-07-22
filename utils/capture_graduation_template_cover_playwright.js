async (page) => {
  // 切换到封面页，确保模板缩略图与编辑器中的最新商业化封面一致。
  await page.evaluate(() => {
    const app = document.querySelector('#app')?.__vue_app__
    const piniaKey = Reflect.ownKeys(app?._context?.provides || {})
      .find(key => String(key) === 'Symbol(pinia)')
    const store = piniaKey ? app._context.provides[piniaKey]?._s?.get('slides') : undefined
    if (!store) throw new Error('未找到 slides store')
    store.updateSlideIndex(0)
  })

  // 等待两帧，让背景图、文字和缩放状态都完成刷新。
  await page.evaluate(() => new Promise(resolve => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  }))

  const canvas = page.locator('.viewport-wrapper').first()
  await canvas.waitFor({ state: 'visible' })
  await canvas.screenshot({
    path: 'backend/main_api/template/template_5.jpg',
    type: 'jpeg',
    quality: 92,
  })

  return {
    path: 'backend/main_api/template/template_5.jpg',
    box: await canvas.boundingBox(),
  }
}

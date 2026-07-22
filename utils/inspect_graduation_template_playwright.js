async (page) => {
  // 从 Vue 应用里读取 Pinia 幻灯片状态，核对模板语义替换和画布尺寸。
  const summary = await page.evaluate(() => {
    const app = document.querySelector('#app')?.__vue_app__
    const piniaKey = Reflect.ownKeys(app?._context?.provides || {})
      .find(key => String(key) === 'Symbol(pinia)')
    const pinia = piniaKey ? app._context.provides[piniaKey] : undefined
    const store = pinia?._s?.get('slides')
    if (!store) throw new Error('未找到 slides store')

    const plainText = element => {
      const html = element.content || element.text?.content || ''
      const container = document.createElement('div')
      container.innerHTML = html
      return (container.textContent || '').trim()
    }

    return {
      count: store.slides.length,
      types: store.slides.map(slide => slide.type),
      viewportSize: store.viewportSize,
      viewportRatio: store.viewportRatio,
      texts: store.slides.map(slide => slide.elements.map(plainText).filter(Boolean)),
      charts: store.slides.flatMap(slide => slide.elements
        .filter(element => element.type === 'chart')
        .map(element => ({ chartType: element.chartType, data: element.data }))),
      overflowElements: store.slides.flatMap((slide, slideIndex) => slide.elements
        .filter(element => {
          const isBackground = element.type === 'image' && element.width > 1100 && element.height > 650
          if (isBackground) return false
          const right = element.left + (Number.isFinite(element.width) ? element.width : 0)
          const bottom = element.top + (Number.isFinite(element.height) ? element.height : 0)
          return element.left < 0 || element.top < -15 || right > 1280 || bottom > 720
        })
        .map(element => ({ slide: slideIndex + 1, id: element.id, type: element.type }))),
    }
  })

  // 逐页切换后截图，确保每类页面都经过真实渲染。
  for (let index = 0; index < summary.count; index += 1) {
    await page.evaluate(slideIndex => {
      const app = document.querySelector('#app').__vue_app__
      const piniaKey = Reflect.ownKeys(app._context.provides).find(key => String(key) === 'Symbol(pinia)')
      app._context.provides[piniaKey]._s.get('slides').updateSlideIndex(slideIndex)
    }, index)
    await page.waitForTimeout(300)
    await page.screenshot({ path: `.playwright-cli/graduation-template-slide-${index + 1}.png` })
  }

  const brokenImages = await page.locator('img').evaluateAll(images => images
    .filter(image => image.complete && image.naturalWidth === 0)
    .map(image => image.src))

  return { ...summary, brokenImages }
}

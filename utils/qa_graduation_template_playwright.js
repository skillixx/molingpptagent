async (page) => {
  // 只模拟 AI 内容流，模板列表、模板 JSON、图片资源和编辑器仍走真实本地服务。
  await page.unroute('**/api/tools/aippt').catch(() => {})

  const slides = [
    { type: 'cover', data: { title: '人工智能毕业答辩', text: '计算机学院 · 2026' } },
    { type: 'contents', data: { items: ['研究背景', '研究目标', '研究方法', '实验结果', '问题讨论', '结论展望'] } },
    { type: 'transition', data: { title: '研究背景', text: '从行业现状到研究问题' } },
    {
      type: 'content',
      data: {
        title: '研究背景',
        items: [
          { kind: 'text', title: '行业现状', text: '人工智能正在重塑科研与产业流程。' },
          { kind: 'text', title: '核心问题', text: '现有方法在准确率与可解释性之间仍需平衡。' },
          { kind: 'text', title: '研究价值', text: '本研究提出可复现、可验证的改进方案。' },
        ],
      },
    },
    {
      type: 'content',
      data: {
        title: '问题讨论',
        items: [
          { kind: 'text', title: '样本规模', text: '后续需要继续扩大多场景样本覆盖。' },
          { kind: 'text', title: '泛化能力', text: '跨数据集性能仍有进一步提升空间。' },
          { kind: 'text', title: '部署成本', text: '推理效率和硬件成本需要持续优化。' },
        ],
      },
    },
    {
      type: 'content',
      data: {
        title: '研究目标',
        items: [{ kind: 'text', title: '总体目标', text: '构建一套稳定、准确且可解释的研究方案。' }],
      },
    },
    {
      type: 'content',
      data: {
        title: '关键创新',
        items: [
          { kind: 'text', title: '方法创新', text: '设计新的特征融合机制。' },
          { kind: 'text', title: '应用创新', text: '形成可迁移的工程实现路径。' },
        ],
      },
    },
    {
      type: 'content',
      data: {
        title: '研究方法与实施路径',
        items: [
          { kind: 'text', title: '数据准备', text: '完成清洗、标注和训练集划分。' },
          { kind: 'text', title: '模型设计', text: '构建兼顾精度与可解释性的网络结构。' },
          { kind: 'text', title: '实验验证', text: '通过消融实验和多组基线开展对比。' },
          { kind: 'text', title: '成果评估', text: '从性能、稳定性和应用价值综合评价。' },
        ],
      },
    },
    {
      type: 'content',
      data: {
        title: '实验设计',
        items: [
          { kind: 'text', title: '对照设置', text: '选择公开基线模型作为参照。' },
          { kind: 'text', title: '评价指标', text: '同时关注准确率、召回率和效率。' },
          { kind: 'text', title: '消融分析', text: '分别验证各模块的实际贡献。' },
          { kind: 'text', title: '重复实验', text: '通过多次运行评估结果稳定性。' },
        ],
      },
    },
    {
      type: 'content',
      data: {
        title: '结果分析',
        items: [
          { kind: 'text', title: '精度提升', text: '核心指标相较基线明显提高。' },
          { kind: 'text', title: '稳定表现', text: '不同随机种子下波动较小。' },
          { kind: 'text', title: '效率变化', text: '新增模块仅带来有限计算开销。' },
          { kind: 'text', title: '应用价值', text: '验证了方案在实际场景中的潜力。' },
        ],
      },
    },
    {
      type: 'content',
      data: {
        title: '结论与展望',
        items: [
          { kind: 'text', title: '主要结论', text: '提出的方法达到预期研究目标。' },
          { kind: 'text', title: '理论意义', text: '补充了相关问题的分析框架。' },
          { kind: 'text', title: '实践意义', text: '形成了可复用的技术实现方案。' },
          { kind: 'text', title: '未来工作', text: '将继续扩充数据并优化部署效率。' },
        ],
      },
    },
    {
      type: 'content',
      data: {
        title: '系统展示',
        items: [{
          kind: 'image',
          title: '系统原型',
          text: '核心功能已完成端到端验证。',
          src: '/api/data/template_5_asset_adaae87c9afb.png',
        }],
      },
    },
    {
      type: 'content',
      data: {
        title: '成果场景',
        items: [
          {
            kind: 'image',
            title: '数据准备',
            text: '形成规范的数据治理与样本管理流程。',
            src: '/api/data/template_5_asset_adaae87c9afb.png',
          },
          {
            kind: 'image',
            title: '模型验证',
            text: '通过多组实验验证方案的有效性。',
            src: '/api/data/template_5_asset_2efcef743ac3.png',
          },
          {
            kind: 'image',
            title: '成果应用',
            text: '将研究成果沉淀为可复用的应用能力。',
            src: '/api/data/template_5_asset_2937dfb7a757.png',
          },
        ],
      },
    },
    {
      type: 'content',
      data: {
        title: '实验结果',
        items: [
          {
            kind: 'chart',
            title: '模型准确率',
            text: '最终方案准确率达到 93%。',
            chartType: 'bar',
            labels: ['基线', '方案A', '方案B', '最终方案'],
            series: [{ name: '准确率', data: [72, 81, 88, 93] }],
          },
        ],
      },
    },
    { type: 'end', data: {} },
  ]

  const body = slides.map(slide => `data: ${JSON.stringify(slide)}\n\n`).join('') + 'data: [DONE]\n\n'
  await page.route('**/api/tools/aippt', route => route.fulfill({
    status: 200,
    contentType: 'text/event-stream; charset=utf-8',
    headers: { 'Cache-Control': 'no-cache' },
    body,
  }))

  await page.goto('http://127.0.0.1:5174/ppt')
  await page.getByText('毕业答辩', { exact: true }).click()
  await page.getByRole('button', { name: /生成PPT/ }).click()
  await page.waitForURL(/\/editor/)
  await page.waitForTimeout(4000)

  return { url: page.url(), title: await page.title() }
}

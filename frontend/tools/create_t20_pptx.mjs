import pptxgen from 'pptxgenjs'

const outputPath = process.argv[2]
if (!outputPath) throw new Error('missing output path')

const pptx = new pptxgen()
pptx.layout = 'LAYOUT_16x9'
pptx.author = 'TrainPPTAgent T20 verification'
pptx.subject = 'PPTX archive roundtrip'
pptx.title = 'TrainPPTAgent T20'
const slide = pptx.addSlide()
slide.background = { color: 'F4F7FF' }
slide.addText('TrainPPTAgent T20', {
  x: 0.8, y: 1.1, w: 8.4, h: 0.8, fontFace: 'Microsoft YaHei',
  fontSize: 30, bold: true, color: '2541B2', align: 'center',
})
slide.addText('同一 Blob · 对象存储归档 · 历史下载', {
  x: 1, y: 2.3, w: 8, h: 0.6, fontFace: 'Microsoft YaHei',
  fontSize: 18, color: '344054', align: 'center',
})
await pptx.writeFile({ fileName: outputPath })

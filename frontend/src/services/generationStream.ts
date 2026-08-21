export class GenerationStreamError extends Error {
  constructor(public readonly status: number, message = 'GENERATION_STREAM_FAILED') {
    super(message)
    this.name = 'GenerationStreamError'
  }
}

export class GenerationIncompleteError extends Error {
  constructor(
    public readonly received: number,
    public readonly expected: number,
  ) {
    super('PPT_STREAM_INCOMPLETE')
    this.name = 'GenerationIncompleteError'
  }
}

/**
 * 消费生成接口的文本流。只有 HTTP 成功且存在响应体时才进入生成态，
 * 避免把后端错误 JSON 当成大纲或幻灯片内容。
 */
export async function consumeTextResponse(
  response: Response,
  onChunk: (chunk: string) => void,
  onOpen?: () => void,
): Promise<string> {
  if (!response.ok || !response.body) {
    throw new GenerationStreamError(response.status)
  }

  onOpen?.()
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let content = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value, { stream: true })
    content += chunk
    onChunk(chunk)
  }

  const tail = decoder.decode()
  if (tail) {
    content += tail
    onChunk(tail)
  }
  return content
}

/** 大纲至少需要一个 Markdown 标题，过程话术或错误 JSON 均视为中断。 */
export function isUsableMarkdownOutline(content: string): boolean {
  const normalized = content.trim()
  return normalized.length >= 20
    && /^#{1,6}\s+\S+/m.test(normalized)
    && !/^\s*\{\s*"code"\s*:/i.test(normalized)
}

/**
 * 与后端大纲转幻灯片规则保持一致，计算一次生成至少应返回的页数。
 * 封面、目录、章节过渡页、三级标题内容页和结束页都必须存在。
 */
export function expectedSlideCountFromOutline(content: string | null | undefined): number {
  // 模板页可被直接访问；缺少路由大纲时返回0，不能让生成按钮永久卡在加载态。
  if (typeof content !== 'string') return 0
  const lines = content.split(/\r?\n/).map(line => line.trim())
  const hasTitle = lines.some(line => /^#\s+\S+/.test(line))
  if (!hasTitle) return 0

  const sectionCount = lines.filter(line => /^##\s+\S+/.test(line)).length
  const contentCount = lines.filter(line => /^###\s+\S+/.test(line)).length
  const contentsPageCount = sectionCount > 0 ? 1 : 0
  return 1 + contentsPageCount + sectionCount + contentCount + 1
}

/** 结束信号只代表连接结束；页数达标后才代表业务生成完整。 */
export function assertCompleteSlideGeneration(received: number, expected: number): void {
  if (expected > 0 && received < expected) {
    throw new GenerationIncompleteError(received, expected)
  }
}

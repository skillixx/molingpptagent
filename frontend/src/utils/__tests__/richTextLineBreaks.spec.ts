import { describe, expect, it } from 'vitest'
import { DOMSerializer } from 'prosemirror-model'
import { createDocument } from '../prosemirror'

describe('模板文字的显式换行', () => {
  it('在解析和重新序列化后保留副标题、汇报人与日期三行', () => {
    const source = '<p style="text-align: center;"><span style="font-size: 22px;">产品发布<br>汇报人：产品团队<br>日期：2026年9月</span></p>'
    const documentNode = createDocument(source)
    const container = document.createElement('div')
    container.appendChild(DOMSerializer.fromSchema(documentNode.type.schema).serializeFragment(documentNode.content))
    // 使用编辑器公开的 HTML 解析接口检查实际换行，避免仅断言三个词仍存在。
    expect(container.querySelectorAll('br')).toHaveLength(2)
    expect(container.textContent).toBe('产品发布汇报人：产品团队日期：2026年9月')
    const reloaded = createDocument(container.innerHTML)
    expect(reloaded.eq(documentNode)).toBe(true)
  })
})

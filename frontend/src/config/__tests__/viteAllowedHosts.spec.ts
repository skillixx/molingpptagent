// @vitest-environment node

import { describe, expect, it } from 'vitest'

import viteConfig from '../../../vite.config'


describe('Vite 开发服务器域名白名单', () => {
  it('开发联调阶段允许反向代理使用任意 Host', () => {
    expect(viteConfig.server?.allowedHosts).toBe(true)
  })
})

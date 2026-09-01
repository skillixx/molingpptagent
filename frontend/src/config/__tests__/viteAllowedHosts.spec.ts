// @vitest-environment node

import { describe, expect, it } from 'vitest'

import viteConfig, { resolveAllowedHosts } from '../../../vite.config'


describe('Vite 开发服务器域名白名单', () => {
  it('默认只允许正式入口域名', () => {
    expect(viteConfig.server?.allowedHosts).toEqual(['ppt.axicomin.cn'])
  })

  it('只有显式开发开关才允许任意 Host', () => {
    expect(resolveAllowedHosts('true')).toBe(true)
    expect(resolveAllowedHosts('false')).toEqual(['ppt.axicomin.cn'])
    expect(resolveAllowedHosts()).toEqual(['ppt.axicomin.cn'])
  })
})

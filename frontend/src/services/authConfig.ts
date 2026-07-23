function parsePortalUrl(rawValue: string | undefined): string {
  if (!rawValue?.trim()) return ''
  try {
    const url = new URL(rawValue)
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.toString() : ''
  }
  catch {
    return ''
  }
}

export const authFrontendConfig = Object.freeze({
  ssoEnabled: import.meta.env.VITE_SSO_ENABLED === 'true',
  // 墨灵门户地址是部署配置，禁止在组件内写死测试服IP。
  molingPortalUrl: parsePortalUrl(import.meta.env.VITE_MOLING_PORTAL_URL),
})

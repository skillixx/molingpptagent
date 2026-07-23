const MOBILE_USER_AGENT = /(iPhone|iPod|iPad|Android|Mobile|BlackBerry|Symbian|Windows Phone)/i

export function shouldUseMobileEditor(userAgent: string, viewportWidth: number): boolean {
  // 同时依据设备能力和真实视口；桌面浏览器窄窗口不能继续挤压三栏编辑器。
  return MOBILE_USER_AGENT.test(userAgent) || viewportWidth <= 600
}

import { createReadStream, existsSync, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, normalize, resolve } from 'node:path'

const root = resolve('dist')
const port = Number.parseInt(process.env.VERIFY_PORT || '4174', 10)
const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
}

if (!existsSync(join(root, 'index.html'))) {
  throw new Error('dist不存在，请先执行正式构建')
}
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('VERIFY_PORT必须是有效端口')
}

createServer((request, response) => {
  // 验证服务器不记录query；解码失败、路径穿越和目录请求统一走安全回退。
  let pathname = '/'
  try {
    pathname = new URL(request.url || '/', 'http://127.0.0.1').pathname
  }
  catch {
    response.writeHead(400).end('Bad Request')
    return
  }
  let decodedPath = ''
  try {
    decodedPath = decodeURIComponent(pathname)
  }
  catch {
    response.writeHead(400).end('Bad Request')
    return
  }
  const relative = normalize(decodedPath).replace(/^([/\\])+/, '')
  const candidate = resolve(root, relative)
  const insideRoot = candidate === root || candidate.startsWith(`${root}\\`) || candidate.startsWith(`${root}/`)
  let filePath = insideRoot && existsSync(candidate) && statSync(candidate).isFile()
    ? candidate
    : join(root, 'index.html')
  if (pathname.startsWith('/assets/') && filePath.endsWith('index.html')) {
    response.writeHead(404, { 'Cache-Control': 'no-store' }).end('Not Found')
    return
  }
  const immutable = pathname.startsWith('/assets/')
  response.writeHead(200, {
    'Content-Type': mimeTypes[extname(filePath)] || 'application/octet-stream',
    'Cache-Control': immutable ? 'public, max-age=31536000, immutable' : 'no-store',
    'X-Content-Type-Options': 'nosniff',
  })
  createReadStream(filePath).pipe(response)
}).listen(port, '127.0.0.1', () => {
  console.log(`正式静态产物验证服务已启动 port=${port}`)
})

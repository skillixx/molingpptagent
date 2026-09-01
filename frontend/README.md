# 🚀 安装
```
npm install

npm run dev
```
Browser access: http://127.0.0.1:5778/

> 当前开发联调配置为 `server.allowedHosts: true`，便于反向代理通过任意 Host 访问 Vite 开发服务器。生产环境必须使用静态构建产物；若临时暴露 Vite 服务，应先恢复为精确域名白名单。

# 检查配置
vite.config.ts中配置的API地址
http://127.0.0.1:6800

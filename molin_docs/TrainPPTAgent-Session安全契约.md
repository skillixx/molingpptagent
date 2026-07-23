# TrainPPTAgent Session 安全契约

> 状态：T04代码契约与真实墨灵verify请求链均已验收通过。
> 生效前提：`SSO_ENABLED=true`、T04迁移已执行、生产Cookie启用Secure。

## 生命周期

- 登录票据由后端调用墨灵verify恰好一次；超时或终态未知时不自动重放，用户必须从墨灵重新发起进入。
- 每次成功登录签发新的256位级随机Session ID，不接受浏览器预置值，也不复用旧登录值。
- 同一浏览器再次成功登录时，先签发新Session，再撤销该浏览器Cookie指向的旧Session；其他设备的独立Session保持有效。
- Cookie只保存原始随机值；`app_sessions.id`只保存SHA-256摘要。
- 绝对有效期默认24小时（`SESSION_TTL_SECONDS=86400`），空闲有效期默认2小时（`SESSION_IDLE_TTL_SECONDS=7200`）；空闲期必须短于绝对期。
- `revoked_at`用于退出或管理员撤销；T05实现退出写入，T21实现过期清理。过期、撤销或查询不到均fail-closed。
- Session时间统一按UTC写库，API边界返回带时区时间。

## Cookie与入口

- Cookie属性：`HttpOnly`、`SameSite=Lax`、`Path=/`；staging/production强制`Secure`。
- `/enter`成功只返回302到`/works`，不把ticket带入目标URL。
- `/enter`所有成功和错误响应都设置`Cache-Control: no-store`与`Referrer-Policy: no-referrer`。
- ticket缺失、空白、含控制字符或超过512字符时，在调用平台前返回400。
- 平台票据失败返回401、app/product错域返回403、平台不可用返回503、协议异常返回502；任何失败都不创建本地Session。

## 日志与代理

- 应用安全事件只记录稳定事件名和request ID，不记录ticket、Cookie、内部令牌或平台原始正文。
- Nginx使用`location = /enter`精确代理并设置`access_log off`，避免查询串进入访问日志。
- 当前直接启动方式在SSO开启时关闭Uvicorn请求行日志；容器启动固定使用`--no-access-log`。非入口访问日志由Nginx承担。

## CSRF与Origin

- Cookie认证的写接口必须调用`enforce_trusted_origin`或采用等价CSRF Token机制；CORS不作为唯一防护。
- 第一版Origin采用完整字符串精确匹配，缺失、`null`、不同scheme、host或port均拒绝。
- `APP_BASE_URL`在SSO开启时必填，并按浏览器Origin规则移除路径和默认端口后参与精确匹配。
- T05的logout已接入Origin校验；后续作品/生成/导出写接口在各自任务接入。

## 当前用户与退出

- 浏览器通过外部`GET /api/auth/me`读取当前身份，代理只移除一次`/api`前缀，后端内部路由为`GET /auth/me`。
- 当前身份只来自服务端Session，查询串或请求体中的`user_id`不参与owner解析；响应只包含`user_id/app_id/product_id`。
- 外部`POST /api/auth/logout`在可信Origin下幂等撤销当前Cookie Session并清除Cookie；缺失或恶意Origin返回403且不得撤销会话。
- 同一浏览器标签共享的旧Cookie在任一标签退出后立即401；其他设备的独立Session保持有效。
- 前端每次受保护导航及标签重新可见时强制复核`/me`，认证epoch会丢弃退出后迟到的旧成功响应。

## 迁移、回滚与清理

- 应用启动不自动迁移；开启SSO时若`app_sessions`结构未就绪，在监听端口前安全失败。
- T04迁移创建哈希主键、用户索引和绝对过期索引；生产应用回滚保留表数据，不执行破坏性Alembic downgrade。
- 关闭`SSO_ENABLED`可停止新Session签发，但不删除既有会话数据。
- 物理清理由T21按过期/撤销时间分批实现；T04不在请求路径同步批量删除。

## 当前真实联调边界

- 2026-07-23已在现有Chrome登录态确认商品73可发起“进入应用”，并获得新的短期ticket。
- ticket仅在浏览器内存与本机隔离验收请求中传递，未写入文档、测试、控制台或应用日志；验收后已从浏览器地址清除。
- 只读内部主闸预检调用`user-entitlements`成功，证明当前Token与来源IP已获平台接受；该预检不消费ticket、不创建Session、不扣费。
- 新ticket签发后立即由本机隔离门面调用真实verify：入口返回302到`/works`，Cookie恢复得到HTTP 200，重放同一ticket得到HTTP 401；响应包含no-store/no-referrer且未回显ticket。
- 先前两次401归因于人工从历史提取票据导致的时效/旧票据问题，不再记录为Token/IP白名单阻塞。
- 本次隔离SQLite包含一条真实Session哈希记录；门面已关闭，但当前环境策略拒绝删除该生成文件，需人工删除`output/t04/real-entry.db`。原始Cookie值已从运行内存清除。
- T05使用新ticket复验：`/auth/me`返回200且字段形状正确；恶意Origin退出返回403并保留会话；按当前配置Origin退出返回204并清Cookie，另一标签旧Cookie随后返回401。未记录真实用户ID。

# 数据库迁移

迁移使用仓库根目录的 `alembic.ini`。数据库 URL 只从进程环境或本地未跟踪的 `.env` 读取，迁移日志不得输出完整连接串。

```powershell
.\.venv312\Scripts\python.exe -m alembic upgrade head
```

第一期迁移只向前新增。应用版本回滚不自动执行生产 `downgrade`，更不删除业务表或用户数据。

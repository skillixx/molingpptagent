"""启动当前分支的隔离验收 API：复用真实只读路由，不连接生产依赖。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/main_api'))
sys.path.insert(0, str(ROOT))

# 验收进程不加载根目录凭据，避免启动生产数据库、计费或远程 Agent 调用。
for key, value in {'APP_ENV': 'test', 'PERSISTENCE_ENABLED': 'false', 'SSO_ENABLED': 'false',
                   'BILLING_ENABLED': 'false', 'STORAGE_ENABLED': 'false', 'TASK_WORKER_ENABLED': 'false',
                   'RELEASE_CHANNEL': 'test', 'RELEASE_COMMIT': 'template-27-local-review'}.items():
    os.environ[key] = value
import dotenv
dotenv.load_dotenv = lambda *args, **kwargs: False
import main
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

app = FastAPI()


@app.middleware('http')
async def read_only(request, call_next):
    """只开放模板读取和固定数据预览，其他操作明确反馈且不进入真实处理链。"""
    if request.method != 'GET':
        return JSONResponse({'code': 'QA_READ_ONLY', 'message': '当前为固定数据验收预览，请使用编辑器本地导出。'}, status_code=405)
    path = request.url.path
    if path not in {'/auth/me', '/templates', '/qa/document', '/qa/info'} and not path.startswith('/data/'):
        return JSONResponse({'code': 'QA_READ_ONLY'}, status_code=404)
    return await call_next(request)


@app.get('/auth/me')
async def identity():
    # 明确为本机验收身份，不建立用户会话，也不写真实作品。
    return {'user_id': 1, 'app_id': 1, 'product_id': 1, 'mode': 'local-qa-fixture'}


@app.get('/qa/document')
async def document():
    return FileResponse(ROOT / 'doc/assets/template_27_qa/production-document.json', media_type='application/json')


@app.get('/qa/info')
async def info():
    return {'templateId': 'template_27', 'mode': 'local-fixed-data-preview', 'root': str(ROOT), 'productionWrites': False}


# 直接挂载当前分支真实 API，模板列表和资源加载不使用复制或模拟返回。
app.mount('/', main.app)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=6801, access_log=False)

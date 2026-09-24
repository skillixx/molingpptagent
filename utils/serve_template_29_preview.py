"""启动当前分支隔离验收 API，读取真实模板并将编辑稿保存在专用 SQLite。"""
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
                   'RELEASE_CHANNEL': 'test', 'RELEASE_COMMIT': 'template-29-local-review'}.items():
    os.environ[key] = value
import dotenv
dotenv.load_dotenv = lambda *args, **kwargs: False
import main
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from sqlalchemy import create_engine
from backend.main_api.api.presentations import create_presentations_router
from backend.main_api.core.identity import RequestPrincipal
from backend.main_api.models.base import Base
from backend.main_api.repositories.resources import PresentationRepository
from backend.main_api.services.presentations import PresentationService

app = FastAPI()
database = ROOT / 'doc/assets/template_29_qa/runtime-preview.sqlite'
engine = create_engine(f"sqlite:///{database.as_posix()}", connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)


def qa_principal():
    # 本机专用验收身份，不读取生产登录会话或真实作品。
    return RequestPrincipal(user_id=1, app_id=1, product_id=1, knowledge_subject='template29-local-qa')


app.include_router(create_presentations_router(
    service=PresentationService(PresentationRepository(engine), task_max_attempts=1, user_presentation_limit=None),
    principal_dependency=qa_principal,
    trusted_origins=('http://127.0.0.1:5781',), csrf_enabled=True))


@app.middleware('http')
async def isolated_scope(request, call_next):
    """只允许隔离作品草稿和编辑保存，其余写入拒绝，不创建真实生成任务。"""
    path = request.url.path
    local_save = (request.method == 'POST' and path == '/presentations/drafts') or (
        request.method == 'PATCH' and path.startswith('/presentations/') and path.count('/') == 2)
    if request.method != 'GET' and not local_save:
        return JSONResponse({'code': 'QA_LOCAL_ONLY', 'message': '验收环境仅支持本地草稿保存和编辑，不启动生成任务。'}, status_code=405)
    if path not in {'/auth/me', '/templates', '/qa/document', '/qa/info'} and not path.startswith(('/data/', '/presentations')):
        return JSONResponse({'code': 'QA_LOCAL_ONLY'}, status_code=404)
    return await call_next(request)


@app.get('/auth/me')
async def identity():
    # 明确为本机验收身份，不建立用户会话，也不写真实作品。
    return {'user_id': 1, 'app_id': 1, 'product_id': 1, 'mode': 'local-qa-fixture'}


@app.get('/qa/document')
async def document():
    return FileResponse(ROOT / 'doc/assets/template_29_qa/production-document.json', media_type='application/json')


@app.get('/qa/info')
async def info():
    return {'templateId': 'template_29', 'mode': 'local-fixed-data-preview', 'root': str(ROOT),
            'database': str(database), 'productionWrites': False, 'generationEnabled': False}


# 直接挂载当前分支真实 API，模板列表和资源加载不使用复制或模拟返回。
app.mount('/', main.app)

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=6803, access_log=False)

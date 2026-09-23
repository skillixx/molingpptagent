"""通过真实作品 API 和隔离 SQLite 验证完整编辑稿保存、重载和版本冲突。"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def document(raw):
    return {'schema_version': 1, 'slides': raw['slides'], 'theme': raw.get('theme', {}),
            'viewport_size': 1000, 'viewport_ratio': 0.5625}


def main():
    # 验证失败或异常退出时保留 RUNNING，不能沿用之前的 PASS 摘要。
    summary_path = ROOT / 'doc/assets/template_27_qa/persistence-summary.json'
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps({'status': 'RUNNING'}), encoding='utf-8')
    # 依赖加载也属于本次验证，失败时不能遗留旧成功状态。
    from fastapi import FastAPI, Header
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from backend.main_api.api.presentations import create_presentations_router
    from backend.main_api.core.identity import RequestPrincipal
    from backend.main_api.models.base import Base
    from backend.main_api.repositories.resources import PresentationRepository
    from backend.main_api.services.presentations import PresentationService
    source = ROOT / 'doc/assets/template_27_qa/production-document.json'
    edited_file = Path(sys.argv[1]).resolve()
    original = document(json.loads(source.read_text(encoding='utf-8')))
    edited = document(json.loads(edited_file.read_text(encoding='utf-8')))
    origin = 'http://template27.example.invalid'
    with tempfile.TemporaryDirectory(prefix='template27-save-') as temp:
        engine = create_engine(f"sqlite:///{(Path(temp) / 'save.db').as_posix()}", connect_args={'check_same_thread': False})
        Base.metadata.create_all(engine)

        def principal(x_test_user: int = Header(default=1001)):
            return RequestPrincipal(user_id=x_test_user, app_id=15, product_id=73, knowledge_subject=f'test:{x_test_user}')

        app = FastAPI()
        app.include_router(create_presentations_router(service=PresentationService(PresentationRepository(engine), task_max_attempts=1, user_presentation_limit=None),
                                                       principal_dependency=principal, trusted_origins=(origin,), csrf_enabled=True), prefix='/api')
        with TestClient(app) as client:
            created = client.post('/api/presentations/drafts', headers={'Origin': origin, 'Idempotency-Key': 'template27-draft'},
                                  json={'title': '唯美清新初稿', 'template_id': 'template_27', 'slides': original})
            if created.status_code != 201:
                raise RuntimeError(f'初稿保存失败: {created.status_code}')
            identity = created.json()['presentation']['id']
            saved = client.patch(f'/api/presentations/{identity}', headers={'Origin': origin},
                                 json={'base_version': 1, 'title': '唯美清新编辑保存验证', 'slides': edited})
            if saved.status_code != 200 or saved.json()['current_version'] != 2:
                raise RuntimeError(f'编辑稿保存失败: {saved.status_code}')
        # 关闭客户端和连接池后重新读取，排除仅在前端内存保留修改的假阳性。
        engine.dispose()
        with TestClient(app) as reopened:
            restored = reopened.get(f'/api/presentations/{identity}')
            if restored.status_code != 200 or restored.json()['slides'] != edited:
                raise RuntimeError('数据库重载内容与完整编辑稿不一致')
            conflict = reopened.patch(f'/api/presentations/{identity}', headers={'Origin': origin},
                                      json={'base_version': 1, 'title': '过期请求', 'slides': original})
            if conflict.status_code != 409 or reopened.get(f'/api/presentations/{identity}').json()['slides'] != edited:
                raise RuntimeError('过期版本覆盖了编辑稿')
            if reopened.get(f'/api/presentations/{identity}', headers={'X-Test-User': '2002'}).status_code != 404:
                raise RuntimeError('作品所有者隔离失败')
        engine.dispose()
    result = {'status': 'PASS', 'templateId': 'template_27', 'slides': len(edited['slides']), 'draftCreated': True,
              'editedDocumentPersisted': True, 'fullStateEqualAfterReopen': True, 'staleWriteRejected': True, 'ownerIsolation': True,
              'database': 'isolated-temporary-sqlite', 'productionWrites': False, 'sourceSha256': hashlib.sha256(edited_file.read_bytes()).hexdigest()}
    (ROOT / 'doc/assets/template_27_qa/persistence-summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

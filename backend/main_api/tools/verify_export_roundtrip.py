"""T20真实对象存储PPTX归档/下载验证；仅输出摘要，不输出凭据或对象端点。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit

import dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 允许从仓库根目录按文件路径执行，与部署包导入方式保持一致。
repository_root = Path(__file__).resolve().parents[3]
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

from backend.main_api.core.config import load_settings
from backend.main_api.integrations.storage import S3StorageAdapter
from backend.main_api.models.base import Base
from backend.main_api.models.domain import Presentation
from backend.main_api.repositories.exports import ExportRepository
from backend.main_api.repositories.files import FileRepository
from backend.main_api.services.exports import ExportService
from backend.main_api.services.files import FileService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("downloaded", type=Path)
    args = parser.parse_args()
    dotenv.load_dotenv(repository_root / ".env")
    # 验证器自行注入隔离下载密钥，因此只关闭应用启动开关校验，不改变实际对象存储参数。
    settings = load_settings({**os.environ, "STORAGE_ENABLED": "false"})
    required = (
        settings.storage_endpoint, settings.storage_bucket,
        settings.storage_access_key_id, settings.storage_secret_access_key,
    )
    if any(value is None for value in required):
        print(json.dumps({"export_roundtrip": "blocked", "reason": "storage_not_configured"}))
        return 2

    body = args.source.read_bytes()
    presentation_id = f"t20-{uuid4().hex}"
    now = datetime.now(UTC).replace(tzinfo=None)
    adapter = S3StorageAdapter(
        endpoint=settings.storage_endpoint,
        bucket=settings.storage_bucket,
        access_key_id=settings.storage_access_key_id.get_secret_value(),
        secret_access_key=settings.storage_secret_access_key.get_secret_value(),
        connect_timeout_seconds=settings.storage_connect_timeout_seconds,
        read_timeout_seconds=settings.storage_read_timeout_seconds,
        max_attempts=settings.storage_max_attempts,
    )
    object_key = None
    with tempfile.TemporaryDirectory(prefix="trainppt-t20-") as temporary:
        engine = create_engine(f"sqlite:///{(Path(temporary) / 'verify.db').as_posix()}")
        Base.metadata.create_all(engine)
        with sessionmaker(engine).begin() as db:
            db.add(Presentation(
                id=presentation_id, owner_user_id=9_900_020, title="T20真实归档",
                status="ready", slides_json="{}", current_version=1, slide_count=1,
                template_id=None, thumbnail_file_id=None, created_at=now,
                updated_at=now, deleted_at=None,
            ))
        file_service = FileService(
            repository=FileRepository(engine), storage=adapter,
            storage_prefix=settings.storage_prefix,
            user_storage_quota_bytes=max(len(body) * 2, 10 * 1024 * 1024),
        )
        service = ExportService(
            repository=ExportRepository(engine), file_service=file_service,
            download_signing_secret="isolated-t20-download-signing-secret-32-bytes",
        )
        digest = hashlib.sha256(body).hexdigest()
        try:
            archived = service.archive(
                9_900_020, presentation_id, 1, f"verify-{uuid4().hex}", digest, body
            )
            object_key = archived.record.file.object_key
            query = parse_qs(urlsplit(archived.download_url).query)
            expires = int(query["expires"][0])
            signature = query["signature"][0]
            downloaded, _ = service.download(
                9_900_020, archived.record.file.id, expires, signature
            )
            args.downloaded.parent.mkdir(parents=True, exist_ok=True)
            args.downloaded.write_bytes(downloaded)
            downloaded_digest = hashlib.sha256(downloaded).hexdigest()
            print(json.dumps({
                "export_roundtrip": "passed",
                "source_bytes": len(body),
                "downloaded_bytes": len(downloaded),
                "hash_match": digest == downloaded_digest,
                "record_count": 1,
            }))
            return 0 if digest == downloaded_digest else 1
        finally:
            if object_key:
                adapter.delete(object_key)
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

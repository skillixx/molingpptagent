"""T19 真实对象存储最小写读删；输出只含布尔结果，不含配置与对象键。"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from uuid import uuid4

import dotenv


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main_api.core.config import load_settings
from backend.main_api.integrations.storage import S3StorageAdapter, StorageError


def main() -> int:
    dotenv.load_dotenv(ROOT / ".env")
    settings = load_settings()
    required = (
        settings.storage_endpoint,
        settings.storage_bucket,
        settings.storage_access_key_id,
        settings.storage_secret_access_key,
    )
    if any(value is None for value in required):
        print("storage_roundtrip=not_configured")
        return 2
    assert settings.storage_endpoint is not None
    assert settings.storage_bucket is not None
    assert settings.storage_access_key_id is not None
    assert settings.storage_secret_access_key is not None
    adapter = S3StorageAdapter(
        endpoint=settings.storage_endpoint,
        bucket=settings.storage_bucket,
        access_key_id=settings.storage_access_key_id.get_secret_value(),
        secret_access_key=settings.storage_secret_access_key.get_secret_value(),
        connect_timeout_seconds=settings.storage_connect_timeout_seconds,
        read_timeout_seconds=settings.storage_read_timeout_seconds,
        max_attempts=settings.storage_max_attempts,
    )
    body = b"TrainPPTAgent T19 isolated storage verification\n"
    digest = hashlib.sha256(body).hexdigest()
    key = f"{settings.storage_prefix.strip('/')}/verification/t19/{uuid4().hex}"
    hash_match = False
    deleted = False
    failed = False
    try:
        adapter.put(
            object_key=key,
            body=body,
            mime_type="text/plain",
            sha256=digest,
        )
        read_back = adapter.get(key, expected_size=len(body))
        hash_match = hashlib.sha256(read_back).hexdigest() == digest
    except StorageError:
        failed = True
    finally:
        # put可能已在服务端成功但响应丢失；无论后续哪一步失败都必须用同一隔离键尽力清理。
        try:
            adapter.delete(key)
            deleted = not adapter.exists(key)
        except StorageError:
            deleted = False
    passed = not failed and hash_match and deleted
    print(f"storage_roundtrip={'passed' if passed else 'failed'}")
    print(f"hash_match={str(hash_match).lower()}")
    print(f"deleted={str(deleted).lower()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

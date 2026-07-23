"""T19 Storage Adapter、文件归属与配额公开行为测试。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import secrets
import gzip
import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from botocore.exceptions import ReadTimeoutError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.main_api.integrations.storage import S3StorageAdapter, StorageError
from backend.main_api.models.base import Base
from backend.main_api.models.domain import (
    OwnerStorageUsage,
    Presentation,
    PresentationVersion,
    StoredFile,
)
from backend.main_api.repositories.files import FileRepository, FileSchemaError
from backend.main_api.repositories.resources import PresentationRepository
from backend.main_api.schemas.presentations import CreateCheckpointRequest
from backend.main_api.services.files import FileService, FileServiceError
from backend.main_api.services.presentations import PresentationService


NOW = datetime(2026, 7, 23, 8, 0, 0)
PDF = b"%PDF-1.7\nT19 isolated fixture\n%%EOF"


class MemoryStorage:
    """测试存储只记录对象键和字节，不模拟真实云厂商成功。"""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str, str]] = {}
        self.put_calls = 0
        self.fail_put = False
        self.fail_delete = False

    def put(self, *, object_key: str, body: bytes, mime_type: str, sha256: str) -> None:
        self.put_calls += 1
        if self.fail_put:
            raise StorageError("对象存储暂时不可用")
        self.objects[object_key] = (body, mime_type, sha256)

    def get(self, object_key: str, *, expected_size: int) -> bytes:
        try:
            body = self.objects[object_key][0]
        except KeyError:
            raise StorageError("对象不存在") from None
        if len(body) != expected_size:
            raise StorageError("对象大小不匹配")
        return body

    def delete(self, object_key: str) -> None:
        if self.fail_delete:
            raise StorageError("对象存储暂时不可用")
        self.objects.pop(object_key, None)


def _service(tmp_path: Path, *, quota: int = 1024):
    tmp_path.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'files.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    repository = FileRepository(engine)
    with sessionmaker(engine).begin() as db:
        db.add(Presentation(
            id="presentation-safe", owner_user_id=1001, title="文件作品", status="ready",
            slides_json="{}", current_version=1, slide_count=0, template_id=None,
            thumbnail_file_id=None, created_at=NOW, updated_at=NOW, deleted_at=None,
        ))
    storage = MemoryStorage()
    service = FileService(
        repository=repository,
        storage=storage,
        storage_prefix="trainppt-test",
        user_storage_quota_bytes=quota,
        id_factory=lambda: "file-safe",
        now_factory=lambda: NOW,
    )
    return engine, repository, storage, service


def test_upload_uses_server_key_validates_signature_and_is_owner_scoped(tmp_path: Path) -> None:
    engine, repository, storage, service = _service(tmp_path)
    try:
        stored = service.store(
            1001, "presentation-safe", purpose="source", mime_type="application/pdf", body=PDF
        )
        assert stored.object_key.startswith("trainppt-test/")
        assert ".." not in stored.object_key and "\\" not in stored.object_key
        assert service.read(1001, stored.id) == PDF
        with pytest.raises(FileServiceError) as denied:
            service.read(2002, stored.id)
        assert denied.value.code == "FILE_NOT_FOUND"
        assert repository.used_bytes(1001) == len(PDF)

        with pytest.raises(FileServiceError) as invalid:
            service.store(
                1001, "presentation-safe", purpose="source",
                mime_type="application/pdf", body=b"not a pdf",
            )
        assert invalid.value.code == "FILE_SIGNATURE_INVALID"
        with pytest.raises(FileServiceError) as traversal:
            service.store(
                1001, "../escape", purpose="source", mime_type="application/pdf", body=PDF
            )
        assert traversal.value.code == "FILE_OWNER_NOT_FOUND"
        assert storage.put_calls == 1
        with pytest.raises(FileServiceError) as fake_zip:
            service.store(
                1001, "presentation-safe", purpose="pptx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
                body=b"PK\x03\x04not-a-real-pptx",
            )
        assert fake_zip.value.code == "FILE_SIGNATURE_INVALID"
    finally:
        engine.dispose()


def test_same_content_reuses_file_and_does_not_double_charge_quota(tmp_path: Path) -> None:
    engine, repository, storage, service = _service(tmp_path)
    try:
        first = service.store(
            1001, "presentation-safe", purpose="source", mime_type="application/pdf", body=PDF
        )
        second = service.store(
            1001, "presentation-safe", purpose="source", mime_type="application/pdf", body=PDF
        )
        assert second.id == first.id
        assert storage.put_calls == 1
        assert repository.used_bytes(1001) == len(PDF)
    finally:
        engine.dispose()


def test_quota_and_storage_failure_never_leave_active_file_or_reserved_bytes(tmp_path: Path) -> None:
    engine, repository, storage, service = _service(tmp_path, quota=len(PDF))
    try:
        service.store(
            1001, "presentation-safe", purpose="source", mime_type="application/pdf", body=PDF
        )
        with pytest.raises(FileServiceError) as full:
            service.store(
                1001, "presentation-safe", purpose="attachment",
                mime_type="text/plain", body=b"x",
            )
        assert full.value.code == "STORAGE_QUOTA_EXCEEDED"
        assert storage.put_calls == 1

        other_engine, other_repository, other_storage, other_service = _service(
            tmp_path / "failed", quota=1024
        )
        other_storage.fail_put = True
        try:
            with pytest.raises(FileServiceError) as unavailable:
                other_service.store(
                    1001, "presentation-safe", purpose="source",
                    mime_type="application/pdf", body=PDF,
                )
            assert unavailable.value.code == "STORAGE_UNAVAILABLE"
            assert other_repository.used_bytes(1001) == 0
            assert other_repository.active_count(1001) == 0
        finally:
            other_engine.dispose()
    finally:
        engine.dispose()


def test_large_checkpoint_round_trips_through_storage_adapter(tmp_path: Path) -> None:
    engine, repository, storage, file_service = _service(tmp_path, quota=1024 * 1024)
    try:
        with sessionmaker(engine).begin() as db:
            presentation = db.scalar(select(Presentation))
            presentation.slides_json = (
                '{"schema_version":1,"slides":[{"id":"1","elements":[],"remark":"'
                + secrets.token_hex(2048)
                + '"}]}'
            )
        service = PresentationService(
            PresentationRepository(engine),
            task_max_attempts=3,
            user_presentation_limit=100,
            checkpoint_inline_max_bytes=64,
            file_service=file_service,
            id_factory=lambda: "checkpoint-safe",
            now_factory=lambda: NOW,
        )
        created = service.create_checkpoint(
            1001,
            "presentation-safe",
            CreateCheckpointRequest(base_version=1, reason="manual"),
        )
        assert created.uncompressed_bytes > 64
        assert storage.put_calls == 1
        assert repository.active_count(1001) == 1
        listed = service.list_checkpoints(1001, "presentation-safe")
        assert listed[0].content_sha256 == created.content_sha256
    finally:
        engine.dispose()


def test_concurrent_uploads_share_one_owner_quota_lock(tmp_path: Path) -> None:
    engine, repository, storage, _ = _service(tmp_path, quota=len(PDF))
    with sessionmaker(engine).begin() as db:
        db.add(Presentation(
            id="presentation-two", owner_user_id=1001, title="第二作品", status="ready",
            slides_json="{}", current_version=1, slide_count=0, template_id=None,
            thumbnail_file_id=None, created_at=NOW, updated_at=NOW, deleted_at=None,
        ))
    service = FileService(
        repository=repository,
        storage=storage,
        storage_prefix="trainppt-test",
        user_storage_quota_bytes=len(PDF),
        now_factory=lambda: NOW,
    )

    def upload(presentation_id: str) -> str:
        try:
            service.store(
                1001, presentation_id, purpose="source", mime_type="application/pdf", body=PDF
            )
            return "stored"
        except FileServiceError as exc:
            return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(upload, ("presentation-safe", "presentation-two")))
        assert sorted(results) == ["STORAGE_QUOTA_EXCEEDED", "stored"]
        assert repository.used_bytes(1001) == len(PDF)
        assert repository.active_count(1001) == 1
    finally:
        engine.dispose()


def test_storage_schema_gate_fails_before_first_upload(tmp_path: Path) -> None:
    engine, repository, _, _ = _service(tmp_path)
    try:
        OwnerStorageUsage.__table__.drop(engine)
        with pytest.raises(FileSchemaError):
            repository.ensure_schema()
    finally:
        engine.dispose()


def test_crash_recovery_deletes_stale_object_before_releasing_quota(tmp_path: Path) -> None:
    engine, repository, storage, service = _service(tmp_path)
    digest = "a" * 64
    uploading = StoredFile(
        id="stale-file", owner_user_id=1001, presentation_id="presentation-safe",
        purpose="source", object_key="trainppt-test/stale/object",
        mime_type="application/pdf", size_bytes=9, sha256=digest, status="uploading",
        created_at=NOW, updated_at=NOW, deleted_at=None,
    )
    try:
        repository.reserve(uploading, user_storage_quota_bytes=1024)
        storage.objects[uploading.object_key] = (b"orphaned", "application/pdf", digest)
        assert service.recover_stale_uploads(NOW, limit=10) == 1
        assert uploading.object_key not in storage.objects
        assert repository.used_bytes(1001) == 0
        assert repository.active_count(1001) == 0
    finally:
        engine.dispose()


def test_delete_failure_keeps_upload_index_and_quota_until_restart_recovery(tmp_path: Path) -> None:
    engine, repository, storage, service = _service(tmp_path)
    storage.fail_put = True
    storage.fail_delete = True
    try:
        with pytest.raises(FileServiceError):
            service.store(
                1001, "presentation-safe", purpose="source",
                mime_type="application/pdf", body=PDF,
            )
        assert repository.used_bytes(1001) == len(PDF)
        storage.fail_put = False
        storage.fail_delete = False
        # 新服务实例模拟应用重启；陈旧上传删除成功后才释放占额。
        restarted = FileService(
            repository=repository, storage=storage, storage_prefix="trainppt-test",
            user_storage_quota_bytes=1024, now_factory=lambda: NOW,
        )
        assert restarted.recover_stale_uploads(NOW, limit=10) == 1
        assert repository.used_bytes(1001) == 0
    finally:
        engine.dispose()


def test_unreferenced_checkpoint_gc_preserves_referenced_objects(tmp_path: Path) -> None:
    engine, repository, storage, service = _service(tmp_path)
    compressed = gzip.compress(b'{"schema_version":1,"slides":[]}', mtime=0)
    try:
        orphan = service.store(
            1001, "presentation-safe", purpose="checkpoint",
            mime_type="application/gzip", body=compressed,
        )
        assert service.cleanup_unreferenced_checkpoints(NOW, limit=10) == 1
        assert orphan.object_key not in storage.objects
        assert repository.used_bytes(1001) == 0

        referenced = service.store(
            1001, "presentation-safe", purpose="checkpoint",
            mime_type="application/gzip", body=compressed,
        )
        with sessionmaker(engine).begin() as db:
            db.add(PresentationVersion(
                id="version-ref", presentation_id="presentation-safe", version=1,
                slides_json=(
                    '{"format":"storage-gzip-v1","file_id":"' + referenced.id + '"}'
                ),
                reason="manual", created_by=1001, created_at=NOW,
            ))
        assert service.cleanup_unreferenced_checkpoints(NOW, limit=10) == 0
        assert referenced.object_key in storage.objects
        assert repository.used_bytes(1001) == len(compressed)
    finally:
        engine.dispose()


def test_s3_timeout_is_bounded_and_mapped_without_endpoint_leak(monkeypatch) -> None:
    captured = {}

    class TimeoutClient:
        def put_object(self, **kwargs):
            raise ReadTimeoutError(endpoint_url="https://secret-storage.example")

        def head_bucket(self, **kwargs):
            raise ReadTimeoutError(endpoint_url="https://secret-storage.example")

    def fake_client(*args, **kwargs):
        captured["config"] = kwargs["config"]
        return TimeoutClient()

    monkeypatch.setattr("backend.main_api.integrations.storage.boto3.client", fake_client)
    adapter = S3StorageAdapter(
        endpoint="https://storage.example.test",
        bucket="test",
        access_key_id="fake-access",
        secret_access_key="fake-secret",
        connect_timeout_seconds=2,
        read_timeout_seconds=7,
        max_attempts=2,
    )
    with pytest.raises(StorageError) as exc_info:
        adapter.put(
            object_key="safe/t19/object",
            body=PDF,
            mime_type="application/pdf",
            sha256=hashlib.sha256(PDF).hexdigest(),
        )
    assert captured["config"].connect_timeout == 2
    assert captured["config"].read_timeout == 7
    assert "secret-storage" not in str(exc_info.value)
    with pytest.raises(StorageError) as health_error:
        adapter.check()
    assert "secret-storage" not in str(health_error.value)


def test_checkpoint_pruning_deletes_only_unreferenced_storage_objects(tmp_path: Path) -> None:
    engine, repository, storage, _ = _service(tmp_path, quota=1024 * 1024)
    file_service = FileService(
        repository=repository, storage=storage, storage_prefix="trainppt-test",
        user_storage_quota_bytes=1024 * 1024, now_factory=lambda: NOW,
    )
    checkpoint_ids = iter(("checkpoint-1", "checkpoint-2", "checkpoint-3"))
    service = PresentationService(
        PresentationRepository(engine), task_max_attempts=3,
        user_presentation_limit=100, checkpoint_max_count=2,
        checkpoint_inline_max_bytes=64, file_service=file_service,
        storage_upload_stale_seconds=0,
        id_factory=lambda: next(checkpoint_ids), now_factory=lambda: NOW,
    )
    try:
        for version in (1, 2, 3):
            with sessionmaker(engine).begin() as db:
                presentation = db.scalar(select(Presentation))
                presentation.current_version = version
                presentation.slides_json = (
                    '{"schema_version":1,"slides":[{"id":"s","elements":[],"remark":"'
                    + secrets.token_hex(1024)
                    + '"}]}'
                )
            service.create_checkpoint(
                1001, "presentation-safe",
                CreateCheckpointRequest(base_version=version, reason="manual"),
            )
        assert repository.active_count(1001) == 3
        service.prune_checkpoints(1001, "presentation-safe")
        assert len(service.list_checkpoints(1001, "presentation-safe")) == 2
        assert repository.active_count(1001) == 2
        assert len(storage.objects) == 2
    finally:
        engine.dispose()


def test_stale_upload_claim_cannot_delete_file_activated_by_original_uploader(tmp_path: Path) -> None:
    engine, repository, storage, _ = _service(tmp_path)
    uploading = StoredFile(
        id="race-file", owner_user_id=1001, presentation_id="presentation-safe",
        purpose="source", object_key="trainppt-test/race/object",
        mime_type="application/pdf", size_bytes=len(PDF),
        sha256=hashlib.sha256(PDF).hexdigest(), status="uploading",
        created_at=NOW, updated_at=NOW, deleted_at=None,
    )
    try:
        repository.reserve(uploading, user_storage_quota_bytes=1024)
        candidates = repository.list_stale_uploads(NOW, limit=10)
        assert candidates[0].id == uploading.id
        repository.activate(1001, uploading.id, NOW + timedelta(seconds=1))
        assert repository.claim_stale_upload(
            uploading.id, stale_before=NOW, now=NOW + timedelta(seconds=2)
        ) is None
        assert repository.get_active(1001, uploading.id) is not None
    finally:
        engine.dispose()


def test_reusing_old_checkpoint_refreshes_lease_before_gc_claim(tmp_path: Path) -> None:
    engine, repository, storage, service = _service(tmp_path)
    compressed = gzip.compress(b'{"schema_version":1,"slides":[]}', mtime=0)
    try:
        first = service.store(
            1001, "presentation-safe", purpose="checkpoint",
            mime_type="application/gzip", body=compressed,
        )
        later = NOW + timedelta(seconds=1000)
        reused_service = FileService(
            repository=repository, storage=storage, storage_prefix="trainppt-test",
            user_storage_quota_bytes=1024, now_factory=lambda: later,
        )
        assert reused_service.store(
            1001, "presentation-safe", purpose="checkpoint",
            mime_type="application/gzip", body=compressed,
        ).id == first.id
        assert repository.claim_unreferenced_checkpoint(
            first.id,
            stale_before=NOW + timedelta(seconds=500),
            now=later,
        ) is None
        assert first.object_key in storage.objects
    finally:
        engine.dispose()


def test_reuse_touch_loser_never_returns_cached_active_file(tmp_path: Path, monkeypatch) -> None:
    engine, repository, storage, service = _service(tmp_path)
    try:
        service.store(
            1001, "presentation-safe", purpose="source",
            mime_type="application/pdf", body=PDF,
        )
        # 模拟GC已先赢得active→deleting，touch条件更新受影响行数为0。
        monkeypatch.setattr(repository, "_touch_active", lambda db, file_id, now: False)
        with pytest.raises(FileServiceError) as exc_info:
            service.store(
                1001, "presentation-safe", purpose="source",
                mime_type="application/pdf", body=PDF,
            )
        assert exc_info.value.code == "FILE_UPLOAD_IN_PROGRESS"
        assert storage.put_calls == 1
    finally:
        engine.dispose()


def test_deleting_crash_replays_delete_and_releases_quota_on_restart(tmp_path: Path) -> None:
    engine, repository, storage, service = _service(tmp_path)
    compressed = gzip.compress(b'{"schema_version":1,"slides":[]}', mtime=0)
    try:
        stored = service.store(
            1001, "presentation-safe", purpose="checkpoint",
            mime_type="application/gzip", body=compressed,
        )
        claimed = repository.claim_unreferenced_checkpoint(
            stored.id, stale_before=NOW, now=NOW
        )
        assert claimed is not None
        storage.delete(stored.object_key)
        assert repository.used_bytes(1001) == len(compressed)
        # 模拟物理删除成功后进程崩溃；新实例按同一键幂等删除并提交本地释放。
        assert service.recover_stale_deletions(NOW, limit=10) == 1
        assert repository.used_bytes(1001) == 0
        assert repository.active_count(1001) == 0
    finally:
        engine.dispose()

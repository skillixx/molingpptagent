"""T20 PPTX归档、历史下载和owner隔离公开契约测试。"""

from __future__ import annotations

import hashlib
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.main_api.api.exports import create_exports_router
from backend.main_api.core.identity import RequestPrincipal
from backend.main_api.models.base import Base
from backend.main_api.models.domain import Presentation, PresentationExport
from backend.main_api.repositories.exports import ExportNotFound, ExportRepository
from backend.main_api.repositories.files import FileRepository
from backend.main_api.services.exports import ExportService, ExportServiceError
from backend.main_api.services.files import FileService


NOW = datetime(2026, 7, 23, 9, 0, 0)
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class MemoryStorage:
    """隔离测试只验证业务契约；真实S3写读删由T19/T20独立脚本验证。"""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_calls = 0

    def put(self, *, object_key: str, body: bytes, mime_type: str, sha256: str) -> None:
        self.put_calls += 1
        self.objects[object_key] = body

    def get(self, object_key: str, *, expected_size: int) -> bytes:
        return self.objects[object_key]

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


def _pptx() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("ppt/presentation.xml", "<p:presentation/>")
        archive.writestr("ppt/slides/slide1.xml", "<p:sld/>")
    return output.getvalue()


PPTX = _pptx()


@pytest.fixture()
def export_api(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'exports.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with sessionmaker(engine).begin() as db:
        db.add(Presentation(
            id="presentation-1", owner_user_id=1001, title="季度/汇报", status="ready",
            slides_json="{}", current_version=3, slide_count=1, template_id=None,
            thumbnail_file_id=None, created_at=NOW, updated_at=NOW, deleted_at=None,
        ))

    storage = MemoryStorage()
    file_service = FileService(
        repository=FileRepository(engine), storage=storage,
        storage_prefix="trainppt-test", user_storage_quota_bytes=10 * 1024 * 1024,
        now_factory=lambda: NOW,
    )
    service = ExportService(
        repository=ExportRepository(engine), file_service=file_service,
        download_signing_secret="t20-download-signing-secret-32-bytes",
        download_url_ttl_seconds=60, now_factory=lambda: NOW,
    )

    def principal(x_test_user: int = Header(default=1001)) -> RequestPrincipal:
        return RequestPrincipal(
            user_id=x_test_user, app_id=15, product_id=73,
            knowledge_subject=f"moling:test:15:{x_test_user}",
        )

    app = FastAPI()
    app.include_router(create_exports_router(
        service=service, principal_dependency=principal,
        trusted_origins=("https://trainppt.example.com",), csrf_enabled=True,
    ), prefix="/api")
    client = TestClient(app)
    yield client, engine, storage
    client.close()
    engine.dispose()


def _archive(client: TestClient, *, key: str = "export-request-1", user: int = 1001):
    body = PPTX
    return client.post(
        "/api/presentations/presentation-1/exports/pptx",
        headers={
            "Origin": "https://trainppt.example.com",
            "Idempotency-Key": key,
            "X-Test-User": str(user),
            "X-Presentation-Version": "3",
            "X-Content-SHA256": hashlib.sha256(body).hexdigest(),
            "Content-Type": PPTX_MIME,
        },
        content=body,
    )


def test_same_pptx_request_is_idempotent_and_history_download_is_byte_identical(export_api) -> None:
    client, engine, storage = export_api
    original = PPTX
    first = _archive(client)
    retry = _archive(client)

    assert first.status_code == retry.status_code == 201
    assert first.json()["sha256"] == hashlib.sha256(original).hexdigest()
    assert retry.json()["id"] == first.json()["id"]
    assert retry.json()["reused"] is True
    assert storage.put_calls == 1
    with sessionmaker(engine)() as db:
        assert db.scalar(select(func.count()).select_from(PresentationExport)) == 1

    history = client.get("/api/presentations/presentation-1/exports")
    assert history.status_code == 200
    download = client.get(history.json()["items"][0]["download_url"])
    assert download.status_code == 200
    assert download.content == original
    assert hashlib.sha256(download.content).hexdigest() == first.json()["sha256"]
    disposition = download.headers["content-disposition"]
    assert 'filename="presentation-v3.pptx"' in disposition
    assert "%E5%AD%A3%E5%BA%A6_%E6%B1%87%E6%8A%A5-v3.pptx" in disposition


def test_cross_user_expired_url_and_soft_deleted_presentation_cannot_download(export_api) -> None:
    client, engine, _ = export_api
    archived = _archive(client).json()
    url = archived["download_url"]

    assert client.get(url, headers={"X-Test-User": "2002"}).status_code == 404
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    query["expires"] = ["1"]
    expired_url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment)
    )
    expired = client.get(expired_url)
    assert expired.status_code == 410
    assert expired.json()["code"] == "DOWNLOAD_URL_EXPIRED"

    with sessionmaker(engine).begin() as db:
        presentation = db.get(Presentation, "presentation-1")
        presentation.deleted_at = NOW
    assert client.get(url).status_code == 404


def test_hash_mismatch_and_same_key_with_changed_payload_are_rejected(export_api) -> None:
    client, _, _ = export_api
    assert _archive(client).status_code == 201
    body = _pptx() + b"changed"
    changed = client.post(
        "/api/presentations/presentation-1/exports/pptx",
        headers={
            "Origin": "https://trainppt.example.com",
            "Idempotency-Key": "export-request-1",
            "X-Presentation-Version": "3",
            "X-Content-SHA256": hashlib.sha256(body).hexdigest(),
            "Content-Type": PPTX_MIME,
        },
        content=body,
    )
    assert changed.status_code == 409
    bad_hash = _archive(client, key="bad-hash")
    # 独立构造错误摘要，确保服务端不信任浏览器声明。
    bad_hash = client.post(
        "/api/presentations/presentation-1/exports/pptx",
        headers={
            "Origin": "https://trainppt.example.com",
            "Idempotency-Key": "bad-hash",
            "X-Presentation-Version": "3",
            "X-Content-SHA256": "0" * 64,
            "Content-Type": PPTX_MIME,
        }, content=PPTX,
    )
    assert bad_hash.status_code == 400


def test_thumbnail_updates_owner_presentation_and_rejects_untrusted_origin(export_api) -> None:
    client, engine, _ = export_api
    png = b"\x89PNG\r\n\x1a\nT20-thumbnail"
    headers = {
        "Origin": "https://trainppt.example.com",
        "Content-Type": "image/png",
        "X-Content-SHA256": hashlib.sha256(png).hexdigest(),
    }
    stored = client.put("/api/presentations/presentation-1/thumbnail", headers=headers, content=png)
    assert stored.status_code == 200
    with sessionmaker(engine)() as db:
        presentation = db.get(Presentation, "presentation-1")
        assert presentation.thumbnail_file_id == stored.json()["file_id"]

    rejected = client.put(
        "/api/presentations/presentation-1/thumbnail",
        headers={**headers, "Origin": "https://evil.example"}, content=png,
    )
    assert rejected.status_code == 403


def test_version_conflict_compensates_object_and_quota(export_api) -> None:
    client, engine, storage = export_api
    response = client.post(
        "/api/presentations/presentation-1/exports/pptx",
        headers={
            "Origin": "https://trainppt.example.com",
            "Idempotency-Key": "stale-version",
            "X-Presentation-Version": "2",
            "X-Content-SHA256": hashlib.sha256(PPTX).hexdigest(),
            "Content-Type": PPTX_MIME,
        }, content=PPTX,
    )
    assert response.status_code == 409
    assert storage.objects == {}
    assert FileRepository(engine).used_bytes(1001) == 0


def test_replacing_thumbnail_deletes_old_unreferenced_object_and_releases_quota(export_api) -> None:
    client, engine, storage = export_api
    first = b"\x89PNG\r\n\x1a\nfirst-thumbnail"
    second = b"\x89PNG\r\n\x1a\nsecond-thumbnail"
    for body in (first, second):
        response = client.put(
            "/api/presentations/presentation-1/thumbnail",
            headers={
                "Origin": "https://trainppt.example.com", "Content-Type": "image/png",
                "X-Content-SHA256": hashlib.sha256(body).hexdigest(),
            }, content=body,
        )
        assert response.status_code == 200
    assert len(storage.objects) == 1
    assert FileRepository(engine).used_bytes(1001) == len(second)


def test_export_openapi_freezes_success_and_error_contracts(export_api) -> None:
    client, _, _ = export_api
    schema = client.app.openapi()
    archive = schema["paths"]["/api/presentations/{presentation_id}/exports/pptx"]["post"]
    history = schema["paths"]["/api/presentations/{presentation_id}/exports"]["get"]
    download = schema["paths"]["/api/files/{file_id}/download"]["get"]
    assert {"201", "400", "403", "404", "409", "410", "413", "415", "503"} <= set(archive["responses"])
    assert PPTX_MIME in archive["requestBody"]["content"]
    thumbnail = schema["paths"]["/api/presentations/{presentation_id}/thumbnail"]["put"]
    assert "image/png" in thumbnail["requestBody"]["content"]
    assert "415" in thumbnail["responses"]
    assert history["responses"]["200"]["content"]["application/json"]["schema"]
    assert {"200", "400", "404", "410", "503"} <= set(download["responses"])


def test_concurrent_idempotency_loser_cleans_its_different_presentation_file(export_api, monkeypatch) -> None:
    client, engine, storage = export_api
    assert _archive(client).status_code == 201
    with sessionmaker(engine).begin() as db:
        db.add(Presentation(
            id="presentation-2", owner_user_id=1001, title="第二作品", status="ready",
            slides_json="{}", current_version=3, slide_count=1, template_id=None,
            thumbnail_file_id=None, created_at=NOW, updated_at=NOW, deleted_at=None,
        ))
    repository = ExportRepository(engine)
    winner = repository.get_request(1001, "export-request-1")
    assert winner is not None
    file_service = FileService(
        repository=FileRepository(engine), storage=storage,
        storage_prefix="trainppt-test", user_storage_quota_bytes=10 * 1024 * 1024,
        now_factory=lambda: NOW,
    )
    service = ExportService(
        repository=repository, file_service=file_service,
        download_signing_secret="t20-download-signing-secret-32-bytes",
        now_factory=lambda: NOW,
    )
    monkeypatch.setattr(repository, "get_request", lambda owner, request: None)
    monkeypatch.setattr(repository, "create", lambda record: (winner, True))
    with pytest.raises(ExportServiceError) as conflict:
        service.archive(
            1001, "presentation-2", 3, "export-request-1",
            hashlib.sha256(PPTX).hexdigest(), PPTX,
        )
    assert getattr(conflict.value, "code", None) == "EXPORT_IDEMPOTENCY_CONFLICT"
    assert len(storage.objects) == 1
    assert FileRepository(engine).used_bytes(1001) == len(PPTX)


def test_thumbnail_commit_failure_cleans_new_file(export_api, monkeypatch) -> None:
    _, engine, storage = export_api
    repository = ExportRepository(engine)
    file_service = FileService(
        repository=FileRepository(engine), storage=storage,
        storage_prefix="trainppt-test", user_storage_quota_bytes=10 * 1024 * 1024,
        now_factory=lambda: NOW,
    )
    service = ExportService(
        repository=repository, file_service=file_service,
        download_signing_secret="t20-download-signing-secret-32-bytes",
        now_factory=lambda: NOW,
    )
    monkeypatch.setattr(repository, "set_thumbnail", lambda *args: (_ for _ in ()).throw(ExportNotFound()))
    png = b"\x89PNG\r\n\x1a\ncommit-race"
    with pytest.raises(ExportServiceError) as missing:
        service.store_thumbnail(1001, "presentation-1", hashlib.sha256(png).hexdigest(), png)
    assert getattr(missing.value, "code", None) == "EXPORT_NOT_FOUND"
    assert storage.objects == {}
    assert FileRepository(engine).used_bytes(1001) == 0

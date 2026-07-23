"""T07 旧接口服务端身份与 PersonalDB 复合命名空间测试。"""

from __future__ import annotations

from datetime import datetime
import importlib
import sys
from pathlib import Path

import pytest
import logging
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.main_api.core.identity import (
    LegacyIdentityResolver,
    RequestPrincipal,
    generation_context_id,
    knowledge_subject,
)
from backend.main_api.models.auth import AppSession
from backend.personaldb.namespace import collection_name_for_subject, subject_log_tag
from backend.personaldb.security import safe_upload_filename


class FakeAuthService:
    """只接受测试Cookie，并返回服务端持久化的可信身份。"""

    def resolve_session(self, raw_token: str | None) -> AppSession | None:
        if raw_token != "valid-cookie":
            return None
        now = datetime(2026, 7, 23)
        return AppSession(
            id="hash",
            user_id=1001,
            app_id=15,
            product_id=73,
            created_at=now,
            expires_at=now,
            last_seen_at=now,
        )


def _request(*, cookie: str | None = None, query: str = "") -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", f"trainppt_session={cookie}".encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/tools/aippt",
            "query_string": query.encode(),
            "headers": headers,
        }
    )


def _load_main_module():
    """兼容主模块保留的脚本式绝对导入。"""
    module_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(module_dir))
    try:
        return importlib.import_module("backend.main_api.main")
    finally:
        sys.path.remove(str(module_dir))


def test_sso_resolver_ignores_forged_user_id_and_builds_composite_subject() -> None:
    """浏览器伪造的 owner 参数不能覆盖服务端 Session 身份。"""
    resolver = LegacyIdentityResolver(
        sso_enabled=True,
        app_env="production",
        cookie_name="trainppt_session",
        auth_service=FakeAuthService(),
    )

    principal = resolver.resolve(_request(cookie="valid-cookie", query="user_id=999999"))

    assert principal.user_id == 1001
    assert principal.app_id == 15
    assert principal.knowledge_subject == "moling:production:15:1001"
    assert "999999" not in principal.knowledge_subject


def test_sso_resolver_rejects_missing_or_expired_session() -> None:
    """SSO 模式旧接口不得退回客户端 user_id 或匿名共享空间。"""
    resolver = LegacyIdentityResolver(
        sso_enabled=True,
        app_env="production",
        cookie_name="trainppt_session",
        auth_service=FakeAuthService(),
    )
    with pytest.raises(HTTPException) as exc_info:
        resolver.resolve(_request(query="user_id=1001"))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "AUTH_SESSION_EXPIRED"


def test_local_mode_uses_fixed_development_subject_not_session_id() -> None:
    """关闭SSO时保留单机旧流程，但随机 sessionId 只能作为生成上下文。"""
    resolver = LegacyIdentityResolver(
        sso_enabled=False,
        app_env="development",
        cookie_name="trainppt_session",
        auth_service=None,
    )
    principal = resolver.resolve(_request(query="user_id=8&sessionId=random-client-value"))
    assert principal.user_id == 0
    assert principal.knowledge_subject == "local:development:trainppt"
    assert "random-client-value" not in principal.knowledge_subject


def test_session_id_is_bounded_generation_context_only() -> None:
    """合法旧值可保持生成连续性，路径/控制字符和超长值不能进入 Agent 上下文。"""
    assert generation_context_id("nanoid_123", "server-random") == "nanoid_123"
    assert generation_context_id("../foreign-user", "server-random") == "server-random"
    assert generation_context_id("x" * 129, "server-random") == "server-random"


def test_namespace_separates_environment_app_and_user_and_keeps_legacy_numeric_names() -> None:
    """同名文件只有在相同复合主体内相遇，环境、应用或用户变化都会换集合。"""
    subjects = {
        knowledge_subject("production", 15, 1001),
        knowledge_subject("staging", 15, 1001),
        knowledge_subject("production", 16, 1001),
        knowledge_subject("production", 15, 1002),
    }
    collections = {collection_name_for_subject(subject) for subject in subjects}
    assert len(collections) == 4
    assert all(name.startswith("subject_") and len(name) == 40 for name in collections)
    assert collection_name_for_subject(123456) == "user_123456"
    assert "1001" not in subject_log_tag("moling:production:15:1001")


@pytest.mark.parametrize("subject", ["", " ", "bad/subject", "arbitrary", "x" * 257])
def test_personaldb_rejects_unsafe_or_unbounded_subjects(subject: str) -> None:
    """内部主体仍需严格校验，避免构造任意集合名或无界元数据。"""
    with pytest.raises(ValueError):
        collection_name_for_subject(subject)


@pytest.mark.parametrize(
    ("client_name", "safe_name"),
    [
        ("../../foreign.txt", "foreign.txt"),
        ("..\\..\\foreign.txt", "foreign.txt"),
        ("..", "uploaded_file"),
        ("bad\nname.txt", "uploaded_file"),
    ],
)
def test_personaldb_upload_filename_cannot_escape_temp_directory(client_name: str, safe_name: str) -> None:
    assert safe_upload_filename(client_name) == safe_name


def test_personaldb_cache_log_does_not_print_document_content(tmp_path, monkeypatch, caplog) -> None:
    """Embedding缓存键可能包含全文，命中与写入日志只能保留摘要。"""
    from backend.personaldb.embedding_utils import cache_decorator

    monkeypatch.chdir(tmp_path)
    secret_document = "PRIVATE_DOCUMENT_MARKER_T07"

    @cache_decorator
    def transform(value: str) -> str:
        return value.upper()

    with caplog.at_level(logging.INFO):
        assert transform(secret_document)
        assert transform(secret_document)
    assert secret_document not in caplog.text
    assert "tag=" in caplog.text


def test_legacy_numeric_metadata_remains_listable_after_string_namespace_support() -> None:
    """旧Chroma元数据可能保存int，新的字符串路径仍须找到同一数字主体文件。"""
    from backend.personaldb.embedding_utils import ChromaDB

    class CollectionInfo:
        name = "user_123"

    class Collection:
        def get(self):
            return {
                "metadatas": [
                    {
                        "file_id": 7,
                        "file_name": "legacy.txt",
                        "file_type": "txt",
                        "url": "",
                        "folder_id": 0,
                        "user_id": 123,
                    }
                ]
            }

    class Client:
        def list_collections(self):
            return [CollectionInfo()]

        def get_collection(self, name: str):
            assert name == "user_123"
            return Collection()

    chroma = object.__new__(ChromaDB)
    chroma.client = Client()
    files = chroma.list_files_by_user("123")
    assert [item["file_name"] for item in files] == ["legacy.txt"]


def test_agent_cache_log_does_not_print_prompt_content(tmp_path, monkeypatch, caplog) -> None:
    """生成Agent缓存同样不得把提示词或知识库主体拼进日志。"""
    cache_path = Path(__file__).resolve().parents[2] / "slide_agent/slide_agent/sub_agents/ppt_writer/cache_utils.py"
    spec = importlib.util.spec_from_file_location("t07_agent_cache_utils", cache_path)
    assert spec is not None and spec.loader is not None
    cache_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cache_module)
    cache_decorator = cache_module.cache_decorator

    monkeypatch.chdir(tmp_path)
    secret_prompt = "PRIVATE_AGENT_PROMPT_T07"

    @cache_decorator
    def generate(value: str) -> str:
        return value.upper()

    with caplog.at_level(logging.INFO):
        assert generate(secret_prompt)
        assert generate(secret_prompt)
    assert secret_prompt not in caplog.text
    assert "tag=" in caplog.text


def test_file_upload_endpoint_forwards_server_subject_not_forged_form_user(monkeypatch) -> None:
    """真实FastAPI路由即使收到伪造表单user_id，也只能转发服务端主体。"""
    main = _load_main_module()

    class StaticResolver:
        def resolve(self, request):
            return RequestPrincipal(1001, 15, 73, "moling:test:15:1001")

    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"markdown_content": "# 来自可信空间"}

        def raise_for_status(self):
            return None

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, data, files, timeout):
            captured.update({"url": url, "data": data, "files": files, "timeout": timeout})
            return FakeResponse()

    async def fake_outline(markdown: str, language: str):
        yield f"{markdown}:{language}"

    monkeypatch.setattr(main, "legacy_identity_resolver", StaticResolver())
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(main, "stream_agent_response", fake_outline)

    with TestClient(main.app) as client:
        response = client.post(
            "/tools/aippt_outline_from_file",
            data={"user_id": "999999", "language": "chinese"},
            files={"file": ("same-name.txt", b"hello", "text/plain")},
        )

    assert response.status_code == 200
    assert captured["data"]["userId"] == "moling:test:15:1001"
    assert "999999" not in str(captured)


def test_content_endpoint_uses_session_id_only_as_agent_context(monkeypatch) -> None:
    """正文请求可延续Agent上下文，但知识库owner仍只能来自服务端主体。"""
    main = _load_main_module()

    class StaticResolver:
        def resolve(self, request):
            return RequestPrincipal(1001, 15, 73, "moling:test:15:1001")

    captured: dict[str, object] = {}

    async def fake_content(markdown_content, language, generateFromUploadedFile, generateFromWebSearch, knowledge_subject, context_id):
        captured.update(
            {
                "markdown": markdown_content,
                "knowledge_subject": knowledge_subject,
                "context_id": context_id,
            }
        )
        yield b"data: [DONE]\n\n"

    monkeypatch.setattr(main, "legacy_identity_resolver", StaticResolver())
    monkeypatch.setattr(main, "stream_content_response", fake_content)

    with TestClient(main.app) as client:
        response = client.post(
            "/tools/aippt",
            json={
                "content": "# outline",
                "language": "zh",
                "sessionId": "client_context_123",
                "user_id": "999999",
                "generateFromUploadedFile": True,
                "generateFromWebSearch": False,
            },
        )

    assert response.status_code == 200
    assert captured["knowledge_subject"] == "moling:test:15:1001"
    assert captured["context_id"] == "client_context_123"
    assert "999999" not in str(captured)


@pytest.mark.parametrize(
    ("data", "files", "status_code"),
    [
        ({"language": "chinese"}, None, 400),
        (
            {"language": "chinese", "url": "https://example.invalid/a.txt"},
            {"file": ("a.txt", b"hello", "text/plain")},
            400,
        ),
        (
            {"language": "chinese"},
            {"file": ("malware.exe", b"hello", "application/octet-stream")},
            415,
        ),
    ],
)
def test_file_upload_rejects_missing_ambiguous_or_unsupported_input(
    monkeypatch, data, files, status_code
) -> None:
    """错误输入在调用PersonalDB前失败，并给前端稳定中文提示。"""
    main = _load_main_module()

    class StaticResolver:
        def resolve(self, request):
            return RequestPrincipal(1001, 15, 73, "moling:test:15:1001")

    monkeypatch.setattr(main, "legacy_identity_resolver", StaticResolver())
    with TestClient(main.app) as client:
        response = client.post("/tools/aippt_outline_from_file", data=data, files=files)
    assert response.status_code == status_code
    # T21统一错误契约不再暴露FastAPI detail或原始输入。
    assert response.json()["code"] in {"REQUEST_INVALID", "REQUEST_REJECTED"}
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert "detail" not in response.json()

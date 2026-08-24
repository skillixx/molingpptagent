import asyncio
import json
import re
import os
import sys
import dotenv
from pathlib import Path
from datetime import UTC, datetime, timedelta
from fastapi import FastAPI, UploadFile, File
import logging
from pydantic import BaseModel
import uuid
import httpx
from urllib.parse import quote
from typing import Annotated

# 兼容既有 `python main.py` 启动方式，同时允许新增模块使用稳定的包内相对导入。
repository_root = Path(__file__).resolve().parents[2]
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import UploadFile, File, HTTPException, Form
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from outline_client import A2AOutlineClientWrapper
from content_client import A2AContentClientWrapper
from core.config import load_settings
from backend.main_api.api.auth import create_auth_router
from backend.main_api.api.health import create_health_router
from backend.main_api.api.presentations import create_presentations_router
from backend.main_api.api.exports import create_exports_router
from backend.main_api.api.tasks import create_tasks_router
from backend.main_api.core.db import create_verified_database_engine
from backend.main_api.core.health import DependencyProbe, HealthService
from backend.main_api.core.identity import LegacyIdentityResolver, RequestPrincipal, generation_context_id
from backend.main_api.core.observability import (
    FixedWindowRateLimiter, OperationalSafetyMiddleware, install_safe_exception_handlers,
)
from backend.main_api.core.security import trusted_origin_from_url, uvicorn_access_log_enabled
from backend.main_api.integrations.moling import MolingClient
from backend.main_api.integrations.storage import S3StorageAdapter
from backend.main_api.repositories.files import FileRepository
from backend.main_api.repositories.exports import ExportRepository
from backend.main_api.repositories.sessions import SessionRepository
from backend.main_api.repositories.resources import PresentationRepository
from backend.main_api.repositories.reconciliation import BillingReconciliationRepository
from backend.main_api.services.auth import AuthService
from backend.main_api.services.presentations import PresentationService
from backend.main_api.services.exports import ExportService
from backend.main_api.services.files import FileService
from backend.main_api.services.tasks import TaskQueryService
from backend.main_api.template_assets import resolve_template_asset

logger = logging.getLogger(__name__)
dotenv.load_dotenv()

# 加载统一环境配置
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    dotenv.load_dotenv(env_file)
else:
    dotenv.load_dotenv()

# 新功能默认关闭；一旦显式开启，配置不完整会在监听端口前安全失败。
settings = load_settings()
OUTLINE_API = settings.outline_api
CONTENT_API = settings.content_api
app = FastAPI()
install_safe_exception_handlers(app)
auth_service: AuthService | None = None
persistence_engine = None
storage_adapter: S3StorageAdapter | None = None

# 持久功能共用同一连接池；应用启动只检查迁移，不自动建表或升级生产数据库。
if settings.persistence_enabled:
    assert settings.database_url is not None
    persistence_engine = create_verified_database_engine(
        settings.database_url.get_secret_value(),
        # SQLite只允许APP_ENV=test的隔离验证，开发/预发/生产仍强制MySQL。
        allow_sqlite=settings.app_env == "test",
    )

# SSO默认关闭；显式开启后才连接MySQL并注册可信入口，且绝不自动执行迁移。
if settings.sso_enabled:
    assert settings.database_url is not None
    assert settings.moling_api_base_url is not None
    assert settings.internal_api_token is not None
    assert settings.moling_app_id is not None
    assert settings.moling_product_id is not None
    assert persistence_engine is not None
    moling_client = MolingClient(
        base_url=settings.moling_api_base_url,
        internal_api_token=settings.internal_api_token.get_secret_value(),
        app_id=settings.moling_app_id,
        product_id=settings.moling_product_id,
        connect_timeout_seconds=settings.moling_connect_timeout_seconds,
        read_timeout_seconds=settings.moling_read_timeout_seconds,
    )
    session_repository = SessionRepository(persistence_engine)
    # SSO开启时迁移缺失必须在监听端口前失败，禁止首个用户请求才暴露500。
    try:
        session_repository.ensure_schema()
    except Exception:
        persistence_engine.dispose()
        raise
    auth_service = AuthService(
        moling_client=moling_client,
        session_repository=session_repository,
        absolute_ttl=timedelta(seconds=settings.session_ttl_seconds),
        idle_ttl=timedelta(seconds=settings.session_idle_ttl_seconds),
    )
    app.include_router(
        create_auth_router(
            auth_service=auth_service,
            cookie_name=settings.session_cookie_name,
            cookie_secure=settings.session_cookie_secure,
            trusted_origins=(trusted_origin_from_url(settings.app_base_url),),
        )
    )

# 旧工具接口在SSO模式只从服务端Session取owner；本地模式使用固定开发主体保持兼容。
legacy_identity_resolver = LegacyIdentityResolver(
    sso_enabled=settings.sso_enabled,
    app_env=settings.app_env,
    cookie_name=settings.session_cookie_name,
    auth_service=auth_service,
)


def resolve_legacy_principal(request: Request) -> RequestPrincipal:
    """同步Session读取交给FastAPI线程池，避免在流式异步路由中阻塞事件循环。"""
    # 限流中间件与路由依赖共用同一次身份解析，避免一次写请求重复读取Session。
    cached = getattr(request.state, "principal", None)
    if isinstance(cached, RequestPrincipal):
        return cached
    principal = legacy_identity_resolver.resolve(request)
    request.state.principal = principal
    return principal


LegacyPrincipal = Annotated[RequestPrincipal, Depends(resolve_legacy_principal)]

# 公共路径为 /api/presentations；Vite/Nginx去掉 /api 后转发到本路由。
if persistence_engine is not None:
    presentation_repository = PresentationRepository(persistence_engine)
    file_service = None
    if settings.storage_enabled:
        assert settings.storage_endpoint is not None
        assert settings.storage_bucket is not None
        assert settings.storage_access_key_id is not None
        assert settings.storage_secret_access_key is not None
        assert settings.user_storage_quota_bytes is not None
        file_repository = FileRepository(persistence_engine)
        try:
            file_repository.ensure_schema()
        except Exception:
            persistence_engine.dispose()
            raise
        storage_adapter = S3StorageAdapter(
            endpoint=settings.storage_endpoint,
            bucket=settings.storage_bucket,
            access_key_id=settings.storage_access_key_id.get_secret_value(),
            secret_access_key=settings.storage_secret_access_key.get_secret_value(),
            connect_timeout_seconds=settings.storage_connect_timeout_seconds,
            read_timeout_seconds=settings.storage_read_timeout_seconds,
            max_attempts=settings.storage_max_attempts,
        )
        file_service = FileService(
            repository=file_repository,
            storage=storage_adapter,
            storage_prefix=settings.storage_prefix,
            user_storage_quota_bytes=settings.user_storage_quota_bytes,
            upload_file_max_bytes=settings.upload_file_max_bytes,
            export_pptx_max_bytes=settings.export_pptx_max_bytes,
            thumbnail_max_bytes=settings.thumbnail_max_bytes,
        )
        storage_stale_before = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            seconds=settings.storage_upload_stale_seconds
        )
        # 启动恢复只处理超过租约的未激活/未引用对象；删除失败会保留索引和占额供下次重试。
        file_service.recover_stale_uploads(
            storage_stale_before, limit=settings.cleanup_batch_size
        )
        file_service.recover_stale_deletions(
            storage_stale_before, limit=settings.cleanup_batch_size
        )
        file_service.cleanup_unreferenced_checkpoints(
            storage_stale_before, limit=settings.cleanup_batch_size
        )
        assert settings.download_signing_secret is not None
        export_repository = ExportRepository(persistence_engine)
        export_repository.ensure_schema()
        app.include_router(create_exports_router(
            service=ExportService(
                repository=export_repository,
                file_service=file_service,
                download_signing_secret=settings.download_signing_secret.get_secret_value(),
                download_url_ttl_seconds=settings.download_url_ttl_seconds,
            ),
            principal_dependency=resolve_legacy_principal,
            trusted_origins=(trusted_origin_from_url(settings.app_base_url),)
            if settings.app_base_url else (),
            csrf_enabled=settings.sso_enabled,
        ))
    try:
        presentation_repository.ensure_schema()
    except Exception:
        persistence_engine.dispose()
        raise
    app.include_router(
        create_presentations_router(
            service=PresentationService(
                presentation_repository,
                task_max_attempts=settings.task_max_attempts,
                user_presentation_limit=settings.user_presentation_limit,
                presentation_json_max_bytes=settings.presentation_json_max_bytes,
                checkpoint_max_count=settings.checkpoint_max_count,
                checkpoint_inline_max_bytes=settings.checkpoint_inline_max_bytes,
                billing_enabled=settings.billing_enabled,
                billing_product_id=settings.moling_product_id,
                billing_reserve_points=settings.ppt_generation_reserve_points,
                billing_settle_points=settings.ppt_generation_settle_points,
                file_service=file_service,
                storage_upload_stale_seconds=settings.storage_upload_stale_seconds,
            ),
            principal_dependency=resolve_legacy_principal,
            trusted_origins=(trusted_origin_from_url(settings.app_base_url),)
            if settings.app_base_url
            else (),
            csrf_enabled=settings.sso_enabled,
        )
    )
    app.include_router(
        create_tasks_router(
            service=TaskQueryService(BillingReconciliationRepository(persistence_engine)),
            principal_dependency=resolve_legacy_principal,
        )
    )
    # Engine由应用进程持有，关闭时只注册一次释放连接池。
    app.router.add_event_handler("shutdown", persistence_engine.dispose)


def _http_health_check(url: str):
    """构造只读依赖探针；异常、URL与响应正文均不进入健康响应或日志。"""
    def check() -> bool:
        with httpx.Client(
            timeout=settings.health_probe_timeout_seconds,
            follow_redirects=False,
        ) as client:
            response = client.get(url)
            return 200 <= response.status_code < 300
    return check


def _http_reachability_check(url: str):
    """外部平台未提供健康路由时，只验证网络和 HTTP 服务可达，不冒充业务鉴权成功。"""
    def check() -> bool:
        with httpx.Client(
            timeout=settings.health_probe_timeout_seconds,
            follow_redirects=False,
        ) as client:
            response = client.get(url)
            return response.status_code < 500
    return check


dependency_probes: list[DependencyProbe] = [
    DependencyProbe("outline", True, _http_health_check(f"{settings.outline_api.rstrip('/')}/.well-known/agent.json")),
    DependencyProbe("content", True, _http_health_check(f"{settings.content_api.rstrip('/')}/.well-known/agent.json")),
    DependencyProbe("personaldb", True, _http_health_check(f"{settings.personal_db.rstrip('/')}/healthz")),
]
if persistence_engine is not None:
    def _database_health_check() -> bool:
        # 只执行常量查询，不读取业务数据，也不把连接串写入异常。
        from sqlalchemy import text
        with persistence_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    dependency_probes.append(DependencyProbe("database", True, _database_health_check))
if storage_adapter is not None:
    dependency_probes.append(DependencyProbe("storage", True, storage_adapter.check))
if settings.sso_enabled and settings.moling_api_base_url:
    dependency_probes.append(DependencyProbe(
        "moling", True,
        _http_reachability_check(settings.moling_api_base_url.rstrip("/")),
    ))
app.include_router(create_health_router(
    HealthService(tuple(dependency_probes)),
    release_commit=settings.release_commit,
    release_channel=settings.release_channel,
))

# 关键写接口按真实owner独立限流；多实例部署时T22网关还会提供外层粗粒度保护。
critical_write_routes = {
    "POST /presentations", "PATCH /presentations/*", "DELETE /presentations/*",
    "POST /presentations/*/duplicate", "POST /presentations/*/versions",
    "POST /presentations/*/versions/*/restore", "POST /presentations/*/exports/pptx",
    "PUT /presentations/*/thumbnail", "POST /tools/aippt",
    "POST /tools/aippt_outline", "POST /tools/aippt_outline_from_file",
    "POST /tools/aippt_by_id", "POST /auth/logout",
}
app.add_middleware(
    OperationalSafetyMiddleware,
    limiter=FixedWindowRateLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    ),
    critical_routes=critical_write_routes if settings.rate_limit_enabled else set(),
    principal_resolver=resolve_legacy_principal,
    audit_enabled=settings.audit_log_enabled,
)

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [trusted_origin_from_url(settings.app_base_url)]
        if settings.sso_enabled and settings.app_base_url
        else ["*"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool

async def stream_agent_response(prompt: str, language: str = "chinese"):
    """A generator that yields parts of the agent response."""
    outline_wrapper = A2AOutlineClientWrapper(session_id=uuid.uuid4().hex, agent_url=OUTLINE_API)
    async for chunk_data in outline_wrapper.generate(prompt, language=language):
        logger.debug("大纲分片 type=%s", chunk_data.get("type"))
        if chunk_data["type"] == "text":
            yield chunk_data["text"]


@app.post("/tools/aippt_outline")
async def aippt_outline(payload: AipptRequest, principal: LegacyPrincipal):
    assert payload.stream, "只支持流式的返回大纲"
    logger.info("收到大纲生成请求 language=%s", payload.language)
    return StreamingResponse(stream_agent_response(payload.content, payload.language), media_type="text/plain")


@app.post("/tools/aippt_outline_from_file")
async def aippt_outline_from_file(
    principal: LegacyPrincipal,
    user_id: int | str | None = Form(None),
    file: UploadFile = File(None),  # 允许缺省，这样我们可以决定走 file 或 url
    url: str | None = Form(None),
    folder_id: int|str = Form(0),
    file_type: str | None = Form(None),
    language: str = Form("chinese"),  # 添加language参数，默认为chinese
):
    """
    对齐 personaldb 的 /upload/：
    - 必填: userId, fileId
    - 可选: folderId (默认0), fileType
    - file 与 url 互斥，至少一个
    """
    personaldb_api_url = settings.personal_db

    # 互斥校验（与 personaldb 完全一致）
    has_file = file is not None
    has_url = bool(url and url.strip())
    if not has_file and not has_url:
        raise HTTPException(status_code=400, detail="必须提供文件或URL")
    if has_file and has_url:
        raise HTTPException(status_code=400, detail="文件和URL只能提供一个")

    # 服务端生成随机文件键，避免同毫秒并发上传覆盖同一主体的向量。
    file_id = uuid.uuid4().hex

    # 推断 fileType（当上传文件时且未显式传入）
    if has_file and not file_type:
        if file.filename and "." in file.filename:
            file_type = file.filename.rsplit(".", 1)[-1]
        else:
            file_type = "unknown"
    normalized_file_type = (file_type or "").lower().lstrip(".")
    if normalized_file_type not in {"txt", "docx", "pdf", "pptx"}:
        raise HTTPException(status_code=415, detail="仅支持TXT、DOCX、PDF和PPTX文件")

    # 组装 multipart/form-data
    # 注意：即使是 url 分支，也仍用 multipart，personaldb 也能解析 form
    data = {
        # 保留旧 user_id 表单字段只为兼容客户端，真正主体始终来自服务端Session。
        "userId": principal.knowledge_subject,
        "fileId": file_id,
        "folderId": str(folder_id),
    }
    data["fileType"] = normalized_file_type
    if has_url:
        data["url"] = url.strip()

    files_payload = None
    if has_file:
        # 读取一次到内存，httpx 需要 (filename, bytes/obj, content_type)
        file_bytes = await file.read(settings.upload_file_max_bytes + 1)
        if not file_bytes:
            raise HTTPException(status_code=400, detail="文件内容为空")
        if len(file_bytes) > settings.upload_file_max_bytes:
            raise HTTPException(status_code=413, detail="上传文件超过大小限制")
        files_payload = {
            "file": (
                file.filename or "uploaded_file",
                file_bytes,
                file.content_type or "application/octet-stream",
            )
        }

    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                upload_url,
                data=data,
                files=files_payload,
                timeout=360.0,
            )
            # 不直接 raise，先打日志方便定位
            if resp.status_code >= 400:
                logger.warning("PersonalDB上传失败 status=%s", resp.status_code)
                resp.raise_for_status()

            # personaldb 的处理函数最终会返回一个 JSON（你上游期望里要有 markdown_content）
            try:
                result = resp.json()
            except ValueError:
                raise HTTPException(status_code=502, detail="PersonalDB响应格式错误")

            markdown_content = result.get("markdown_content")
            if markdown_content is None:
                raise HTTPException(status_code=502, detail="PersonalDB响应缺少转换内容")
            logger.info("文件转换完成，开始生成大纲 language=%s", language)

            return StreamingResponse(stream_agent_response(markdown_content, language), media_type="text/plain")

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="PersonalDB处理超时") from None
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail="PersonalDB处理失败") from None
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="PersonalDB连接失败") from None

class AipptContentRequest(BaseModel):
    content: str
    language: str = "zh"  #默认中文
    sessionId: str = ""  # 仅用于同一次Agent生成上下文，知识库owner始终来自服务端Session
    generateFromUploadedFile: bool = False  # 是否从上传的文件中生成PPT内容
    generateFromWebSearch: bool = True  # 是否从网络搜索中生成PPT内容

async def stream_content_response(
    markdown_content: str,
    language,
    generateFromUploadedFile,
    generateFromWebSearch,
    knowledge_subject: str,
    context_id: str,
):
    match = re.search(r"(# .*)", markdown_content, flags=re.DOTALL)
    result = markdown_content[match.start():] if match else markdown_content
    logger.info("正文生成接收大纲 chars=%s", len(result))

    content_wrapper = A2AContentClientWrapper(session_id=context_id, agent_url=CONTENT_API)

    search_engine = []
    if generateFromUploadedFile:
        search_engine.append("KnowledgeBaseSearch")
    if generateFromWebSearch:
        search_engine.append("DocumentSearch")

    metadata = {"user_id": knowledge_subject, "search_engine": search_engine, "language": language}
    logger.info("收到正文生成请求 language=%s search_count=%s", language, len(search_engine))

    last_flush = asyncio.get_event_loop().time()

    async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
        logger.debug("正文分片 type=%s", chunk_data.get("type"))

        # 心跳：每15秒发一次注释，避免某些代理断连接
        now = asyncio.get_event_loop().time()
        if now - last_flush > 10:
            yield b": keep-alive\n\n"
            last_flush = now

        if chunk_data.get("type") == "text":
            # 注意：每条 SSE 事件以空行结束
            payload = chunk_data["text"]
            yield f"data: {payload}\n\n".encode("utf-8")

    # 可选：显式结束信号（前端可据此收尾）
    yield b"data: [DONE]\n\n"

@app.post("/tools/aippt")
async def aippt_content(payload: AipptContentRequest, principal: LegacyPrincipal):
    markdown_content = payload.content
    # sessionId仅维持同一次生成的Agent上下文，绝不参与owner或知识库命名空间。
    context_id = generation_context_id(payload.sessionId, uuid.uuid4().hex)

    async def event_generator():
        async for chunk in stream_content_response(
            markdown_content,
            language=payload.language,
            generateFromUploadedFile=payload.generateFromUploadedFile,
            generateFromWebSearch=payload.generateFromWebSearch,
            knowledge_subject=principal.knowledge_subject,
            context_id=context_id,
        ):
            yield chunk

    # 关键：SSE 推荐这些头
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/data/{filename}")
async def get_data(filename: str):
    try:
        file_path = resolve_template_asset(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="模板资源不存在") from None
    return FileResponse(file_path)

@app.get("/templates")
async def get_templates():
    templates = [
        { "name": "红色通用", "id": "template_1", "cover": "/api/data/template_1.jpg" },
        { "name": "蓝色通用", "id": "template_2", "cover": "/api/data/template_2.jpg" },
        { "name": "紫色通用", "id": "template_3", "cover": "/api/data/template_3.jpg" },
        { "name": "莫兰迪配色", "id": "template_4", "cover": "/api/data/template_4.jpg" },
        # 毕业答辩模板由用户提供的 PPTX 转换，并完成页面与内容槽位标注。
        { "name": "毕业答辩", "id": "template_5", "cover": "/api/data/template_5.jpg" },
        # { "name": "图表", "id": "template_6", "cover": "/api/data/template_6.jpg" },
        # 红金年会模板使用原创背景与装饰素材，内容图片槽和装饰图片已显式隔离。
        { "name": "红金年会颁奖", "id": "template_7", "cover": "/api/data/template_7.jpg" },
        # 科技蓝扁平模板基于用户参考PPT重构，使用原创位图和可编辑PPTist语义槽。
        { "name": "科技蓝扁平", "id": "template_8", "cover": "/api/data/template_8.jpg" },
    ]

    return {"data": templates}

class AipptByIDRequest(BaseModel):
    id: str
    language: str = "chinese"  # 添加language字段，默认为chinese

async def aippt_file_id_streamer(id: str, knowledge_subject: str, language: str = "chinese"):
    """根据用户的已有的文件数据中的文件id来生成ppt
    id: 文件的id，例如论文的pmid
    """
    yield json.dumps({"type": "status", "message": "正在解析文件..."}, ensure_ascii=False) + '\n'
    paper_markdown = ""
    if not paper_markdown:
        yield json.dumps({"type": "status", "message": "没有找到该文章"}, ensure_ascii=False) + '\n'
        return
    personaldb_api_url = settings.personal_db
    # 论文名称
    file_name = f"{id}.md"
    data = {
        "userId": knowledge_subject,
        "fileId": id,
        "folderId": 123,
        "fileType": "txt"
    }
    files = {"file": (file_name, paper_markdown, "text/plain")}
    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"
    response = httpx.post(upload_url, data=data, files=files, timeout=40.0)
    result = response.json()
    if not result.get("id"):
        yield json.dumps({"type": "status", "message": "论文向量化失败，请联系管理员"}, ensure_ascii=False) + '\n'
    yield json.dumps({"type": "status", "message": "正在生成大纲..."}, ensure_ascii=False) + '\n'
    outline = ""
    async for outline_trunk in stream_agent_response(paper_markdown, language):
        outline += outline_trunk
    yield json.dumps({"type": "status", "message": "大纲生成完毕，即将生成PPT..."}, ensure_ascii=False) + '\n'

    match = re.search(r"(# .*)", outline, flags=re.DOTALL)

    if match:
        result = outline[match.start():]
    else:
        result = outline
    logger.info("按文件生成接收大纲 chars=%s", len(result))
    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)
    # 传入不同的参数，使用不同的搜索,可以同时使用多个搜索
    search_engine = ["KnowledgeBaseSearch"]
    # 方便测试，这个已经在知识库中插入了对应的数据
    metadata = {"user_id": knowledge_subject, "search_engine": search_engine, "language": language}
    logger.info("按文件生成正文 language=%s", language)
    async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
        logger.debug("按文件正文分片 type=%s", chunk_data.get("type"))
        if chunk_data["type"] == "text":
            slide = chunk_data["text"]
            yield slide + '\n'


@app.post("/tools/aippt_by_id")
async def aippt_by_id(payload: AipptByIDRequest, principal: LegacyPrincipal):
    return StreamingResponse(
        aippt_file_id_streamer(payload.id, principal.knowledge_subject, payload.language),
        media_type="application/json; charset=utf-8",
    )


@app.get("/files/{user_id}")
async def list_user_files(user_id: str, principal: LegacyPrincipal):
    """
    列出指定用户的所有文件信息
    """
    personaldb_api_url = settings.personal_db
    # 路径中的旧user_id被忽略，只把服务端主体编码后转发给内部服务。
    url = f"{personaldb_api_url}/files/{quote(principal.knowledge_subject, safe='')}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="PersonalDB连接失败") from None
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail="PersonalDB处理失败") from None


@app.get("/proxy")
async def proxy(request: Request, url: str = Query(..., description="Target absolute URL")):
    """
    透明代理上游资源，转发部分请求头，透传关键响应头，并允许前端同源访问。
    适合图片/音视频等二进制内容。
    """
    HEADERS_TO_FORWARD = {"Range", "User-Agent"}  # 需要时可扩展
    HEADERS_TO_COPY = {
        "Content-Type",
        "Content-Length",
        "Content-Disposition",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
        "Cache-Control",
        "Expires",
    }
    forward_headers = {}
    for h in HEADERS_TO_FORWARD:
        v = request.headers.get(h)
        if v:
            forward_headers[h] = v

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            upstream = await client.get(url, headers=forward_headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream fetch error: {e!s}")

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail="Upstream error")

    headers = {}
    for h in HEADERS_TO_COPY:
        if h in upstream.headers:
            headers[h] = upstream.headers[h]

    # 允许被前端同源读取
    headers["Access-Control-Allow-Origin"] = "*"
    # 给静态资源加简单缓存（按需调整）
    headers.setdefault("Cache-Control", "public, max-age=86400")

    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        headers=headers,
        media_type=upstream.headers.get("Content-Type"),
    )

if __name__ == "__main__":
    import uvicorn
    # SSO入口含一次性query票据；启用SSO时关闭Uvicorn请求行日志，由Nginx记录非入口流量。
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.main_api_port,
        access_log=uvicorn_access_log_enabled(sso_enabled=settings.sso_enabled),
    )

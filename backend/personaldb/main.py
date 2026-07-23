#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/12
# @Desc  : 使用FastAPI实现API，接收JSON或RabbitMQ消息，下载七牛云文件，读取内容并生成embedding向量

import os
import json
import requests
import uvicorn
import logging
import asyncio
import uuid
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from pydantic import BaseModel, ValidationError
from typing import List, Optional
import embedding_utils
from embedding_utils import cache_decorator
from urllib.parse import urlparse
from core.magic_pdf_converter import MagicPDFConverter
from core.markitdown_converter import MarkItDownConverter
from core.chunkers.semantic_chunker import SemanticChunker
from core.chunkers.fast_chunker import FastChunker
try:
    from .namespace import collection_name_for_subject, subject_log_tag
    from .security import safe_upload_filename
except ImportError:
    from namespace import collection_name_for_subject, subject_log_tag
    from security import safe_upload_filename

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/healthz")
def healthz():
    """仅证明知识库进程可响应；不在探针中读取或修改任何用户集合。"""
    return {"status": "ok"}

# 创建临时下载目录
TEMP_DIR = "temp_download"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# RabbitMQ消息处理类

class SearchQuery(BaseModel):
    userId: int | str
    query: str
    keyword: Optional[str] = ""
    topk: Optional[int] = 3

@app.post("/search")
def search_personal_knowledge_base(query: SearchQuery):
    """
    搜索个人知识库
    """
    try:
        logger.info("收到知识库搜索 subject=%s topk=%s", subject_log_tag(query.userId), query.topk)
        embedder = embedding_utils.EmbeddingModel()
        chroma = embedding_utils.ChromaDB(embedder)
        collection_name = collection_name_for_subject(query.userId)

        result = chroma.query2collection(
            collection=collection_name,
            query_documents=[query.query],
            keyword=query.keyword,
            topk=query.topk
        )
        documents = result.get("documents") or []
        result_count = len(documents[0]) if documents and isinstance(documents[0], list) else len(documents)
        logger.info("知识库搜索成功 subject=%s count=%s", subject_log_tag(query.userId), result_count)
        return result
    except Exception:
        logger.error("知识库搜索失败 subject=%s", subject_log_tag(query.userId))
        raise HTTPException(status_code=500, detail="知识库搜索失败") from None

@cache_decorator
def _get_markdown_content(file_path: str, file_name: str) -> str:
    """
    根据文件类型选择合适的转换器，将文件内容转换为Markdown格式。
    PDF文件使用MagicPDFConverter（MinerU），其他文件使用MarkitdownConverter。
    """
    # 获取文件扩展名, 是否可以使用MinerU，如果不用显卡速度太慢
    USE_MINERU = os.environ.get("USE_MINERU", "false")
    if USE_MINERU.lower() == "true":
        CAN_USE_MINERU = True
    else:
        CAN_USE_MINERU = False
    file_extension = os.path.splitext(file_name)[1].lower() if file_name else ""

    # 根据文件类型选择转换器
    if CAN_USE_MINERU and file_extension == '.pdf':
        # 使用 MinerU (MagicPDFConverter) 处理PDF
        logger.info("使用PDF转换器处理上传文件")
        converter = MagicPDFConverter(output_dir="./output_pdf")
        content, _ = converter.convert_pdf_file(file_path)
        return True, content
    else:
        # 使用 markitdown 处理其他文件
        logger.info("使用Markitdown转换器处理上传文件")
        converter = MarkItDownConverter(use_magic_pdf=False)  #use_magic_pdf设定是否使用MinerU
        content, _ = converter.convert_file(file_path)
        return True, content


def process_and_vectorize_local_file(file_name: str, temp_file_path: str, id: int, user_id: int|str, file_type: str, url: str, folder_id: int):
    """
    从本地文件路径处理文件、进行向量化并存储
    """
    # 步骤2: 使用适当的转换器读取文件内容
    logger.info("开始读取上传文件内容")
    
    status, markdown_content = _get_markdown_content(temp_file_path, file_name)

    if not markdown_content or not markdown_content.strip():
        logger.error("上传文件内容为空或无效")
        raise ValueError("文件内容为空或无效")
    logger.info("文件内容读取成功，准备进行分块")

    # 对Markdown格式进行Trunk(分块)
    documents = _chunk_text(markdown_content)
    if not documents:
        raise ValueError("分块后内容为空")
    logger.info("内容分块成功 count=%s", len(documents))

    # 步骤3: 检查环境变量
    if not os.getenv("ALI_API_KEY"):
        logger.error("ALI_API_KEY环境变量未设置")
        raise ValueError("ALI_API_KEY环境变量未设置")

    # 步骤4: 使用embedding_utils生成embedding向量并插入向量
    logger.info("初始化embedding模型")
    embedder = embedding_utils.EmbeddingModel()
    chroma = embedding_utils.ChromaDB(embedder)
    logger.info("开始插入文件向量 file_id=%s", id)
    embedding_result = chroma.insert_file_vectors(
        file_name=file_name,
        user_id=user_id,
        file_id=id,
        file_type=file_type or "unknown",
        url=url or "",
        folder_id=folder_id or 0,
        documents=documents
    )
    logger.info("向量插入成功")

    result = {
        "id": id,
        "file_name": file_name,
        "userId": user_id,
        "fileType": file_type,
        "url": url,
        "folderId": folder_id,
        "embedding_result": embedding_result,
        "markdown_content": markdown_content
    }
    logger.info("文件转换与向量化完成")
    return result


def process_file_sync(file_name:str, id: int, user_id: int|str, file_type: str, url: str, folder_id: int):
    """
    处理文件下载、读取和生成embedding的同步版本
    """
    if not url:
        logger.error("url为空")
        raise ValueError("url不能为空")

    # 验证URL格式
    if not url.startswith(("http://", "https://")):
        logger.error("下载URL格式无效")
        raise ValueError("url必须以http://或https://开头")

    parsed_url = urlparse(url)
    temp_file_path = None
    try:
        # 步骤1: 下载文件
        # file_name = os.path.basename(parsed_url.path) or f"downloaded_file_{user_id}"
        temp_file_path = os.path.join(TEMP_DIR, file_name)
        logger.info("开始下载依据文件")
        response = requests.get(url, timeout=60, proxies=None)
        response.raise_for_status()
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)
        logger.info("依据文件下载成功")

        return process_and_vectorize_local_file(file_name, temp_file_path, id, user_id, file_type, url, folder_id)

    except requests.exceptions.Timeout:
        logger.error("依据文件下载超时")
        raise ValueError("依据文件下载超时") from None
    except requests.exceptions.RequestException:
        logger.error("依据文件下载失败")
        raise ValueError("依据文件下载失败") from None
    except ValueError:
        logger.error("依据文件处理失败")
        raise
    except Exception:
        logger.error("依据文件处理失败 error_type=unexpected")
        raise ValueError("依据文件处理失败") from None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info("依据文件临时副本已删除")


@app.post("/upload/")
async def upload_and_vectorize_endpoint(request: Request):
    """
    支持三种内容类型：
    - multipart/form-data（带或不带文件）
    - application/x-www-form-urlencoded
    - application/json

    字段：
    - userId: int
    - fileId: int
    - folderId: int (可选，默认0)
    - fileType: str (可选)
    - url: str (可选，与 file 互斥)
    - file: UploadFile (可选，与 url 互斥)
    """
    temp_file_path = None
    try:
        # 统一解析 body
        content_type = request.headers.get("content-type", "")
        data = {}
        upload_file: UploadFile | None = None

        if "application/json" in content_type:
            data = await request.json()
        else:
            # 对 multipart/form-data 与 x-www-form-urlencoded 都适用
            form = await request.form()
            data = dict(form)
            possible_file = form.get("file")
            if possible_file:
                upload_file = possible_file

        # 参数解析与校验
        userId = data.get("userId")
        fileId = data.get("fileId")

        if userId is None:
            raise HTTPException(status_code=422, detail="缺少或非法参数: userId")
        if fileId is None:
            raise HTTPException(status_code=422, detail="缺少或非法参数: fileId")

        folderId = int(data.get("folderId", 0))
        fileType = data.get("fileType")
        url = data.get("url")

        # 互斥校验
        has_url = bool(url and str(url).strip())
        has_file = upload_file is not None
        if not has_url and not has_file:
            raise HTTPException(status_code=400, detail="必须提供 'url' 或 'file'")
        if has_url and has_file:
            raise HTTPException(status_code=400, detail="只能提供 'url' 或 'file' 中的一个")

        # 分支：文件上传
        if has_file:
            safe_file_name = safe_upload_filename(upload_file.filename if upload_file else None)
            # 推断 fileType
            if not fileType:
                fileType = safe_file_name.rsplit(".", 1)[-1] if "." in safe_file_name else "unknown"

            temp_file_name = f"{uuid.uuid4()}_{safe_file_name}"
            temp_file_path = os.path.join(TEMP_DIR, temp_file_name)
            # 保存上传内容
            content_bytes = await upload_file.read()
            with open(temp_file_path, "wb") as buffer:
                buffer.write(content_bytes)
            logger.info("上传文件临时副本写入成功")

            return process_and_vectorize_local_file(
                file_name=safe_file_name,
                temp_file_path=temp_file_path,
                id=fileId,
                user_id=userId,
                file_type=fileType,
                url="",  # 直接上传无 URL
                folder_id=folderId
            )

        # 分支：URL 下载处理
        else:
            file_name = os.path.basename(urlparse(url).path) or f"downloaded_file_{userId}"
            return process_file_sync(
                file_name=file_name,
                id=fileId,
                user_id=userId,
                file_type=fileType,
                url=url,
                folder_id=folderId
            )

    except HTTPException:
        raise
    except Exception:
        # URL、文件名、正文和底层异常可能含敏感数据，仅返回稳定错误。
        logger.error("上传和向量化失败")
        raise HTTPException(status_code=500, detail="上传和向量化失败") from None
    finally:
        pass


class TextVectorizeBody(BaseModel):
    """
    纯文本向量化请求体。
    仅必需字段：content, fileId, fileName
    其余参数均为可选，默认空/0。
    """
    content: str
    fileId: int
    fileName: str
    userId: Optional[int | str] = 0
    fileType: Optional[str] = None
    url: Optional[str] = ""
    folderId: Optional[int] = 0


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    """
    使用 SemanticChunker 进行分块。
    """
    text = (text or "").strip()
    if not text:
        return []
    chunker = FastChunker(max_tokens=max_chars)
    chunks = chunker.chunk_text(text)
    return [chunk.content for chunk in chunks]


def process_text_content(
    file_name: str,
    text: str,
    id: int,
    user_id: int | str = 0,
    file_type: Optional[str] = None,
    folder_id: int = 0,
    url: str = ""
):
    """
    直接对纯文本进行向量化并落库（Chroma）。
    其余参数默认空/0，以满足“无需额外参数”的需求。
    """
    logger.info("开始处理纯文本向量化")
    if not text or not text.strip():
        raise ValueError("content 不能为空")

    # 与现有流程保持一致的环境变量校验
    if not os.getenv("ALI_API_KEY"):
        logger.error("ALI_API_KEY环境变量未设置")
        raise ValueError("ALI_API_KEY环境变量未设置")

    documents = _chunk_text(text)
    if not documents:
        raise ValueError("content 无有效文本")

    logger.info("初始化 embedding 模型与 Chroma")
    embedder = embedding_utils.EmbeddingModel()
    chroma = embedding_utils.ChromaDB(embedder)

    logger.info("插入文本向量 fileId=%s subject=%s", id, subject_log_tag(user_id))
    embedding_result = chroma.insert_file_vectors(
        file_name=file_name,
        user_id=user_id or 0,
        file_id=id,
        file_type=file_type or "unknown",
        url=url or "",
        folder_id=folder_id or 0,
        documents=documents
    )

    result = {
        "id": id,
        "file_name": file_name,
        "userId": user_id or 0,
        "fileType": file_type or "unknown",
        "url": url or "",
        "folderId": folder_id or 0,
        "embedding_result": embedding_result
    }
    logger.info("纯文本向量化完成")
    return result


# ===== 纯文本向量化接口 =====
@app.post("/vectorize/text")
def vectorize_text_endpoint(body: TextVectorizeBody):
    """
    纯文本向量化：
    - 必填：content, fileId, fileName
    - 可选：userId(默认0), fileType(None), url(""), folderId(0)
    """
    try:
        logger.info(
            "收到文本向量化请求 fileId=%s subject=%s",
            body.fileId,
            subject_log_tag(body.userId or 0),
        )
        return process_text_content(
            file_name=body.fileName,
            text=body.content,
            id=body.fileId,
            user_id=body.userId or 0,
            file_type=body.fileType,
            folder_id=body.folderId or 0,
            url=body.url or ""
        )
    except Exception:
        logger.error("文本向量化失败 subject=%s", subject_log_tag(body.userId or 0))
        raise HTTPException(status_code=500, detail="文本向量化失败") from None

@app.get("/files/{user_id}")
def list_user_files(user_id: str):
    """
    列出指定用户的所有文件信息
    """
    try:
        logger.info("收到文件列表请求 subject=%s", subject_log_tag(user_id))
        embedder = embedding_utils.EmbeddingModel()
        chroma = embedding_utils.ChromaDB(embedder)

        files = chroma.list_files_by_user(user_id=user_id)

        if not files:
            logger.info("主体%s没有文件", subject_log_tag(user_id))
            return []

        logger.info("文件列表成功 subject=%s count=%s", subject_log_tag(user_id), len(files))
        return files
    except Exception:
        logger.error("文件列表失败 subject=%s", subject_log_tag(user_id))
        raise HTTPException(status_code=500, detail="列出文件失败") from None


if __name__ == "__main__":
    """
    主函数入口：启动FastAPI服务
    """
    logger.info("启动Personal DB FastAPI服务")
    uvicorn.run(app, host="127.0.0.1", port=9100)

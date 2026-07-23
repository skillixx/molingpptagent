"""T20导出归档OpenAPI响应模型。"""

from datetime import datetime

from pydantic import BaseModel


class ExportResponse(BaseModel):
    id: str
    presentation_id: str
    presentation_version: int
    file_id: str
    sha256: str
    size_bytes: int
    created_at: datetime
    download_url: str
    reused: bool


class ExportListResponse(BaseModel):
    items: list[ExportResponse]
    total: int


class ThumbnailResponse(BaseModel):
    file_id: str


__all__ = ["ExportListResponse", "ExportResponse", "ThumbnailResponse"]

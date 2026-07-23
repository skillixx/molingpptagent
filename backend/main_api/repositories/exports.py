"""T20 导出记录仓储：幂等、owner作用域和软删除围栏。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from ..models.domain import Presentation, PresentationExport, StoredFile


class ExportConflict(RuntimeError):
    """同一幂等键被用于不同导出内容。"""


class ExportNotFound(RuntimeError):
    """作品或导出文件不属于当前owner，统一按不存在处理。"""


class ExportSchemaError(RuntimeError):
    """T20迁移未应用。"""


@dataclass(frozen=True)
class ExportWithFile:
    export: PresentationExport
    file: StoredFile
    title: str


class ExportRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)

    def ensure_schema(self) -> None:
        try:
            schema = inspect(self.engine)
            columns = {item["name"] for item in schema.get_columns("trainppt_exports")}
            uniques = {item["name"] for item in schema.get_unique_constraints("trainppt_exports")}
            if "request_id" not in columns or "uq_exports_owner_request" not in uniques:
                raise ExportSchemaError("导出数据表迁移未完成")
        except ExportSchemaError:
            raise
        except Exception:
            raise ExportSchemaError("导出数据表迁移检查失败") from None

    def get_request(self, owner_user_id: int, request_id: str) -> ExportWithFile | None:
        with self._session_factory() as db:
            row = db.execute(
                select(PresentationExport, StoredFile, Presentation.title)
                .join(StoredFile, StoredFile.id == PresentationExport.file_id)
                .join(Presentation, Presentation.id == PresentationExport.presentation_id)
                .where(
                    PresentationExport.owner_user_id == owner_user_id,
                    PresentationExport.request_id == request_id,
                )
            ).one_or_none()
            return ExportWithFile(*row) if row else None

    def create(self, record: PresentationExport) -> tuple[ExportWithFile, bool]:
        try:
            with self._session_factory.begin() as db:
                presentation = db.scalar(select(Presentation).where(
                    Presentation.id == record.presentation_id,
                    Presentation.owner_user_id == record.owner_user_id,
                    Presentation.deleted_at.is_(None),
                ).with_for_update())
                if presentation is None:
                    raise ExportNotFound
                if presentation.current_version != record.presentation_version:
                    raise ExportConflict
                file = db.scalar(select(StoredFile.id).where(
                    StoredFile.id == record.file_id,
                    StoredFile.owner_user_id == record.owner_user_id,
                    StoredFile.presentation_id == record.presentation_id,
                    StoredFile.purpose == "pptx",
                    StoredFile.status == "active",
                    StoredFile.deleted_at.is_(None),
                ))
                if file is None:
                    raise ExportNotFound
                db.add(record)
        except IntegrityError:
            existing = self.get_request(record.owner_user_id, record.request_id)
            if existing is None:
                raise
            return existing, True
        created = self.get_request(record.owner_user_id, record.request_id)
        if created is None:
            raise RuntimeError("export insert missing")
        return created, False

    def list(self, owner_user_id: int, presentation_id: str) -> tuple[ExportWithFile, ...]:
        with self._session_factory() as db:
            if db.scalar(select(Presentation.id).where(
                Presentation.id == presentation_id,
                Presentation.owner_user_id == owner_user_id,
                Presentation.deleted_at.is_(None),
            )) is None:
                raise ExportNotFound
            rows = db.execute(
                select(PresentationExport, StoredFile, Presentation.title)
                .join(StoredFile, StoredFile.id == PresentationExport.file_id)
                .join(Presentation, Presentation.id == PresentationExport.presentation_id)
                .where(
                    PresentationExport.owner_user_id == owner_user_id,
                    PresentationExport.presentation_id == presentation_id,
                    StoredFile.status == "active",
                    StoredFile.deleted_at.is_(None),
                )
                .order_by(PresentationExport.created_at.desc(), PresentationExport.id.desc())
            ).all()
            return tuple(ExportWithFile(*row) for row in rows)

    def downloadable(self, owner_user_id: int, file_id: str) -> ExportWithFile | None:
        with self._session_factory() as db:
            row = db.execute(
                select(PresentationExport, StoredFile, Presentation.title)
                .join(StoredFile, StoredFile.id == PresentationExport.file_id)
                .join(Presentation, Presentation.id == PresentationExport.presentation_id)
                .where(
                    PresentationExport.owner_user_id == owner_user_id,
                    PresentationExport.file_id == file_id,
                    Presentation.deleted_at.is_(None),
                    StoredFile.status == "active",
                    StoredFile.deleted_at.is_(None),
                )
            ).first()
            return ExportWithFile(*row) if row else None

    def set_thumbnail(self, owner_user_id: int, presentation_id: str, file_id: str) -> str | None:
        with self._session_factory.begin() as db:
            presentation = db.scalar(select(Presentation).where(
                Presentation.id == presentation_id,
                Presentation.owner_user_id == owner_user_id,
                Presentation.deleted_at.is_(None),
            ).with_for_update())
            if presentation is None:
                raise ExportNotFound
            file = db.scalar(select(StoredFile.id).where(
                StoredFile.id == file_id,
                StoredFile.owner_user_id == owner_user_id,
                StoredFile.presentation_id == presentation_id,
                StoredFile.purpose == "thumbnail",
                StoredFile.status == "active",
                StoredFile.deleted_at.is_(None),
            ))
            if file is None:
                raise ExportNotFound
            previous = presentation.thumbnail_file_id
            presentation.thumbnail_file_id = file_id
            return previous

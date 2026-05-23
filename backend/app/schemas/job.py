from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel

from app.db.models.enums import JobStatus, SourceType
from app.db.models.job import Job


class JobRead(BaseModel):
    id: UUID
    source_type: SourceType
    source_url: str | None
    original_filename: str
    duration_seconds: float | None
    status: JobStatus
    progress_pct: int
    progress_message: str
    detection_config: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, job: Job) -> Self:
        return cls(
            id=job.id,
            source_type=job.source_type,
            source_url=job.source_url,
            original_filename=job.original_filename,
            duration_seconds=job.duration_seconds,
            status=job.status,
            progress_pct=job.progress_pct,
            progress_message=job.progress_message,
            detection_config=job.detection_config,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


class JobListItem(BaseModel):
    id: UUID
    source_type: SourceType
    original_filename: str
    status: JobStatus
    progress_pct: int
    created_at: datetime

    @classmethod
    def from_model(cls, job: Job) -> Self:
        return cls(
            id=job.id,
            source_type=job.source_type,
            original_filename=job.original_filename,
            status=job.status,
            progress_pct=job.progress_pct,
            created_at=job.created_at,
        )


class JobListResponse(BaseModel):
    items: list[JobListItem]
    total: int
    page: int
    page_size: int

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.db.models.clip import ClipCandidate
from app.db.models.enums import ClipStatus, DetectionStrategy


class ClipRead(BaseModel):
    id: UUID
    job_id: UUID
    start_seconds: float
    end_seconds: float
    user_start_seconds: float | None
    user_end_seconds: float | None
    detection_strategy: DetectionStrategy
    score: float
    reason: str
    transcript_excerpt: str | None
    status: ClipStatus
    exported_paths: dict[str, str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, clip: ClipCandidate) -> Self:
        return cls(
            id=clip.id,
            job_id=clip.job_id,
            start_seconds=clip.start_seconds,
            end_seconds=clip.end_seconds,
            user_start_seconds=clip.user_start_seconds,
            user_end_seconds=clip.user_end_seconds,
            detection_strategy=clip.detection_strategy,
            score=clip.score,
            reason=clip.reason,
            transcript_excerpt=clip.transcript_excerpt,
            status=clip.status,
            exported_paths=clip.exported_paths,
            created_at=clip.created_at,
            updated_at=clip.updated_at,
        )


class ClipUpdate(BaseModel):
    user_start_seconds: float | None = None
    user_end_seconds: float | None = None
    status: ClipStatus | None = None

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if (
            self.user_start_seconds is not None
            and self.user_end_seconds is not None
            and self.user_start_seconds >= self.user_end_seconds
        ):
            raise ValueError("user_start_seconds harus lebih kecil dari user_end_seconds")
        # User hanya boleh set status review-level lewat PATCH.
        if self.status is not None and self.status not in {
            ClipStatus.pending,
            ClipStatus.selected,
            ClipStatus.rejected,
        }:
            raise ValueError("status hanya boleh pending/selected/rejected via PATCH")
        return self

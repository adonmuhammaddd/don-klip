import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import ClipStatus, DetectionStrategy


class ClipCandidate(Base):
    __tablename__ = "clip_candidates"
    __table_args__ = (
        Index("ix_clip_candidates_job_status", "job_id", "status"),
        Index("ix_clip_candidates_job_start", "job_id", "start_seconds"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    user_start_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_end_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    detection_strategy: Mapped[DetectionStrategy] = mapped_column(
        Enum(DetectionStrategy, name="detection_strategy")
    )
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, default="")
    transcript_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ClipStatus] = mapped_column(
        Enum(ClipStatus, name="clip_status"), default=ClipStatus.pending
    )
    # { "9_16": path, "1_1": path, "srt": path }
    exported_paths: Mapped[dict[str, str]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

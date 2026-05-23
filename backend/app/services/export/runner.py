from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.config import get_settings
from app.db.models.clip import ClipCandidate
from app.db.models.enums import ClipStatus
from app.db.models.job import Job
from app.db.models.transcript import Transcript
from app.db.session import SessionLocal
from app.services.export.exporter import export_clip
from app.services.ffmpeg.runner import FfmpegRunner


async def run_clip_export(clip_id: UUID) -> None:
    """Entry point BackgroundTasks: export satu klip (9:16, 1:1, SRT)."""
    settings = get_settings()
    async with SessionLocal() as session:
        clip = await session.get(ClipCandidate, clip_id)
        if clip is None:
            return
        job = await session.get(Job, clip.job_id)
        if job is None or job.source_path is None:
            clip.status = ClipStatus.failed
            await session.commit()
            return

        transcript = (
            await session.execute(select(Transcript).where(Transcript.job_id == job.id))
        ).scalar_one_or_none()
        segments = transcript.segments if transcript is not None else []

        clip.status = ClipStatus.exporting
        await session.commit()

        try:
            paths = await export_clip(
                clip=clip,
                source_path=Path(job.source_path),
                segments=segments,
                outputs_dir=Path(settings.outputs_dir),
                ffmpeg=FfmpegRunner(),
            )
            clip.exported_paths = paths
            clip.status = ClipStatus.exported
            await session.commit()
        except Exception:  # kegagalan export apa pun → status failed
            await session.rollback()
            clip.status = ClipStatus.failed
            await session.commit()

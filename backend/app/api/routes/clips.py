import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import SessionDep
from app.db.models.clip import ClipCandidate
from app.db.models.job import Job
from app.db.models.transcript import Transcript
from app.schemas.clip import ClipRead, ClipUpdate
from app.schemas.transcript import TranscriptRead
from app.services.export.runner import run_clip_export

router = APIRouter(tags=["clips"])


@router.get("/jobs/{job_id}/clips", response_model=list[ClipRead])
async def list_clips(job_id: UUID, session: SessionDep) -> list[ClipRead]:
    rows = (
        await session.execute(
            select(ClipCandidate)
            .where(ClipCandidate.job_id == job_id)
            .order_by(ClipCandidate.score.desc())
        )
    ).scalars().all()
    return [ClipRead.from_model(clip) for clip in rows]


@router.get("/jobs/{job_id}/transcript", response_model=TranscriptRead)
async def get_transcript(job_id: UUID, session: SessionDep) -> TranscriptRead:
    transcript = (
        await session.execute(select(Transcript).where(Transcript.job_id == job_id))
    ).scalar_one_or_none()
    if transcript is None:
        raise HTTPException(status_code=404, detail="transcript belum tersedia")
    return TranscriptRead.from_model(transcript)


@router.patch("/clips/{clip_id}", response_model=ClipRead)
async def update_clip(clip_id: UUID, payload: ClipUpdate, session: SessionDep) -> ClipRead:
    clip = await session.get(ClipCandidate, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="clip tidak ditemukan")

    if payload.user_start_seconds is not None:
        clip.user_start_seconds = payload.user_start_seconds
    if payload.user_end_seconds is not None:
        clip.user_end_seconds = payload.user_end_seconds
    if payload.status is not None:
        clip.status = payload.status

    await session.commit()
    await session.refresh(clip)
    return ClipRead.from_model(clip)


@router.get("/clips/{clip_id}/preview")
async def preview_clip(clip_id: UUID, session: SessionDep) -> FileResponse:
    """Stream source video parent job (range request) untuk player + trim (§4)."""
    clip = await session.get(ClipCandidate, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="clip tidak ditemukan")
    job = await session.get(Job, clip.job_id)
    if job is None or job.source_path is None:
        raise HTTPException(status_code=404, detail="source video belum tersedia")

    path = Path(job.source_path)
    if not await asyncio.to_thread(path.is_file):
        raise HTTPException(status_code=404, detail="file source tidak ditemukan")
    # FileResponse menangani Range request (206) secara otomatis.
    return FileResponse(path)


@router.post("/clips/{clip_id}/export", response_model=ClipRead, status_code=202)
async def export_clip_endpoint(
    clip_id: UUID, background: BackgroundTasks, session: SessionDep
) -> ClipRead:
    clip = await session.get(ClipCandidate, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="clip tidak ditemukan")
    background.add_task(run_clip_export, clip_id)
    return ClipRead.from_model(clip)

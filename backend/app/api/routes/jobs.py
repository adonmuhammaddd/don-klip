import asyncio
import shutil
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.config import get_settings
from app.db.models.enums import JobStatus, SourceType
from app.db.models.job import Job
from app.schemas.detection import DetectionConfigDTO
from app.schemas.job import JobListItem, JobListResponse, JobRead
from app.services.source.local_upload import ALLOWED_EXTENSIONS
from app.workers.job_runner import run_job

router = APIRouter(tags=["jobs"])


def _parse_detection_config(raw: Any) -> DetectionConfigDTO:
    try:
        if isinstance(raw, str):
            return DetectionConfigDTO.model_validate_json(raw)
        return DetectionConfigDTO.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"detection_config tidak valid: {exc.errors()}") from exc


def _save_upload(src: BinaryIO, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.seek(0)
    with dest.open("wb") as out:
        shutil.copyfileobj(src, out)


def _cleanup_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


@router.post("/jobs", response_model=JobRead, status_code=201)
async def create_job(
    request: Request, background: BackgroundTasks, session: SessionDep
) -> JobRead:
    settings = get_settings()
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        payload = await request.json()
        source_url = payload.get("source_url")
        if not isinstance(source_url, str) or not source_url.strip():
            raise HTTPException(status_code=422, detail="source_url wajib untuk job URL")
        config = _parse_detection_config(payload.get("detection_config"))
        job = Job(
            source_type=SourceType.url,
            source_url=source_url.strip(),
            original_filename=source_url.strip(),
            detection_config=config.model_dump(mode="json"),
            status=JobStatus.pending,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

    elif content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(status_code=422, detail="field 'file' wajib untuk upload")
        config = _parse_detection_config(form.get("detection_config"))

        ext = Path(upload.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=422, detail=f"ekstensi tidak didukung: {ext}")

        job = Job(
            source_type=SourceType.upload,
            original_filename=upload.filename or f"source{ext}",
            detection_config=config.model_dump(mode="json"),
            status=JobStatus.pending,
        )
        session.add(job)
        await session.flush()  # dapatkan job.id sebelum simpan file

        dest = Path(settings.uploads_dir) / str(job.id) / f"source{ext}"
        await asyncio.to_thread(_save_upload, upload.file, dest)
        size = await asyncio.to_thread(lambda: dest.stat().st_size)
        if size > settings.max_upload_mb * 1024 * 1024:
            await asyncio.to_thread(_cleanup_dir, dest.parent)
            raise HTTPException(status_code=413, detail=f"file melebihi {settings.max_upload_mb}MB")
        job.source_path = str(dest)
        await session.commit()
        await session.refresh(job)

    else:
        raise HTTPException(
            status_code=415,
            detail="content-type harus multipart/form-data atau application/json",
        )

    background.add_task(run_job, job.id)
    return JobRead.from_model(job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(session: SessionDep, page: int = 1, page_size: int = 20) -> JobListResponse:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    total = (await session.execute(select(func.count()).select_from(Job))).scalar_one()
    rows = (
        await session.execute(
            select(Job)
            .order_by(Job.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return JobListResponse(
        items=[JobListItem.from_model(job) for job in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job(job_id: UUID, session: SessionDep) -> JobRead:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job tidak ditemukan")
    return JobRead.from_model(job)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: UUID, session: SessionDep) -> None:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job tidak ditemukan")
    settings = get_settings()
    await session.delete(job)  # cascade ke transcripts & clip_candidates
    await session.commit()
    await asyncio.to_thread(_cleanup_dir, Path(settings.uploads_dir) / str(job_id))
    await asyncio.to_thread(_cleanup_dir, Path(settings.outputs_dir) / str(job_id))

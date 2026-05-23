from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.clip import ClipCandidate
from app.db.models.enums import ClipStatus, JobStatus
from app.db.models.job import Job
from app.db.models.transcript import Transcript
from app.db.session import SessionLocal
from app.services.detection.audio_spike import AudioSpikeDetector
from app.services.detection.base import DetectedMoment, DetectionContext
from app.services.errors import JobCancelledError
from app.services.ffmpeg.runner import FfmpegRunner
from app.services.progress.tracker import ProgressTracker
from app.services.source.factory import get_source_provider
from app.services.transcription.base import TranscriptResult
from app.services.transcription.whisper_cpp import get_transcriber


async def run_pipeline(job_id: UUID) -> None:
    """Orchestrator: jalankan semua stage untuk satu job (§9).

    Dipakai oleh BackgroundTasks → buka session sendiri (bukan session request).
    """
    settings = get_settings()
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        tracker = ProgressTracker(session, job)
        try:
            await _run_stages(session, job, tracker, settings)
        except JobCancelledError:
            await tracker.finish_cancelled()
        except Exception as exc:  # semua kegagalan stage → status failed
            await tracker.fail(str(exc))


async def _run_stages(
    session: AsyncSession, job: Job, tracker: ProgressTracker, settings: Settings
) -> None:
    ffmpeg = FfmpegRunner()
    work_dir = Path(settings.uploads_dir) / str(job.id)

    # Stage 1: acquire source
    await tracker.update(5, "Mengambil sumber video...", JobStatus.downloading)
    acquired = await get_source_provider(job, settings).acquire(job)
    job.source_path = acquired.source_path
    job.original_filename = acquired.original_filename
    await session.commit()
    source_path = Path(acquired.source_path)

    # Stage 2: probe
    await tracker.update(15, "Membaca metadata video...", JobStatus.transcribing)
    probe = await ffmpeg.probe(source_path)
    job.duration_seconds = probe.duration_seconds
    await session.commit()

    # Stage 3: extract audio (mono 16kHz untuk whisper + audio spike)
    await tracker.update(25, "Mengekstrak audio...")
    audio_path = work_dir / "audio.wav"
    await ffmpeg.extract_audio(source_path, audio_path)

    # Stage 4: transcribe → simpan transcript
    await tracker.update(45, "Transcribing (whisper.cpp)...")
    transcript = await get_transcriber(settings).transcribe(audio_path)
    await _save_transcript(session, job, transcript)

    # Stage 6: detect (Sprint 2: audio spike saja; aggregator multi-strategy di Sprint 4)
    await tracker.update(70, "Mendeteksi momen menarik...", JobStatus.detecting)
    moments = await _run_audio_spike(
        job, source_path, audio_path, probe.duration_seconds, transcript, settings
    )

    # Stage 7: simpan kandidat (cap MAX_CANDIDATES_PER_JOB)
    await tracker.update(90, "Menyimpan kandidat klip...")
    top = sorted(moments, key=lambda m: m.score, reverse=True)[: settings.max_candidates_per_job]
    _save_candidates(session, job, top)
    await session.commit()

    # Stage 8: selesai
    await tracker.update(100, "Siap direview", JobStatus.ready_for_review)


async def _run_audio_spike(
    job: Job,
    source_path: Path,
    audio_path: Path,
    duration: float,
    transcript: TranscriptResult,
    settings: Settings,
) -> list[DetectedMoment]:
    cfg: dict[str, Any] = job.detection_config.get("audio_spike") or {}
    std = float(cfg.get("std_multiplier", settings.audio_spike_std_multiplier))
    ctx = DetectionContext(
        video_path=source_path,
        audio_path=audio_path,
        duration_seconds=duration,
        transcript=transcript,
        config=job.detection_config,
    )
    return await AudioSpikeDetector(std_multiplier=std).detect(ctx)


async def _save_transcript(session: AsyncSession, job: Job, result: TranscriptResult) -> None:
    segments = [
        {"start": s.start, "end": s.end, "text": s.text, "confidence": s.confidence}
        for s in result.segments
    ]
    session.add(Transcript(job_id=job.id, segments=segments, language=result.language))
    await session.commit()


def _save_candidates(session: AsyncSession, job: Job, moments: list[DetectedMoment]) -> None:
    for moment in moments:
        session.add(
            ClipCandidate(
                job_id=job.id,
                start_seconds=moment.start,
                end_seconds=moment.end,
                detection_strategy=moment.strategy,
                score=moment.score,
                reason=moment.reason,
                transcript_excerpt=moment.transcript_excerpt,
                status=ClipStatus.pending,
            )
        )

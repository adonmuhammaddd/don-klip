import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.clip import ClipCandidate
from app.db.models.enums import ClipStatus, JobStatus
from app.db.models.job import Job
from app.db.models.transcript import Transcript
from app.db.session import SessionLocal
from app.schemas.detection import (
    AudioSpikeStrategy,
    DetectionConfigDTO,
    LlmTranscriptStrategy,
    ManualMarkerStrategy,
    TwitchChatStrategy,
)
from app.services.chat.base import ChatMessage
from app.services.chat.twitch import TwitchChatFetcher
from app.services.detection.aggregator import aggregate
from app.services.detection.audio_spike import AudioSpikeDetector
from app.services.detection.base import DetectedMoment, DetectionContext, MomentDetector
from app.services.detection.llm_transcript import LlmTranscriptDetector
from app.services.detection.manual_marker import ManualMarkerDetector
from app.services.detection.twitch_chat import ChatDensityDetector
from app.services.errors import ChatError, JobCancelledError
from app.services.ffmpeg.runner import FfmpegRunner
from app.services.llm.factory import get_llm_provider
from app.services.progress.tracker import ProgressTracker
from app.services.source.base import AcquiredSource
from app.services.source.factory import get_source_provider
from app.services.transcription.base import TranscriptResult
from app.services.transcription.whisper_cpp import get_transcriber

logger = logging.getLogger(__name__)


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
    config = DetectionConfigDTO.model_validate(job.detection_config)

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

    # Stage 5: fetch chat Twitch (kalau strategy aktif & ini VOD Twitch)
    chat_log = await _maybe_fetch_chat(tracker, config, acquired, settings)

    # Stage 6: detect (semua strategi aktif via aggregator)
    await tracker.update(75, "Mendeteksi momen menarik...", JobStatus.detecting)
    ctx = DetectionContext(
        video_path=source_path,
        audio_path=audio_path,
        duration_seconds=probe.duration_seconds,
        transcript=transcript,
        chat_log=chat_log,
        config=job.detection_config,
    )
    detectors = _build_detectors(config, settings)
    moments = await aggregate(detectors, ctx, max_candidates=settings.max_candidates_per_job)

    # Stage 7: simpan kandidat (sudah ter-merge, sort, & cap oleh aggregator)
    await tracker.update(90, "Menyimpan kandidat klip...")
    _save_candidates(session, job, moments)
    await session.commit()

    # Stage 8: selesai
    await tracker.update(100, "Siap direview", JobStatus.ready_for_review)


async def _maybe_fetch_chat(
    tracker: ProgressTracker,
    config: DetectionConfigDTO,
    acquired: AcquiredSource,
    settings: Settings,
) -> list[ChatMessage] | None:
    wants_chat = any(isinstance(s, TwitchChatStrategy) for s in config.strategies)
    if not wants_chat or not acquired.twitch_video_id:
        return None
    await tracker.update(60, "Mengambil chat Twitch...")
    try:
        return await TwitchChatFetcher(settings.twitch_client_id).fetch(acquired.twitch_video_id)
    except ChatError as exc:
        # Non-fatal: lanjut tanpa chat density.
        logger.warning("fetch chat Twitch gagal: %s", exc)
        return None


def _build_detectors(config: DetectionConfigDTO, settings: Settings) -> list[MomentDetector]:
    detectors: list[MomentDetector] = []
    for strategy in config.strategies:
        match strategy:
            case AudioSpikeStrategy():
                detectors.append(AudioSpikeDetector(std_multiplier=strategy.std_multiplier))
            case LlmTranscriptStrategy():
                detectors.append(LlmTranscriptDetector(get_llm_provider(settings)))
            case TwitchChatStrategy():
                detectors.append(ChatDensityDetector())
            case ManualMarkerStrategy():
                detectors.append(ManualMarkerDetector(markers=strategy.markers))
    return detectors


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

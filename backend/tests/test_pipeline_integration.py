"""Integration test pipeline: ffmpeg asli + DB asli, transcriber di-mock.

Skip otomatis kalau ffmpeg / DATABASE_URL tidak tersedia (mis. di unit-test env).
Whisper sengaja di-mock supaya tidak butuh download model.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db.models.clip import ClipCandidate
from app.db.models.enums import JobStatus, SourceType
from app.db.models.job import Job
from app.db.models.transcript import Transcript
from app.db.session import SessionLocal
from app.services.ffmpeg.runner import FfmpegRunner
from app.services.pipeline import pipeline
from app.services.transcription.base import Transcriber, TranscriptResult

pytestmark = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and os.environ.get("DATABASE_URL")),
    reason="butuh ffmpeg + DATABASE_URL",
)


class _FakeTranscriber(Transcriber):
    async def transcribe(self, audio_path: Path) -> TranscriptResult:
        return TranscriptResult(language="en", segments=[])


def _make_clip(path: Path) -> None:
    """Video 20s + sine audio, dengan burst keras di detik 10-12 (→ audio spike)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=20",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=20",
            "-af", "volume=enable='between(t,10,12)':volume=18",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


async def test_ffmpeg_probe_and_extract_audio(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    _make_clip(clip)
    ffmpeg = FfmpegRunner()

    probe = await ffmpeg.probe(clip)
    assert probe.duration_seconds == pytest.approx(20.0, abs=1.0)
    assert probe.video_codec == "h264"

    wav = tmp_path / "audio.wav"
    await ffmpeg.extract_audio(clip, wav)
    assert wav.is_file() and wav.stat().st_size > 0


async def test_run_pipeline_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "get_transcriber", lambda settings: _FakeTranscriber())
    settings = get_settings()

    async with SessionLocal() as session:
        job = Job(
            source_type=SourceType.upload,
            original_filename="clip.mp4",
            detection_config={"strategies": [{"strategy": "audio_spike", "std_multiplier": 2.0}]},
            status=JobStatus.pending,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id
        clip = Path(settings.uploads_dir) / str(job_id) / "source.mp4"
        _make_clip(clip)
        job.source_path = str(clip)
        await session.commit()

    await pipeline.run_pipeline(job_id)

    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        assert job is not None
        assert job.status == JobStatus.ready_for_review
        assert job.progress_pct == 100
        assert job.duration_seconds == pytest.approx(20.0, abs=1.0)

        transcript = (
            await session.execute(select(Transcript).where(Transcript.job_id == job_id))
        ).scalar_one()
        assert transcript.language == "en"

        candidates = (
            await session.execute(select(ClipCandidate).where(ClipCandidate.job_id == job_id))
        ).scalars().all()
        # Burst 10-12s harus terdeteksi sebagai minimal satu kandidat.
        assert len(candidates) >= 1

        await session.delete(job)
        await session.commit()

"""API test untuk clip & transcript endpoints (DB asli, tanpa pipeline/ffmpeg)."""

import os

import httpx
import pytest
from httpx import ASGITransport

from app.db.models.clip import ClipCandidate
from app.db.models.enums import ClipStatus, DetectionStrategy, JobStatus, SourceType
from app.db.models.job import Job
from app.db.models.transcript import Transcript
from app.db.session import SessionLocal
from app.main import app

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="butuh DATABASE_URL")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_clip_list_patch_and_transcript() -> None:
    async with SessionLocal() as session:
        job = Job(
            source_type=SourceType.upload,
            original_filename="x.mp4",
            detection_config={"strategies": [{"strategy": "audio_spike"}]},
            status=JobStatus.ready_for_review,
        )
        session.add(job)
        await session.flush()
        session.add(
            Transcript(
                job_id=job.id,
                segments=[{"start": 0.0, "end": 1.0, "text": "halo", "confidence": None}],
                language="en",
            )
        )
        session.add(
            ClipCandidate(
                job_id=job.id,
                start_seconds=10.0,
                end_seconds=20.0,
                detection_strategy=DetectionStrategy.audio_spike,
                score=0.9,
                reason="audio spike",
                status=ClipStatus.pending,
            )
        )
        await session.commit()
        job_id = job.id

    async with _client() as client:
        listed = await client.get(f"/api/jobs/{job_id}/clips")
        assert listed.status_code == 200
        clips = listed.json()
        assert len(clips) == 1
        clip_id = clips[0]["id"]

        patched = await client.patch(
            f"/api/clips/{clip_id}",
            json={"user_start_seconds": 12.0, "user_end_seconds": 18.0, "status": "selected"},
        )
        assert patched.status_code == 200
        body = patched.json()
        assert body["status"] == "selected"
        assert body["user_start_seconds"] == 12.0

        invalid = await client.patch(
            f"/api/clips/{clip_id}",
            json={"user_start_seconds": 18.0, "user_end_seconds": 12.0},
        )
        assert invalid.status_code == 422

        transcript = await client.get(f"/api/jobs/{job_id}/transcript")
        assert transcript.status_code == 200
        assert transcript.json()["language"] == "en"

    async with SessionLocal() as session:
        job_row = await session.get(Job, job_id)
        if job_row is not None:
            await session.delete(job_row)
            await session.commit()

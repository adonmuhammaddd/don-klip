"""API test untuk Job CRUD via httpx ASGI. BackgroundTasks di-noop-kan.

Skip kalau DATABASE_URL tidak ada (butuh Postgres asli).
"""

import json
import os
from collections.abc import Iterator
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport

from app.api.routes import jobs as jobs_route
from app.db.models.enums import JobStatus, SourceType
from app.db.models.job import Job
from app.db.session import SessionLocal
from app.main import app

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="butuh DATABASE_URL")

_CONFIG = {"strategies": [{"strategy": "audio_spike"}]}


async def _make_job(status: JobStatus) -> UUID:
    async with SessionLocal() as session:
        job = Job(
            source_type=SourceType.upload,
            original_filename="x.mp4",
            detection_config=_CONFIG,
            status=status,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job.id


async def _delete_job(job_id: UUID) -> None:
    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is not None:
            await session.delete(job)
            await session.commit()


@pytest.fixture
def _noop_run_job(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    async def _noop(job_id: UUID) -> None:
        return None

    monkeypatch.setattr(jobs_route, "run_job", _noop)
    yield


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_create_url_job_full_crud(_noop_run_job: None) -> None:
    async with _client() as client:
        resp = await client.post(
            "/api/jobs",
            json={
                "source_url": "https://youtu.be/example",
                "detection_config": {"strategies": [{"strategy": "audio_spike"}]},
            },
        )
        assert resp.status_code == 201
        job = resp.json()
        assert job["status"] == "pending"
        assert job["source_type"] == "url"
        job_id = job["id"]

        listed = await client.get("/api/jobs")
        assert listed.status_code == 200
        assert any(item["id"] == job_id for item in listed.json()["items"])

        detail = await client.get(f"/api/jobs/{job_id}")
        assert detail.status_code == 200

        deleted = await client.delete(f"/api/jobs/{job_id}")
        assert deleted.status_code == 204

        gone = await client.get(f"/api/jobs/{job_id}")
        assert gone.status_code == 404


async def test_create_upload_job_multipart(_noop_run_job: None) -> None:
    # Regresi: form.get("file") mengembalikan starlette.UploadFile, harus lolos isinstance.
    async with _client() as client:
        resp = await client.post(
            "/api/jobs",
            files={"file": ("clip.mp4", b"\x00\x00fakevideo", "video/mp4")},
            data={"detection_config": json.dumps(_CONFIG)},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["source_type"] == "upload"
        assert body["original_filename"] == "clip.mp4"
    await _delete_job(UUID(body["id"]))


async def test_invalid_detection_config_returns_422(_noop_run_job: None) -> None:
    async with _client() as client:
        resp = await client.post(
            "/api/jobs",
            json={"source_url": "https://x.test", "detection_config": {"strategies": []}},
        )
        assert resp.status_code == 422


async def test_missing_source_url_returns_422(_noop_run_job: None) -> None:
    async with _client() as client:
        resp = await client.post(
            "/api/jobs",
            json={"detection_config": {"strategies": [{"strategy": "audio_spike"}]}},
        )
        assert resp.status_code == 422


async def test_cancel_in_progress_job() -> None:
    job_id = await _make_job(JobStatus.downloading)
    try:
        async with _client() as client:
            resp = await client.post(f"/api/jobs/{job_id}/cancel")
            assert resp.status_code == 200
            assert resp.json()["status"] == "cancelled"
    finally:
        await _delete_job(job_id)


async def test_cancel_ready_job_conflict() -> None:
    job_id = await _make_job(JobStatus.ready_for_review)
    try:
        async with _client() as client:
            resp = await client.post(f"/api/jobs/{job_id}/cancel")
            assert resp.status_code == 409
    finally:
        await _delete_job(job_id)


async def test_retry_failed_job(_noop_run_job: None) -> None:
    job_id = await _make_job(JobStatus.failed)
    try:
        async with _client() as client:
            resp = await client.post(f"/api/jobs/{job_id}/retry")
            assert resp.status_code == 202
            body = resp.json()
            assert body["status"] == "pending"
            assert body["progress_pct"] == 0
    finally:
        await _delete_job(job_id)


async def test_retry_ready_job_conflict(_noop_run_job: None) -> None:
    job_id = await _make_job(JobStatus.ready_for_review)
    try:
        async with _client() as client:
            resp = await client.post(f"/api/jobs/{job_id}/retry")
            assert resp.status_code == 409
    finally:
        await _delete_job(job_id)

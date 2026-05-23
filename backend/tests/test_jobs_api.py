"""API test untuk Job CRUD via httpx ASGI. BackgroundTasks di-noop-kan.

Skip kalau DATABASE_URL tidak ada (butuh Postgres asli).
"""

import os
from collections.abc import Iterator
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport

from app.api.routes import jobs as jobs_route
from app.main import app

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="butuh DATABASE_URL")


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

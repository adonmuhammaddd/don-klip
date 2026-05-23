from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import JobStatus
from app.db.models.job import Job
from app.services.errors import JobCancelledError


class ProgressTracker:
    """Update progress job di DB + cek cancellation di tiap stage (§9)."""

    def __init__(self, session: AsyncSession, job: Job) -> None:
        self._session = session
        self._job = job

    async def update(self, pct: int, message: str, status: JobStatus | None = None) -> None:
        await self.ensure_not_cancelled()
        self._job.progress_pct = pct
        self._job.progress_message = message
        if status is not None:
            self._job.status = status
        await self._session.commit()

    async def ensure_not_cancelled(self) -> None:
        # Baca status langsung dari DB (cancel di-commit oleh session lain).
        result = await self._session.execute(select(Job.status).where(Job.id == self._job.id))
        if result.scalar_one() == JobStatus.cancelled:
            raise JobCancelledError(f"job {self._job.id} dibatalkan")

    async def fail(self, error: str) -> None:
        await self._session.rollback()
        self._job.status = JobStatus.failed
        self._job.error_message = error
        self._job.progress_message = "Gagal"
        await self._session.commit()

    async def finish_cancelled(self) -> None:
        await self._session.rollback()
        self._job.progress_message = "Dibatalkan"
        await self._session.commit()

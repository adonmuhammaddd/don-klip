import asyncio
from pathlib import Path

from app.config import Settings
from app.db.models.job import Job
from app.services.errors import SourceError
from app.services.source.base import AcquiredSource, SourceProvider

ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm"}


class LocalUploadProvider(SourceProvider):
    """Validasi file upload yang sudah disimpan route create job di source_path."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def acquire(self, job: Job) -> AcquiredSource:
        if job.source_path is None:
            raise SourceError("upload job tidak punya source_path")
        # Validasi menyentuh filesystem (blocking) → jalankan di thread.
        return await asyncio.to_thread(self._validate, job.source_path, job.original_filename)

    def _validate(self, source_path: str, original_filename: str) -> AcquiredSource:
        path = Path(source_path)
        if not path.is_file():
            raise SourceError(f"file upload tidak ditemukan: {path}")
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise SourceError(f"ekstensi tidak didukung: {path.suffix}")

        max_bytes = self._settings.max_upload_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            raise SourceError(f"file melebihi limit {self._settings.max_upload_mb}MB")

        return AcquiredSource(source_path=str(path), original_filename=original_filename)

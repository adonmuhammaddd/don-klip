from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.db.models.job import Job


@dataclass(frozen=True)
class AcquiredSource:
    """Hasil acquisition: lokasi file source + metadata."""

    source_path: str
    original_filename: str
    twitch_video_id: str | None = None


class SourceProvider(ABC):
    @abstractmethod
    async def acquire(self, job: Job) -> AcquiredSource: ...

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.db.models.enums import DetectionStrategy
from app.services.transcription.base import TranscriptResult


@dataclass(frozen=True)
class DetectedMoment:
    """Kandidat momen dari satu detector (value object, bukan DB model).

    Di-map ke ClipCandidate (DB) oleh pipeline / aggregator.
    """

    start: float
    end: float
    score: float
    reason: str
    strategy: DetectionStrategy
    transcript_excerpt: str | None = None


@dataclass
class DetectionContext:
    """Input bersama untuk semua detector (§5).

    chat_log & manual_markers ditambahkan di Sprint 4 saat strateginya masuk.
    """

    video_path: Path
    audio_path: Path
    duration_seconds: float
    transcript: TranscriptResult | None = None
    config: dict[str, Any] = field(default_factory=dict)


class MomentDetector(ABC):
    strategy: DetectionStrategy

    @abstractmethod
    async def detect(self, ctx: DetectionContext) -> list[DetectedMoment]: ...

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.db.models.enums import DetectionStrategy
from app.services.chat.base import ChatMessage
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
    """Input bersama untuk semua detector (§5)."""

    video_path: Path
    audio_path: Path
    duration_seconds: float
    transcript: TranscriptResult | None = None
    chat_log: list[ChatMessage] | None = None
    config: dict[str, Any] = field(default_factory=dict)


class MomentDetector(ABC):
    strategy: DetectionStrategy

    @abstractmethod
    async def detect(self, ctx: DetectionContext) -> list[DetectedMoment]: ...


def excerpt_for_range(
    transcript: TranscriptResult | None, start: float, end: float
) -> str | None:
    """Gabungkan teks transcript yang overlap dengan rentang [start, end]."""
    if transcript is None:
        return None
    texts = [
        seg.text
        for seg in transcript.segments
        if seg.end > start and seg.start < end and seg.text
    ]
    joined = " ".join(texts).strip()
    return joined or None

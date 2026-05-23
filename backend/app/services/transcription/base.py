from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    confidence: float | None = None


@dataclass(frozen=True)
class TranscriptResult:
    language: str
    segments: list[TranscriptSegment]


class Transcriber(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> TranscriptResult: ...

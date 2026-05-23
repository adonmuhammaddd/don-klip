from typing import Self

from pydantic import BaseModel

from app.db.models.transcript import Transcript


class TranscriptSegmentDTO(BaseModel):
    start: float
    end: float
    text: str
    confidence: float | None = None


class TranscriptRead(BaseModel):
    job_id: str
    language: str
    segments: list[TranscriptSegmentDTO]

    @classmethod
    def from_model(cls, transcript: Transcript) -> Self:
        return cls(
            job_id=str(transcript.job_id),
            language=transcript.language,
            segments=[TranscriptSegmentDTO.model_validate(seg) for seg in transcript.segments],
        )

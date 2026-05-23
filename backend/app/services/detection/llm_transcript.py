from typing import Any

from app.db.models.enums import DetectionStrategy
from app.services.detection.base import (
    DetectedMoment,
    DetectionContext,
    MomentDetector,
    excerpt_for_range,
)
from app.services.detection.dedupe import dedupe_moments
from app.services.llm.base import LLMProvider
from app.services.llm.prompts import load_prompt
from app.services.transcription.base import TranscriptSegment

WINDOW_SEC = 120.0
OVERLAP_SEC = 15.0

LLM_MOMENTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "moments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_sec": {"type": "number"},
                    "end_sec": {"type": "number"},
                    "reason": {"type": "string"},
                    "score": {"type": "number"},
                },
                "required": ["start_sec", "end_sec", "reason", "score"],
            },
        }
    },
    "required": ["moments"],
}


class LlmTranscriptDetector(MomentDetector):
    """Deteksi momen menarik dari transcript via LLM, per chunk ~2 menit (§5.2)."""

    strategy = DetectionStrategy.llm_transcript

    def __init__(self, provider: LLMProvider, model: str | None = None) -> None:
        self._provider = provider
        self._model = model
        self._template = load_prompt("llm_transcript")

    async def detect(self, ctx: DetectionContext) -> list[DetectedMoment]:
        transcript = ctx.transcript
        if transcript is None or not transcript.segments:
            return []

        moments: list[DetectedMoment] = []
        for chunk in _chunk(transcript.segments):
            data = await self._provider.complete_json(
                self._build_prompt(chunk), LLM_MOMENTS_SCHEMA, model=self._model
            )
            moments.extend(self._parse(data, ctx))
        return dedupe_moments(moments)

    def _build_prompt(self, chunk: list[TranscriptSegment]) -> str:
        lines = "\n".join(
            f"[{seg.start:.1f}-{seg.end:.1f}] {seg.text}" for seg in chunk if seg.text.strip()
        )
        return self._template.format(transcript=lines)

    def _parse(self, data: dict[str, Any], ctx: DetectionContext) -> list[DetectedMoment]:
        out: list[DetectedMoment] = []
        for item in data.get("moments", []):
            try:
                start = max(0.0, float(item["start_sec"]))
                end = min(ctx.duration_seconds, float(item["end_sec"]))
            except (KeyError, TypeError, ValueError):
                continue
            if end <= start:
                continue
            score = min(1.0, max(0.0, float(item.get("score", 0.5))))
            reason = str(item.get("reason", "")).strip() or "Momen menarik (LLM)"
            out.append(
                DetectedMoment(
                    start=start,
                    end=end,
                    score=score,
                    reason=reason,
                    strategy=self.strategy,
                    transcript_excerpt=excerpt_for_range(ctx.transcript, start, end),
                )
            )
        return out


def _chunk(segments: list[TranscriptSegment]) -> list[list[TranscriptSegment]]:
    step = WINDOW_SEC - OVERLAP_SEC
    total_end = segments[-1].end
    chunks: list[list[TranscriptSegment]] = []
    t = 0.0
    while t < total_end:
        window = [seg for seg in segments if seg.end > t and seg.start < t + WINDOW_SEC]
        if window:
            chunks.append(window)
        t += step
    return chunks

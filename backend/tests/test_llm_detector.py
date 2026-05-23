from pathlib import Path
from typing import Any

from app.services.detection.base import DetectionContext
from app.services.detection.llm_transcript import LlmTranscriptDetector
from app.services.llm.base import LLMProvider
from app.services.transcription.base import TranscriptResult, TranscriptSegment


class _FakeLLM(LLMProvider):
    def __init__(self, moments: list[dict[str, Any]]) -> None:
        self._moments = moments
        self.calls = 0

    async def complete_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        self.calls += 1
        return {"moments": self._moments}


def _transcript(seconds: int) -> TranscriptResult:
    segs = [
        TranscriptSegment(start=float(i * 10), end=float(i * 10 + 10), text=f"baris {i}")
        for i in range(seconds // 10)
    ]
    return TranscriptResult(language="id", segments=segs)


def _ctx(transcript: TranscriptResult | None, duration: float) -> DetectionContext:
    return DetectionContext(
        video_path=Path("v.mp4"),
        audio_path=Path("a.wav"),
        duration_seconds=duration,
        transcript=transcript,
    )


async def test_llm_detector_parses_and_dedupes() -> None:
    # Transcript 200s → 2 chunk (window 120, step 105). Fake balikin momen sama tiap chunk.
    fake = _FakeLLM([{"start_sec": 50.0, "end_sec": 70.0, "reason": "lucu", "score": 0.8}])
    moments = await LlmTranscriptDetector(fake).detect(_ctx(_transcript(200), 200.0))

    assert fake.calls >= 2
    assert len(moments) == 1  # momen identik dari 2 chunk → dedupe jadi 1
    assert moments[0].strategy.value == "llm_transcript"
    assert moments[0].reason == "lucu"
    assert moments[0].score == 0.8


async def test_llm_detector_clamps_and_skips_invalid() -> None:
    fake = _FakeLLM(
        [
            {"start_sec": 5.0, "end_sec": 1000.0, "reason": "panjang", "score": 2.0},  # clamp
            {"start_sec": 80.0, "end_sec": 70.0, "reason": "kebalik", "score": 0.5},  # invalid
        ]
    )
    moments = await LlmTranscriptDetector(fake).detect(_ctx(_transcript(100), 100.0))

    assert len(moments) == 1
    assert moments[0].end == 100.0  # di-clamp ke durasi
    assert moments[0].score == 1.0  # di-clamp ke [0,1]


async def test_llm_detector_empty_transcript() -> None:
    assert await LlmTranscriptDetector(_FakeLLM([])).detect(_ctx(None, 10.0)) == []

from pathlib import Path

from app.db.models.enums import DetectionStrategy
from app.services.detection.aggregator import aggregate, merge_cross_strategy
from app.services.detection.base import DetectedMoment, DetectionContext, MomentDetector


def _m(start: float, end: float, score: float, strategy: DetectionStrategy) -> DetectedMoment:
    return DetectedMoment(start=start, end=end, score=score, reason=strategy.value, strategy=strategy)


def _ctx() -> DetectionContext:
    return DetectionContext(video_path=Path("v"), audio_path=Path("a"), duration_seconds=300.0)


class _FakeDetector(MomentDetector):
    def __init__(
        self, strategy: DetectionStrategy, moments: list[DetectedMoment] | None = None, fail: bool = False
    ) -> None:
        self.strategy = strategy
        self._moments = moments or []
        self._fail = fail

    async def detect(self, ctx: DetectionContext) -> list[DetectedMoment]:
        if self._fail:
            raise RuntimeError("boom")
        return self._moments


def test_merge_cross_strategy_combines_overlapping() -> None:
    a = _m(10, 20, 0.6, DetectionStrategy.audio_spike)
    b = _m(12, 22, 0.7, DetectionStrategy.llm_transcript)
    c = _m(100, 110, 0.5, DetectionStrategy.audio_spike)

    merged = merge_cross_strategy([a, b, c])

    assert len(merged) == 2
    multi = next(m for m in merged if "multi" in m.reason)
    assert (multi.start, multi.end) == (10, 22)  # span union
    assert multi.score == 1.0  # 0.6 + 0.7 → capped
    assert "audio_spike" in multi.reason and "llm_transcript" in multi.reason


def test_merge_keeps_non_overlapping_separate() -> None:
    a = _m(0, 10, 0.5, DetectionStrategy.audio_spike)
    b = _m(50, 60, 0.4, DetectionStrategy.audio_spike)
    assert len(merge_cross_strategy([a, b])) == 2


async def test_aggregate_sorts_and_caps() -> None:
    moments = [_m(i * 20, i * 20 + 10, 0.1 * i, DetectionStrategy.audio_spike) for i in range(1, 6)]
    out = await aggregate(
        [_FakeDetector(DetectionStrategy.audio_spike, moments)], _ctx(), max_candidates=3
    )
    assert len(out) == 3
    assert out[0].score >= out[1].score >= out[2].score


async def test_aggregate_tolerates_failing_detector() -> None:
    good = _FakeDetector(
        DetectionStrategy.audio_spike, [_m(10, 20, 0.8, DetectionStrategy.audio_spike)]
    )
    bad = _FakeDetector(DetectionStrategy.llm_transcript, fail=True)
    out = await aggregate([good, bad], _ctx(), max_candidates=50)
    assert len(out) == 1  # detector gagal di-skip, yang sukses tetap dipakai

from pathlib import Path

from app.services.detection.base import DetectionContext
from app.services.detection.manual_marker import ManualMarkerDetector


def _ctx(duration: float) -> DetectionContext:
    return DetectionContext(
        video_path=Path("v.mp4"), audio_path=Path("a.wav"), duration_seconds=duration
    )


async def test_manual_markers_parse_and_window() -> None:
    detector = ManualMarkerDetector(
        markers=["00:01:00, epic play", "0:30", "   ", "bukan-timestamp"],
        clip_seconds=30.0,
    )
    moments = await detector.detect(_ctx(120.0))

    assert len(moments) == 2  # 2 valid; baris kosong & invalid di-skip
    by_reason = {m.reason: m for m in moments}

    epic = by_reason["epic play"]
    assert (epic.start, epic.end) == (45.0, 75.0)
    assert epic.score == 1.0
    assert epic.strategy.value == "manual"

    no_comment = by_reason["Manual marker"]  # "0:30" tanpa komentar
    assert (no_comment.start, no_comment.end) == (15.0, 45.0)


async def test_manual_marker_clamps_to_bounds() -> None:
    detector = ManualMarkerDetector(markers=["0:05"], clip_seconds=30.0)
    moments = await detector.detect(_ctx(120.0))
    assert moments[0].start == 0.0  # 5 - 15 → clamp ke 0
    assert moments[0].end == 20.0


async def test_manual_marker_empty() -> None:
    assert await ManualMarkerDetector(markers=[]).detect(_ctx(60.0)) == []

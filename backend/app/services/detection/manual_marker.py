from app.db.models.enums import DetectionStrategy
from app.services.detection.base import (
    DetectedMoment,
    DetectionContext,
    MomentDetector,
    excerpt_for_range,
)

DEFAULT_CLIP_SECONDS = 30.0


def _parse_timestamp(ts: str) -> float | None:
    """Parse 'HH:MM:SS' / 'MM:SS' / 'SS' jadi detik."""
    parts = ts.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if not nums:
        return None
    seconds = 0.0
    for num in nums:
        seconds = seconds * 60 + num
    return seconds


def _parse_marker(raw: str) -> tuple[float, str] | None:
    """Parse satu baris 'HH:MM:SS, comment' jadi (detik, comment)."""
    line = raw.strip()
    if not line:
        return None
    ts_part, _, comment = line.partition(",")
    seconds = _parse_timestamp(ts_part.strip())
    if seconds is None:
        return None
    return seconds, comment.strip()


class ManualMarkerDetector(MomentDetector):
    """Tiap marker user → satu klip (default 30s: 15s sebelum & sesudah) (§5.4)."""

    strategy = DetectionStrategy.manual

    def __init__(self, markers: list[str], clip_seconds: float = DEFAULT_CLIP_SECONDS) -> None:
        self._markers = markers
        self._half = clip_seconds / 2

    async def detect(self, ctx: DetectionContext) -> list[DetectedMoment]:
        moments: list[DetectedMoment] = []
        for raw in self._markers:
            parsed = _parse_marker(raw)
            if parsed is None:
                continue
            marker, comment = parsed
            start = max(0.0, marker - self._half)
            end = min(ctx.duration_seconds, marker + self._half)
            if end <= start:
                continue
            moments.append(
                DetectedMoment(
                    start=start,
                    end=end,
                    score=1.0,  # marker manual = pilihan eksplisit user
                    reason=comment or "Manual marker",
                    strategy=self.strategy,
                    transcript_excerpt=excerpt_for_range(ctx.transcript, start, end),
                )
            )
        return moments

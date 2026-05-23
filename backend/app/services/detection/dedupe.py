from app.services.detection.base import DetectedMoment


def overlap_ratio(a: DetectedMoment, b: DetectedMoment) -> float:
    """Rasio overlap relatif ke durasi momen yang lebih pendek (0..1)."""
    inter = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    shorter = min(a.end - a.start, b.end - b.start)
    return inter / shorter if shorter > 0 else 0.0


def dedupe_moments(moments: list[DetectedMoment], threshold: float = 0.5) -> list[DetectedMoment]:
    """Merge momen dari strategi yang sama yang overlap > threshold (span union, score maks)."""
    result: list[DetectedMoment] = []
    for moment in sorted(moments, key=lambda m: m.start):
        for i, existing in enumerate(result):
            if overlap_ratio(moment, existing) > threshold:
                result[i] = DetectedMoment(
                    start=min(existing.start, moment.start),
                    end=max(existing.end, moment.end),
                    score=max(existing.score, moment.score),
                    reason=existing.reason,
                    strategy=existing.strategy,
                    transcript_excerpt=existing.transcript_excerpt or moment.transcript_excerpt,
                )
                break
        else:
            result.append(moment)
    return result

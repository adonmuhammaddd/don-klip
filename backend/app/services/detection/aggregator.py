import asyncio
import logging

from app.db.models.enums import DetectionStrategy
from app.services.detection.base import DetectedMoment, DetectionContext, MomentDetector
from app.services.detection.dedupe import overlap_ratio

logger = logging.getLogger(__name__)

Weights = dict[DetectionStrategy, float]


def _merge_group(group: list[DetectedMoment], weights: Weights) -> DetectedMoment:
    if len(group) == 1:
        return group[0]

    def weighted(moment: DetectedMoment) -> float:
        return weights.get(moment.strategy, 1.0) * moment.score

    primary = max(group, key=weighted)
    strategies = sorted({m.strategy for m in group}, key=lambda s: s.value)
    score = min(1.0, sum(weighted(m) for m in group))
    excerpt = next((m.transcript_excerpt for m in group if m.transcript_excerpt), None)
    reason = primary.reason
    if len(strategies) > 1:
        reason = f"[multi: {'+'.join(s.value for s in strategies)}] {primary.reason}"

    return DetectedMoment(
        start=min(m.start for m in group),
        end=max(m.end for m in group),
        score=score,
        reason=reason,
        strategy=primary.strategy,
        transcript_excerpt=excerpt,
    )


def merge_cross_strategy(
    moments: list[DetectedMoment], *, threshold: float = 0.5, weights: Weights | None = None
) -> list[DetectedMoment]:
    """Merge kandidat (lintas strategi) yang overlap > threshold, score weighted-sum (§5.5)."""
    weights = weights or {}
    groups: list[list[DetectedMoment]] = []
    for moment in sorted(moments, key=lambda m: m.start):
        for group in groups:
            if any(overlap_ratio(moment, other) > threshold for other in group):
                group.append(moment)
                break
        else:
            groups.append([moment])
    return [_merge_group(group, weights) for group in groups]


async def aggregate(
    detectors: list[MomentDetector],
    ctx: DetectionContext,
    *,
    max_candidates: int,
    weights: Weights | None = None,
) -> list[DetectedMoment]:
    """Jalankan semua detector (parallel), merge+dedupe, sort score desc, cap (§5.5)."""
    if not detectors:
        return []
    results = await asyncio.gather(
        *(detector.detect(ctx) for detector in detectors), return_exceptions=True
    )
    moments: list[DetectedMoment] = []
    for detector, result in zip(detectors, results, strict=True):
        if isinstance(result, BaseException):
            # Satu detector gagal (mis. LLM quota) tidak menggagalkan yang lain.
            logger.warning("detector %s gagal: %s", detector.strategy.value, result)
            continue
        moments.extend(result)

    merged = merge_cross_strategy(moments, weights=weights)
    merged.sort(key=lambda m: m.score, reverse=True)
    return merged[:max_candidates]

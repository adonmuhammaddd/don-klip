import asyncio
import statistics

from app.db.models.enums import DetectionStrategy
from app.services.detection.base import (
    DetectedMoment,
    DetectionContext,
    MomentDetector,
    excerpt_for_range,
)

WINDOW_SEC = 5.0
MERGE_GAP_SEC = 10.0
PAD_BEFORE_SEC = 8.0
PAD_AFTER_SEC = 4.0

# Token hype/emote umum (match per-token, bukan substring).
HYPE_TERMS = {
    "pog", "poggers", "pogchamp", "lul", "lulw", "kekw", "omegalul",
    "ez", "hype", "gg", "clip", "sheesh", "w", "letsgo",
}


def _hype_score(text: str) -> int:
    return sum(1 for token in text.lower().split() if token.strip(".,!?") in HYPE_TERMS)


def _group(indices: list[int]) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    start = prev = indices[0]
    for idx in indices[1:]:
        if (idx - prev) * WINDOW_SEC > MERGE_GAP_SEC:
            groups.append((start, prev))
            start = idx
        prev = idx
    groups.append((start, prev))
    return groups


class ChatDensityDetector(MomentDetector):
    """Deteksi momen hype via lonjakan kepadatan chat Twitch (§5.3)."""

    strategy = DetectionStrategy.twitch_chat

    def __init__(self, std_multiplier: float = 2.0) -> None:
        self._std = std_multiplier

    async def detect(self, ctx: DetectionContext) -> list[DetectedMoment]:
        if not ctx.chat_log:
            return []
        return await asyncio.to_thread(self._detect_sync, ctx)

    def _detect_sync(self, ctx: DetectionContext) -> list[DetectedMoment]:
        chat = ctx.chat_log or []
        n_windows = int(ctx.duration_seconds // WINDOW_SEC) + 1
        if n_windows <= 0:
            return []

        counts = [0] * n_windows
        hype = [0] * n_windows
        for msg in chat:
            idx = int(msg.offset_seconds // WINDOW_SEC)
            if 0 <= idx < n_windows:
                counts[idx] += 1
                hype[idx] += msg.emote_count + _hype_score(msg.text)

        if sum(counts) == 0:
            return []

        mean = statistics.fmean(counts)
        std = statistics.pstdev(counts)
        threshold = mean + self._std * std
        max_count = max(counts)

        spike_idx = [i for i, c in enumerate(counts) if c > threshold and c > 0]
        if not spike_idx:
            return []

        moments: list[DetectedMoment] = []
        for start_idx, end_idx in _group(spike_idx):
            start = max(0.0, start_idx * WINDOW_SEC - PAD_BEFORE_SEC)
            end = min(ctx.duration_seconds, (end_idx + 1) * WINDOW_SEC + PAD_AFTER_SEC)
            if end <= start:
                continue
            peak = max(counts[start_idx : end_idx + 1])
            base = (peak - mean) / (max_count - mean) if max_count > mean else 1.0
            has_hype = any(hype[i] > 0 for i in range(start_idx, end_idx + 1))
            score = min(1.0, max(0.0, base + (0.1 if has_hype else 0.0)))
            reason = f"Chat ramai: {peak} pesan/{int(WINDOW_SEC)}s ({self._std:g}σ)"
            moments.append(
                DetectedMoment(
                    start=start,
                    end=end,
                    score=score,
                    reason=reason,
                    strategy=self.strategy,
                    transcript_excerpt=excerpt_for_range(ctx.transcript, start, end),
                )
            )
        return moments

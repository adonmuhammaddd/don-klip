import asyncio
import wave
from pathlib import Path
from typing import cast

import numpy as np
import numpy.typing as npt

from app.db.models.enums import DetectionStrategy
from app.services.detection.base import (
    DetectedMoment,
    DetectionContext,
    MomentDetector,
    excerpt_for_range,
)
from app.services.errors import DetectionError

WINDOW_SEC = 0.5
MERGE_GAP_SEC = 3.0
PAD_BEFORE_SEC = 8.0
PAD_AFTER_SEC = 4.0
SMOOTH_WINDOWS = 5

FloatArray = npt.NDArray[np.float64]


class AudioSpikeDetector(MomentDetector):
    """Deteksi momen ramai via lonjakan energi audio (RMS) (§5.1)."""

    strategy = DetectionStrategy.audio_spike

    def __init__(self, std_multiplier: float = 2.0) -> None:
        self._std_multiplier = std_multiplier

    async def detect(self, ctx: DetectionContext) -> list[DetectedMoment]:
        # Komputasi numpy CPU-bound → jalankan di thread biar tidak block event loop.
        return await asyncio.to_thread(self._detect_sync, ctx)

    def _detect_sync(self, ctx: DetectionContext) -> list[DetectedMoment]:
        rms = self._smooth(self._compute_rms(ctx.audio_path))
        if rms.size == 0:
            return []

        mean = float(rms.mean())
        std = float(rms.std())
        max_rms = float(rms.max())
        threshold = mean + self._std_multiplier * std

        spike_idx = np.flatnonzero(rms > threshold)
        if spike_idx.size == 0:
            return []

        moments: list[DetectedMoment] = []
        for start_idx, end_idx in self._group(spike_idx):
            raw_start = start_idx * WINDOW_SEC
            raw_end = (end_idx + 1) * WINDOW_SEC
            start = max(0.0, raw_start - PAD_BEFORE_SEC)
            end = min(ctx.duration_seconds, raw_end + PAD_AFTER_SEC)
            if end <= start:
                continue

            peak = float(rms[start_idx : end_idx + 1].max())
            score = (peak - mean) / (max_rms - mean) if max_rms > mean else 1.0
            score = min(1.0, max(0.0, score))
            reason = f"Audio spike: RMS {peak:.0f}, {self._std_multiplier:g}σ di atas rata-rata"

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

    @staticmethod
    def _compute_rms(audio_path: Path) -> FloatArray:
        try:
            with wave.open(str(audio_path), "rb") as wf:
                n_channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                sampwidth = wf.getsampwidth()
                raw = wf.readframes(wf.getnframes())
        except (OSError, wave.Error) as exc:
            raise DetectionError(f"gagal baca audio: {audio_path}") from exc

        if sampwidth != 2:
            raise DetectionError(f"audio harus PCM 16-bit, dapat sampwidth={sampwidth}")

        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(axis=1)

        window_size = int(sample_rate * WINDOW_SEC)
        if window_size <= 0 or samples.size < window_size:
            return np.empty(0, dtype=np.float64)

        n_windows = samples.size // window_size
        framed = samples[: n_windows * window_size].reshape(n_windows, window_size)
        rms = np.sqrt(np.square(framed).mean(axis=1))
        return cast(FloatArray, rms)

    @staticmethod
    def _smooth(rms: FloatArray) -> FloatArray:
        if rms.size < SMOOTH_WINDOWS:
            return rms
        kernel = np.ones(SMOOTH_WINDOWS, dtype=np.float64) / SMOOTH_WINDOWS
        return cast(FloatArray, np.convolve(rms, kernel, mode="same"))

    @staticmethod
    def _group(spike_idx: npt.NDArray[np.intp]) -> list[tuple[int, int]]:
        """Gabung window spike yang gap-nya < MERGE_GAP_SEC jadi satu rentang."""
        groups: list[tuple[int, int]] = []
        start = prev = int(spike_idx[0])
        for raw in spike_idx[1:]:
            idx = int(raw)
            if (idx - prev) * WINDOW_SEC > MERGE_GAP_SEC:
                groups.append((start, prev))
                start = idx
            prev = idx
        groups.append((start, prev))
        return groups

import wave
from pathlib import Path

import numpy as np

from app.services.detection.audio_spike import AudioSpikeDetector
from app.services.detection.base import DetectionContext

SAMPLE_RATE = 16000


def _write_wav(path: Path, samples: np.ndarray) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(samples.astype(np.int16).tobytes())


def _make_context(path: Path, duration: float) -> DetectionContext:
    return DetectionContext(
        video_path=path, audio_path=path, duration_seconds=duration, transcript=None, config={}
    )


async def test_detects_loud_burst(tmp_path: Path) -> None:
    rng = np.random.default_rng(0)
    duration = 30
    samples = (rng.standard_normal(SAMPLE_RATE * duration) * 300).astype(np.int16)
    # Burst keras di 15s..17s.
    burst = slice(15 * SAMPLE_RATE, 17 * SAMPLE_RATE)
    samples[burst] = (rng.standard_normal(2 * SAMPLE_RATE) * 15000).astype(np.int16)
    wav = tmp_path / "burst.wav"
    _write_wav(wav, samples)

    moments = await AudioSpikeDetector(std_multiplier=2.0).detect(_make_context(wav, float(duration)))

    assert len(moments) >= 1
    top = max(moments, key=lambda m: m.score)
    # Burst 15-17 harus tercakup; padding 8s sebelum → start sekitar 7.
    assert top.start <= 15.0 <= top.end
    assert top.start >= 0.0
    assert top.end <= duration
    assert 0.0 <= top.score <= 1.0
    assert top.strategy.value == "audio_spike"


async def test_silence_yields_no_moments(tmp_path: Path) -> None:
    samples = np.zeros(SAMPLE_RATE * 10, dtype=np.int16)
    wav = tmp_path / "silent.wav"
    _write_wav(wav, samples)

    moments = await AudioSpikeDetector(std_multiplier=2.0).detect(_make_context(wav, 10.0))

    assert moments == []


async def test_close_bursts_merge_into_one(tmp_path: Path) -> None:
    rng = np.random.default_rng(1)
    duration = 40
    samples = (rng.standard_normal(SAMPLE_RATE * duration) * 300).astype(np.int16)
    # Dua burst berjarak ~1s (< 3s gap) → harus merge jadi satu rentang.
    for begin in (20, 22):
        seg = slice(begin * SAMPLE_RATE, (begin) * SAMPLE_RATE + SAMPLE_RATE // 2)
        samples[seg] = (rng.standard_normal(SAMPLE_RATE // 2) * 15000).astype(np.int16)
    wav = tmp_path / "merge.wav"
    _write_wav(wav, samples)

    moments = await AudioSpikeDetector(std_multiplier=2.0).detect(_make_context(wav, float(duration)))

    # Kedua burst (20.0 dan 22.0) tercakup dalam satu momen hasil merge.
    covering = [m for m in moments if m.start <= 20.0 and m.end >= 22.5]
    assert len(covering) == 1

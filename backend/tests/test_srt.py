from pathlib import Path
from uuid import uuid4

from app.db.models.clip import ClipCandidate
from app.db.models.enums import ClipStatus, DetectionStrategy
from app.services.export.exporter import export_clip
from app.services.export.srt import build_srt
from app.services.ffmpeg.runner import FfmpegRunner

SEGMENTS = [
    {"start": 0.0, "end": 4.0, "text": "sebelum", "confidence": None},
    {"start": 12.0, "end": 14.0, "text": "di dalam", "confidence": None},
    {"start": 30.0, "end": 31.0, "text": "sesudah", "confidence": None},
]


def test_build_srt_offsets_and_filters() -> None:
    srt = build_srt(SEGMENTS, clip_start=10.0, clip_end=20.0)
    assert "di dalam" in srt
    assert "sebelum" not in srt  # end 4 <= clip_start 10
    assert "sesudah" not in srt  # start 30 >= clip_end 20
    # 12 - 10 = 2s → offset relatif ke awal klip.
    assert "00:00:02,000 --> 00:00:04,000" in srt
    assert srt.startswith("1\n")


def test_build_srt_empty_when_no_overlap() -> None:
    assert build_srt(SEGMENTS, clip_start=100.0, clip_end=110.0) == ""


class _FakeFfmpeg(FfmpegRunner):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def export_vertical(self, input_path: Path, output_path: Path, start: float, end: float) -> None:
        self.calls += 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"x")

    async def export_square(self, input_path: Path, output_path: Path, start: float, end: float) -> None:
        self.calls += 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"x")


def _clip() -> ClipCandidate:
    return ClipCandidate(
        id=uuid4(),
        job_id=uuid4(),
        start_seconds=0.0,
        end_seconds=5.0,
        detection_strategy=DetectionStrategy.audio_spike,
        score=0.5,
        reason="x",
        status=ClipStatus.selected,
        exported_paths={},
    )


async def test_export_clip_idempotent(tmp_path: Path) -> None:
    clip = _clip()
    ffmpeg = _FakeFfmpeg()
    kwargs = {
        "source_path": tmp_path / "src.mp4",
        "segments": SEGMENTS,
        "outputs_dir": tmp_path / "out",
        "ffmpeg": ffmpeg,
    }

    paths = await export_clip(clip=clip, **kwargs)
    assert {"9_16", "1_1", "srt"} <= paths.keys()
    assert ffmpeg.calls == 2

    # File sudah ada + paths terisi → export di-skip.
    clip.exported_paths = paths
    await export_clip(clip=clip, **kwargs)
    assert ffmpeg.calls == 2

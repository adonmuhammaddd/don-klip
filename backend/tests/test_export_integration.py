"""Integration test ffmpeg export (butuh ffmpeg). Skip kalau ffmpeg tidak ada."""

import shutil
import subprocess
from pathlib import Path

import pytest

from app.services.ffmpeg.runner import FfmpegRunner

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="butuh ffmpeg")


def _make_clip(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=8",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=8",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


async def test_export_vertical_and_square_dimensions(tmp_path: Path) -> None:
    src = tmp_path / "src.mp4"
    _make_clip(src)
    ffmpeg = FfmpegRunner()

    vertical = tmp_path / "v.mp4"
    await ffmpeg.export_vertical(src, vertical, 2.0, 6.0)
    pv = await ffmpeg.probe(vertical)
    assert (pv.width, pv.height) == (1080, 1920)
    assert pv.duration_seconds == pytest.approx(4.0, abs=1.0)

    square = tmp_path / "s.mp4"
    await ffmpeg.export_square(src, square, 2.0, 6.0)
    ps = await ffmpeg.probe(square)
    assert (ps.width, ps.height) == (1080, 1080)

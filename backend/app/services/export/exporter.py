import asyncio
from pathlib import Path
from typing import Any

from app.db.models.clip import ClipCandidate
from app.services.export.srt import build_srt
from app.services.ffmpeg.runner import FfmpegRunner


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def export_clip(
    *,
    clip: ClipCandidate,
    source_path: Path,
    segments: list[dict[str, Any]],
    outputs_dir: Path,
    ffmpeg: FfmpegRunner,
) -> dict[str, str]:
    """Export klip ke 9:16, 1:1, dan SRT. Idempoten: skip yang filenya sudah ada (§13)."""
    start = clip.user_start_seconds if clip.user_start_seconds is not None else clip.start_seconds
    end = clip.user_end_seconds if clip.user_end_seconds is not None else clip.end_seconds
    out_dir = outputs_dir / str(clip.job_id) / str(clip.id)
    paths: dict[str, str] = dict(clip.exported_paths)

    vertical = out_dir / "clip_9_16.mp4"
    if "9_16" not in paths or not await asyncio.to_thread(vertical.is_file):
        await ffmpeg.export_vertical(source_path, vertical, start, end)
        paths["9_16"] = str(vertical)

    square = out_dir / "clip_1_1.mp4"
    if "1_1" not in paths or not await asyncio.to_thread(square.is_file):
        await ffmpeg.export_square(source_path, square, start, end)
        paths["1_1"] = str(square)

    srt_content = build_srt(segments, start, end)
    if srt_content:
        srt_path = out_dir / "clip.srt"
        await asyncio.to_thread(_write_text, srt_path, srt_content)
        paths["srt"] = str(srt_path)

    return paths

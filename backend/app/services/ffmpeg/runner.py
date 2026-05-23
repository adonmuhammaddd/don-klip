import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.errors import PipelineError


class FfmpegError(PipelineError):
    """ffmpeg/ffprobe keluar dengan exit code non-zero."""


@dataclass(frozen=True)
class ProbeResult:
    duration_seconds: float
    width: int | None
    height: int | None
    video_codec: str | None
    audio_codec: str | None


class FfmpegRunner:
    """Wrapper async untuk ffmpeg/ffprobe via create_subprocess_exec.

    Method export 9:16 / 1:1 (crop) ditambahkan di Sprint 3 (step 13).
    """

    def __init__(self, ffmpeg_bin: str = "ffmpeg", ffprobe_bin: str = "ffprobe") -> None:
        self._ffmpeg = ffmpeg_bin
        self._ffprobe = ffprobe_bin

    async def _run(self, *args: str) -> bytes:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            tail = stderr.decode(errors="replace")[-2000:]
            raise FfmpegError(f"{args[0]} exited {proc.returncode}: {tail}")
        return stdout

    async def probe(self, input_path: Path) -> ProbeResult:
        stdout = await self._run(
            self._ffprobe,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(input_path),
        )
        data: dict[str, Any] = json.loads(stdout)
        fmt = data.get("format", {})
        streams: list[dict[str, Any]] = data.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

        try:
            duration = float(fmt["duration"])
        except (KeyError, TypeError, ValueError) as exc:
            raise FfmpegError(f"ffprobe tidak mengembalikan duration: {input_path}") from exc

        return ProbeResult(
            duration_seconds=duration,
            width=video.get("width") if video else None,
            height=video.get("height") if video else None,
            video_codec=video.get("codec_name") if video else None,
            audio_codec=audio.get("codec_name") if audio else None,
        )

    async def cut(
        self,
        input_path: Path,
        output_path: Path,
        start: float,
        end: float,
        copy_codec: bool = True,
    ) -> None:
        """Potong klip [start, end]. copy_codec=True cepat tapi snap ke keyframe terdekat."""
        await asyncio.to_thread(output_path.parent.mkdir, parents=True, exist_ok=True)
        # -ss sebelum -i (fast seek) + -t durasi (relatif terhadap -ss, akurat).
        args = [
            self._ffmpeg, "-y",
            "-ss", f"{start}",
            "-i", str(input_path),
            "-t", f"{end - start}",
        ]
        if copy_codec:
            args += ["-c", "copy"]
        args.append(str(output_path))
        await self._run(*args)

    async def extract_audio(
        self, input_path: Path, output_path: Path, sample_rate: int = 16000
    ) -> None:
        """Ekstrak audio mono PCM 16-bit untuk whisper.cpp & audio spike detector."""
        await asyncio.to_thread(output_path.parent.mkdir, parents=True, exist_ok=True)
        await self._run(
            self._ffmpeg,
            "-y",
            "-i", str(input_path),
            "-vn",
            "-ac", "1",
            "-ar", str(sample_rate),
            "-c:a", "pcm_s16le",
            str(output_path),
        )

import asyncio
import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.errors import TranscriptionError
from app.services.transcription.base import Transcriber, TranscriptResult, TranscriptSegment


class WhisperCppTranscriber(Transcriber):
    """Wrapper untuk binary whisper-cli (whisper.cpp). Input wajib WAV mono 16kHz."""

    def __init__(self, binary: str, model_path: Path, language: str | None = None) -> None:
        self._binary = binary
        self._model_path = model_path
        self._language = language

    async def transcribe(self, audio_path: Path) -> TranscriptResult:
        out_prefix = audio_path.with_suffix("")
        args = [
            self._binary,
            "-m", str(self._model_path),
            "-f", str(audio_path),
            "--output-json",
            "-of", str(out_prefix),
        ]
        if self._language:
            args += ["-l", self._language]

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            tail = stderr.decode(errors="replace")[-2000:]
            raise TranscriptionError(f"whisper-cli exited {proc.returncode}: {tail}")

        json_path = out_prefix.with_suffix(".json")
        return await asyncio.to_thread(self._parse, json_path)

    def _parse(self, json_path: Path) -> TranscriptResult:
        try:
            data: dict[str, Any] = json.loads(json_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise TranscriptionError(f"gagal baca output whisper: {json_path}") from exc

        language = str(data.get("result", {}).get("language", "unknown"))
        segments: list[TranscriptSegment] = []
        for item in data.get("transcription", []):
            offsets = item.get("offsets", {})
            segments.append(
                TranscriptSegment(
                    start=offsets["from"] / 1000.0,
                    end=offsets["to"] / 1000.0,
                    text=str(item.get("text", "")).strip(),
                    confidence=None,  # whisper.cpp --output-json tidak punya confidence per-segmen
                )
            )
        return TranscriptResult(language=language, segments=segments)


def get_transcriber(settings: Settings) -> Transcriber:
    model_path = Path(settings.whisper_models_dir) / f"ggml-{settings.whisper_model}.bin"
    # Model *.en sudah fixed English; model multilingual pakai auto-detect.
    language = None if settings.whisper_model.endswith(".en") else "auto"
    return WhisperCppTranscriber(settings.whisper_bin, model_path, language)

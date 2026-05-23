class PipelineError(Exception):
    """Base error untuk pipeline processing."""


class SourceError(PipelineError):
    """Gagal acquire source video (upload tidak valid / download gagal)."""


class TranscriptionError(PipelineError):
    """Gagal transcription."""


class DetectionError(PipelineError):
    """Gagal menjalankan detector."""


class LLMError(PipelineError):
    """Gagal memanggil LLM provider / parse output."""


class ChatError(PipelineError):
    """Gagal mengambil chat replay (mis. Twitch GQL)."""


class JobCancelledError(PipelineError):
    """Job dibatalkan user di tengah pipeline (§9)."""

class PipelineError(Exception):
    """Base error untuk pipeline processing."""


class SourceError(PipelineError):
    """Gagal acquire source video (upload tidak valid / download gagal)."""


class TranscriptionError(PipelineError):
    """Gagal transcription."""


class DetectionError(PipelineError):
    """Gagal menjalankan detector."""


class JobCancelledError(PipelineError):
    """Job dibatalkan user di tengah pipeline (§9)."""

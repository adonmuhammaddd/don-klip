import enum


class SourceType(enum.StrEnum):
    upload = "upload"
    url = "url"


class JobStatus(enum.StrEnum):
    pending = "pending"
    downloading = "downloading"
    transcribing = "transcribing"
    detecting = "detecting"
    ready_for_review = "ready_for_review"
    exporting = "exporting"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"  # cancellation (§9); tidak di tabel §3, ditambah untuk konsistensi


class DetectionStrategy(enum.StrEnum):
    audio_spike = "audio_spike"
    llm_transcript = "llm_transcript"
    twitch_chat = "twitch_chat"
    manual = "manual"


class ClipStatus(enum.StrEnum):
    pending = "pending"
    selected = "selected"
    rejected = "rejected"
    exporting = "exporting"
    exported = "exported"
    failed = "failed"

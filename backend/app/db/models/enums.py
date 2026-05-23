import enum


class SourceType(str, enum.Enum):
    upload = "upload"
    url = "url"


class JobStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    transcribing = "transcribing"
    detecting = "detecting"
    ready_for_review = "ready_for_review"
    exporting = "exporting"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"  # dipakai cancellation (§9); tidak ada di tabel §3, ditambah untuk konsistensi


class DetectionStrategy(str, enum.Enum):
    audio_spike = "audio_spike"
    llm_transcript = "llm_transcript"
    twitch_chat = "twitch_chat"
    manual = "manual"


class ClipStatus(str, enum.Enum):
    pending = "pending"
    selected = "selected"
    rejected = "rejected"
    exporting = "exporting"
    exported = "exported"
    failed = "failed"

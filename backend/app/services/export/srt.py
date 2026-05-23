from typing import Any


def _timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_srt(segments: list[dict[str, Any]], clip_start: float, clip_end: float) -> str:
    """Bangun SRT dari segmen transcript dalam rentang [clip_start, clip_end].

    Timestamp di-offset ke 0 (relatif ke awal klip), bukan ke awal source (§8).
    """
    blocks: list[str] = []
    index = 1
    for seg in segments:
        seg_start = float(seg["start"])
        seg_end = float(seg["end"])
        if seg_end <= clip_start or seg_start >= clip_end:
            continue
        rel_start = max(0.0, seg_start - clip_start)
        rel_end = min(clip_end, seg_end) - clip_start
        if rel_end <= rel_start:
            continue
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        blocks.append(f"{index}\n{_timestamp(rel_start)} --> {_timestamp(rel_end)}\n{text}\n")
        index += 1
    return "\n".join(blocks)

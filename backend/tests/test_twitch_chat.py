from pathlib import Path
from typing import Any

from app.services.chat.base import ChatMessage
from app.services.chat.twitch import parse_comments
from app.services.detection.base import DetectionContext
from app.services.detection.twitch_chat import ChatDensityDetector


def test_parse_comments() -> None:
    comments: dict[str, Any] = {
        "edges": [
            {
                "node": {
                    "contentOffsetSeconds": 12,
                    "message": {
                        "fragments": [
                            {"text": "hello "},
                            {"text": "PogChamp", "emote": {"id": "1"}},
                        ]
                    },
                },
                "cursor": "c1",
            },
            {"node": {"contentOffsetSeconds": 13, "message": {"fragments": [{"text": "lol"}]}}},
            {"node": {"message": {"fragments": [{"text": "no offset"}]}}},  # di-skip
        ]
    }
    msgs = parse_comments(comments)
    assert len(msgs) == 2
    assert msgs[0].offset_seconds == 12.0
    assert msgs[0].emote_count == 1
    assert "PogChamp" in msgs[0].text


def _ctx(chat: list[ChatMessage] | None, duration: float) -> DetectionContext:
    return DetectionContext(
        video_path=Path("v.mp4"),
        audio_path=Path("a.wav"),
        duration_seconds=duration,
        chat_log=chat,
    )


async def test_chat_density_detects_spike() -> None:
    chat: list[ChatMessage] = [
        ChatMessage(offset_seconds=float(t), text="hi") for t in range(0, 100, 5)
    ]
    chat += [ChatMessage(offset_seconds=52.0, text="POG", emote_count=1) for _ in range(50)]

    moments = await ChatDensityDetector(2.0).detect(_ctx(chat, 100.0))

    assert len(moments) >= 1
    top = max(moments, key=lambda m: m.score)
    assert top.start <= 52.0 <= top.end
    assert 0.0 <= top.score <= 1.0
    assert top.strategy.value == "twitch_chat"


async def test_chat_density_empty() -> None:
    assert await ChatDensityDetector().detect(_ctx(None, 100.0)) == []

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    offset_seconds: float  # offset relatif ke awal video
    text: str
    emote_count: int = 0


class ChatFetcher(ABC):
    @abstractmethod
    async def fetch(self, video_id: str) -> list[ChatMessage]: ...

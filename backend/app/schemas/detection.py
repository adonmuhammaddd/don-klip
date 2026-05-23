from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AudioSpikeStrategy(BaseModel):
    strategy: Literal["audio_spike"] = "audio_spike"
    std_multiplier: float = Field(default=2.0, gt=0)


class LlmTranscriptStrategy(BaseModel):
    strategy: Literal["llm_transcript"] = "llm_transcript"
    # parameter ditambah di Sprint 4


class TwitchChatStrategy(BaseModel):
    strategy: Literal["twitch_chat"] = "twitch_chat"
    # parameter ditambah di Sprint 4


class ManualMarkerStrategy(BaseModel):
    strategy: Literal["manual"] = "manual"
    markers: list[str] = Field(default_factory=list)  # diparse penuh di Sprint 4


StrategyConfig = Annotated[
    AudioSpikeStrategy | LlmTranscriptStrategy | TwitchChatStrategy | ManualMarkerStrategy,
    Field(discriminator="strategy"),
]


class DetectionConfigDTO(BaseModel):
    strategies: list[StrategyConfig] = Field(min_length=1)

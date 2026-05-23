from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Panggil LLM dengan structured output, kembalikan JSON object (§7)."""
        ...

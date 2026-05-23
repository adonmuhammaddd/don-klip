from typing import Any, cast

from anthropic import AsyncAnthropic
from anthropic.types import ToolParam, ToolUseBlock

from app.services.errors import LLMError
from app.services.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    """Anthropic Claude, structured output via forced tool use (§7)."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5") -> None:
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY kosong")
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        tool = cast(
            ToolParam,
            {
                "name": "emit_result",
                "description": "Emit hasil dalam bentuk JSON terstruktur.",
                "input_schema": schema,
            },
        )
        try:
            response = await self._client.messages.create(
                model=model or self._model,
                max_tokens=4096,
                temperature=temperature,
                tools=[tool],
                tool_choice={"type": "tool", "name": "emit_result"},
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise LLMError(f"panggilan Claude gagal: {exc}") from exc

        for block in response.content:
            if isinstance(block, ToolUseBlock) and isinstance(block.input, dict):
                return block.input
        raise LLMError("Claude tidak mengembalikan tool_use")

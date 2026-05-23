import json
from typing import Any

from openai import AsyncOpenAI

from app.services.errors import LLMError
from app.services.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI chat completions dengan structured output (response_format json_schema) (§7)."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        if not api_key:
            raise LLMError("OPENAI_API_KEY kosong")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        try:
            response = await self._client.chat.completions.create(
                model=model or self._model,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "result", "schema": schema, "strict": False},
                },
            )
        except Exception as exc:
            raise LLMError(f"panggilan OpenAI gagal: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMError("OpenAI mengembalikan respons kosong")
        try:
            parsed: Any = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"output OpenAI bukan JSON valid: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LLMError("output OpenAI bukan JSON object")
        return parsed

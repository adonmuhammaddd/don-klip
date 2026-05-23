import json
from typing import Any

from google import genai
from google.genai import types

from app.services.errors import LLMError
from app.services.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini via google-genai SDK, native JSON mode via response_schema (§7)."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        if not api_key:
            raise LLMError("GEMINI_API_KEY kosong")
        self._client = genai.Client(api_key=api_key)
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
            response = await self._client.aio.models.generate_content(
                model=model or self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=temperature,
                ),
            )
        except Exception as exc:
            raise LLMError(f"panggilan Gemini gagal: {exc}") from exc

        text = response.text
        if not text:
            raise LLMError("Gemini mengembalikan respons kosong")
        try:
            data: Any = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"output Gemini bukan JSON valid: {exc}") from exc
        if not isinstance(data, dict):
            raise LLMError("output Gemini bukan JSON object")
        return data

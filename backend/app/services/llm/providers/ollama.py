import json
from typing import Any

import httpx

from app.services.errors import LLMError
from app.services.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """LLM lokal via Ollama /api/chat dengan structured output (`format` = JSON schema)."""

    def __init__(
        self, base_url: str, model: str, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._transport = transport

    async def complete_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        payload = {
            "model": model or self._model,
            "messages": [{"role": "user", "content": prompt}],
            "format": schema,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=120.0, transport=self._transport) as client:
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data: Any = resp.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"panggilan Ollama gagal: {exc}") from exc

        try:
            content = data["message"]["content"]
            parsed: Any = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError(f"output Ollama tidak valid: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LLMError("output Ollama bukan JSON object")
        return parsed

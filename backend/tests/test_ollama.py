import json
from typing import Any

import httpx

from app.services.llm.providers.ollama import OllamaProvider


async def test_ollama_complete_json_parses_content() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": '{"city": "Jakarta"}'}})

    provider = OllamaProvider(
        "http://ollama:11434", "llama3.1:8b", transport=httpx.MockTransport(handler)
    )
    result = await provider.complete_json("prompt", {"type": "object"}, temperature=0.0)

    assert result == {"city": "Jakarta"}
    # Schema diteruskan sebagai `format`, stream dimatikan.
    assert captured["body"]["format"] == {"type": "object"}
    assert captured["body"]["stream"] is False

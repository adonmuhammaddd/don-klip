"""Integration test GeminiProvider — hit API Gemini asli. Skip kalau tidak ada key."""

import os
from typing import Any

import pytest

from app.services.errors import LLMError
from app.services.llm.providers.gemini import GeminiProvider

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"), reason="butuh GEMINI_API_KEY"
)


async def test_complete_json_returns_object() -> None:
    provider = GeminiProvider(api_key=os.environ["GEMINI_API_KEY"])
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "country": {"type": "string"},
        },
        "required": ["city", "country"],
    }
    try:
        result = await provider.complete_json(
            "Return JSON: the capital city of Indonesia and its country.",
            schema,
            temperature=0.0,
        )
    except LLMError as exc:
        # Quota/rate-limit akun bukan bug kode → skip, jangan gagalkan suite.
        if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
            pytest.skip(f"Gemini quota/rate-limit: {exc}")
        raise

    assert isinstance(result, dict)
    assert isinstance(result.get("city"), str)
    assert result.get("city", "").lower() == "jakarta"

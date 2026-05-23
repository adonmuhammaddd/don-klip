from typing import assert_never

from app.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.providers.claude import ClaudeProvider
from app.services.llm.providers.gemini import GeminiProvider
from app.services.llm.providers.ollama import OllamaProvider
from app.services.llm.providers.openai import OpenAIProvider


def get_llm_provider(settings: Settings) -> LLMProvider:
    match settings.llm_provider:
        case "gemini":
            return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        case "ollama":
            return OllamaProvider(settings.ollama_url, settings.ollama_model)
        case "claude":
            return ClaudeProvider(api_key=settings.anthropic_api_key)
        case "openai":
            return OpenAIProvider(api_key=settings.openai_api_key)
        case _:
            assert_never(settings.llm_provider)

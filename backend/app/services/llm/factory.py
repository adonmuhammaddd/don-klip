from app.config import Settings
from app.services.llm.base import LLMProvider
from app.services.llm.providers.gemini import GeminiProvider


def get_llm_provider(settings: Settings) -> LLMProvider:
    match settings.llm_provider:
        case "gemini":
            return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        case "ollama" | "claude" | "openai":
            # Provider lain di-implement di Sprint 5 (step 22).
            raise NotImplementedError(
                f"LLM provider '{settings.llm_provider}' belum diimplementasi (Sprint 5)"
            )

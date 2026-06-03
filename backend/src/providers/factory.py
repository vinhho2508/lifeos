from src.providers.anthropic import AnthropicProvider
from src.providers.base import BaseChatProvider
from src.providers.gemini import GeminiProvider
from src.providers.openai import OpenAIProvider


def get_chat_provider(provider_name: str, model: str) -> BaseChatProvider:
    if provider_name == "openai":
        return OpenAIProvider(model=model)
    elif provider_name == "gemini":
        return GeminiProvider(model=model)
    elif provider_name == "anthropic":
        return AnthropicProvider(model=model)
    raise ValueError(f"Unknown provider: {provider_name}")

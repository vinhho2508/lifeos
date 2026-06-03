from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from src.core.database import settings
from src.providers.base import BaseChatProvider


class AnthropicProvider(BaseChatProvider):
    def __init__(self, model: str):
        self.model = model

    def get_langchain_llm(self, streaming: bool = False) -> BaseChatModel:
        return ChatAnthropic(
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            model=self.model,
            streaming=streaming,
        )

    def supports_tool_calling(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def api_key(self) -> str:
        return settings.ANTHROPIC_API_KEY

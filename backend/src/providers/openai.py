from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.core.database import settings
from src.providers.base import BaseChatProvider


class OpenAIProvider(BaseChatProvider):
    def __init__(self, model: str):
        self.model = model

    def get_langchain_llm(self, streaming: bool = False) -> BaseChatModel:
        return ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model=self.model,
            streaming=streaming,
        )

    def supports_tool_calling(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def api_key(self) -> str:
        return settings.OPENAI_API_KEY

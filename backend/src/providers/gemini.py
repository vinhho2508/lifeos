from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.database import settings
from src.providers.base import BaseChatProvider


class GeminiProvider(BaseChatProvider):
    def __init__(self, model: str):
        self.model = model

    def get_langchain_llm(self, streaming: bool = False) -> BaseChatModel:
        return ChatGoogleGenerativeAI(
            google_api_key=settings.GEMINI_API_KEY,
            model=self.model,
            streaming=streaming,
        )

    def supports_tool_calling(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def api_key(self) -> str:
        return settings.GEMINI_API_KEY

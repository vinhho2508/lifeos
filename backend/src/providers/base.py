from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel


class BaseChatProvider(ABC):
    @abstractmethod
    def get_langchain_llm(self, streaming: bool = False) -> BaseChatModel:
        """Return a LangChain-compatible chat model."""

    @abstractmethod
    def supports_tool_calling(self) -> bool:
        """Does this provider support function/tool calling?"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Machine name for this provider (e.g. 'openai', 'gemini')."""

    @property
    @abstractmethod
    def api_key(self) -> str:
        """The API key used by this provider (empty = mock mode)."""

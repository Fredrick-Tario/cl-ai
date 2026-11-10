"""Qwen Cloud adapter using its OpenAI-compatible interface."""

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from cl_ai.ai.provider import AIProvider, ChatMessage, ProviderError
from cl_ai.config import Settings


class QwenProvider(AIProvider):
    """Translate CL-AI messages to a Qwen-compatible LangChain client."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        if client is not None:
            self._client = client
            return
        try:
            self._client = ChatOpenAI(
                model=settings.qwen_model,
                api_key=settings.qwen_api_key.get_secret_value(),
                base_url=str(settings.qwen_base_url).rstrip("/"),
                timeout=settings.qwen_timeout_seconds,
                max_retries=2,
                temperature=0.2,
            )
        except Exception as exc:
            raise ProviderError(
                "Qwen client initialization failed. Check the API key, model ID, "
                "base URL, and installed provider dependencies."
            ) from exc

    def chat(self, messages: Sequence[ChatMessage]) -> str:
        try:
            response = self._client.invoke([self._to_langchain(item) for item in messages])
        except Exception as exc:
            raise ProviderError(
                "Qwen request failed. Check your network, model ID, region, "
                "base URL, API-key permissions, and account quota."
            ) from exc

        content = self._extract_text(response)
        if not content:
            raise ProviderError("Qwen returned an empty response.")
        return content

    @staticmethod
    def _to_langchain(message: ChatMessage) -> BaseMessage:
        message_types = {
            "system": SystemMessage,
            "user": HumanMessage,
            "assistant": AIMessage,
        }
        return message_types[message.role](content=message.content)

    @staticmethod
    def _extract_text(response: Any) -> str:
        content = getattr(response, "content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "\n".join(part for part in parts if part).strip()
        return ""


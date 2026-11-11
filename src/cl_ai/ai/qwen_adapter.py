"""Qwen Cloud adapter using its OpenAI-compatible interface."""

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from cl_ai.ai.provider import AIProvider, ChatMessage, ProviderError
from cl_ai.config import Settings


class QwenProvider(AIProvider):
    """Translate CL-AI messages to an OpenAI-compatible LangChain client.

    The historical class name is retained for import compatibility. The configured
    endpoint may be Qwen Cloud, NVIDIA NIM, or another compatible personal API.
    """

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._provider_name = settings.provider_display_name
        self._timeout_seconds = settings.timeout_seconds
        if client is not None:
            self._client = client
            return
        try:
            self._client = ChatOpenAI(
                model=settings.model_name,
                api_key=settings.api_key.get_secret_value(),
                base_url=str(settings.base_url).rstrip("/"),
                timeout=settings.timeout_seconds,
                max_retries=2,
                temperature=0.2,
            )
        except Exception as exc:
            raise ProviderError(
                f"{settings.provider_display_name} client initialization failed. "
                "Check the API key, model ID, "
                "base URL, and installed provider dependencies."
            ) from exc

    def chat(self, messages: Sequence[ChatMessage]) -> str:
        try:
            response = self._client.invoke([self._to_langchain(item) for item in messages])
        except Exception as exc:
            raise ProviderError(self._safe_request_error(exc)) from exc

        content = self._extract_text(response)
        if not content:
            provider_name = getattr(self, "_provider_name", "Qwen")
            raise ProviderError(f"{provider_name} returned an empty response.")
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

    def _safe_request_error(self, error: Exception) -> str:
        provider_name = getattr(self, "_provider_name", "Qwen")
        timeout_seconds = getattr(self, "_timeout_seconds", None)
        current: BaseException | None = error
        status_code = None
        while current is not None:
            if "timeout" in type(current).__name__.casefold():
                timeout_note = (
                    f" after {timeout_seconds:g} seconds"
                    if isinstance(timeout_seconds, (int, float))
                    else ""
                )
                return f"{provider_name} request timed out{timeout_note}."
            status_code = status_code or getattr(current, "status_code", None)
            current = current.__cause__

        if isinstance(status_code, int):
            return (
                f"{provider_name} request failed (HTTP {status_code}). "
                "Check the model ID, endpoint, API-key permissions, and account quota."
            )
        return (
            f"{provider_name} request failed. Check your network, model ID, region, "
            "base URL, API-key permissions, and account quota."
        )


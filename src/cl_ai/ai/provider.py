"""Provider-neutral AI contracts used by CL-AI features."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Sequence


Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """A provider-independent chat message."""

    role: Role
    content: str


class ProviderError(RuntimeError):
    """A safe, user-facing failure from an AI provider."""


class AIProvider(ABC):
    """Interface implemented by Qwen and any future model provider."""

    @abstractmethod
    def chat(self, messages: Sequence[ChatMessage]) -> str:
        """Return the assistant response for a chat transcript."""


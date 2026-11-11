"""AI provider integrations."""

from cl_ai.ai.provider import AIProvider
from cl_ai.ai.qwen_adapter import QwenProvider
from cl_ai.config import Settings


def create_provider(settings: Settings) -> AIProvider:
    """Create the configured provider behind a provider-neutral interface."""

    if settings.ai_provider in {"qwen", "nvidia_nim", "openai_compatible"}:
        return QwenProvider(settings)
    raise ValueError(f"Unsupported AI provider: {settings.ai_provider}")


__all__ = ["AIProvider", "QwenProvider", "create_provider"]


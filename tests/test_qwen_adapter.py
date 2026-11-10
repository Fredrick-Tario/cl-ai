from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import SecretStr
import pytest

from cl_ai.ai.provider import ChatMessage, ProviderError
from cl_ai.ai.qwen_adapter import QwenProvider
from cl_ai.config import Settings


class FakeClient:
    def __init__(self, response: AIMessage | Exception) -> None:
        self.response = response
        self.received = []

    def invoke(self, messages):
        self.received = messages
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_qwen_adapter_translates_messages() -> None:
    client = FakeClient(AIMessage(content="A safe explanation."))
    provider = QwenProvider.__new__(QwenProvider)
    provider._client = client

    answer = provider.chat(
        [
            ChatMessage("system", "Be safe."),
            ChatMessage("user", "Explain terraform plan."),
        ]
    )

    assert answer == "A safe explanation."
    assert isinstance(client.received[0], SystemMessage)
    assert isinstance(client.received[1], HumanMessage)


def test_qwen_adapter_returns_safe_error() -> None:
    client = FakeClient(RuntimeError("secret upstream detail"))
    provider = QwenProvider.__new__(QwenProvider)
    provider._client = client

    try:
        provider.chat([ChatMessage("user", "hello")])
    except ProviderError as exc:
        assert "secret upstream detail" not in str(exc)
        assert "Qwen request failed" in str(exc)
    else:
        raise AssertionError("Expected ProviderError")


def test_qwen_client_initialization_error_is_safe(monkeypatch) -> None:
    settings = Settings(
        qwen_api_key=SecretStr("fake-secret-value"),
        qwen_base_url="https://example.invalid/compatible-mode/v1",
        qwen_model="test-model",
        _env_file=None,
    )

    def fail_client(**kwargs):
        raise RuntimeError(f"upstream leaked {kwargs['api_key']}")

    monkeypatch.setattr("cl_ai.ai.qwen_adapter.ChatOpenAI", fail_client)

    with pytest.raises(ProviderError) as error:
        QwenProvider(settings)

    assert "fake-secret-value" not in str(error.value)
    assert "initialization failed" in str(error.value)


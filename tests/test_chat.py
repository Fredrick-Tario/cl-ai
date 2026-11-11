from rich.console import Console

from cl_ai.ai.provider import AIProvider, ChatMessage
from cl_ai.chat import Conversation, run_chat


class FakeProvider(AIProvider):
    def __init__(self) -> None:
        self.calls: list[list[ChatMessage]] = []

    def chat(self, messages):
        self.calls.append(list(messages))
        return "Terraform plan previews proposed changes."


class ScriptedPrompt:
    def __init__(self, values: list[str]) -> None:
        self.values = iter(values)

    def prompt(self, message: str) -> str:
        del message
        return next(self.values)


def test_conversation_keeps_transcript() -> None:
    provider = FakeProvider()
    conversation = Conversation(provider, max_requests=2)

    answer = conversation.ask("Explain terraform plan.")

    assert answer.startswith("Terraform plan")
    assert conversation.request_count == 1
    assert [message.role for message in conversation.messages] == [
        "system",
        "user",
        "assistant",
    ]


def test_chat_exits_without_calling_provider() -> None:
    provider = FakeProvider()
    console = Console(record=True, force_terminal=False)

    run_chat(
        provider,
        max_requests=2,
        console=console,
        prompt_reader=ScriptedPrompt(["exit"]),
    )

    assert provider.calls == []
    assert "Goodbye" in console.export_text()


def test_cli_command_in_chat_is_not_sent_to_provider() -> None:
    provider = FakeProvider()
    console = Console(record=True, force_terminal=False)

    run_chat(
        provider,
        max_requests=2,
        console=console,
        prompt_reader=ScriptedPrompt(["cl-ai list", "exit"]),
        provider_name="NVIDIA NIM",
    )

    output = console.export_text()
    assert provider.calls == []
    assert "run it in Git Bash" in output
    assert "not sent" in output
    assert "Provider: NVIDIA NIM" in output


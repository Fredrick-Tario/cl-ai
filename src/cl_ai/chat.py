"""Interactive terminal conversation for the v0.1 foundation."""

from dataclasses import dataclass, field
from typing import Protocol

from prompt_toolkit import PromptSession
from rich.console import Console

from cl_ai.ai.provider import AIProvider, ChatMessage, ProviderError


SYSTEM_PROMPT = """You are CL-AI, a concise DevOps and SRE learning assistant.
Explain commands in plain language, state uncertainty, warn about destructive or
cost-incurring actions, and never claim that a suggested command was executed.
"""

EXIT_WORDS = {"exit", "quit", "/exit", "/quit"}


class PromptReader(Protocol):
    """Small prompt interface that keeps the chat loop easy to test."""

    def prompt(self, message: str) -> str: ...


@dataclass(slots=True)
class Conversation:
    """Own one bounded chat transcript."""

    provider: AIProvider
    max_requests: int
    messages: list[ChatMessage] = field(
        default_factory=lambda: [ChatMessage("system", SYSTEM_PROMPT)]
    )
    request_count: int = 0

    def ask(self, text: str) -> str:
        if self.request_count >= self.max_requests:
            raise ProviderError(
                "This session reached its configured AI request limit. "
                "Exit and increase CLAI_MAX_AI_REQUESTS_PER_SESSION only if intended."
            )

        self.messages.append(ChatMessage("user", text))
        try:
            answer = self.provider.chat(self.messages)
        except ProviderError:
            self.messages.pop()
            raise

        self.messages.append(ChatMessage("assistant", answer))
        self.request_count += 1
        return answer


def run_chat(
    provider: AIProvider,
    max_requests: int,
    *,
    console: Console | None = None,
    prompt_reader: PromptReader | None = None,
) -> None:
    """Run the terminal chat until the user exits or closes input."""

    output = console or Console()
    reader = prompt_reader or PromptSession()
    conversation = Conversation(provider, max_requests)

    output.print("[bold cyan]CL-AI v0.1[/bold cyan] | Provider: Qwen Cloud")
    output.print("Type [bold]exit[/bold] to return to your shell.")

    while True:
        try:
            text = reader.prompt("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            output.print("\nGoodbye.")
            return

        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            output.print("Goodbye.")
            return

        try:
            answer = conversation.ask(text)
        except ProviderError as exc:
            output.print(f"[bold red]CL-AI error:[/bold red] {exc}")
            continue

        output.print(f"[bold green]CL-AI:[/bold green] {answer}")


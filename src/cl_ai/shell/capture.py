"""Validate command text received from the opt-in Git Bash integration."""

from typing import TextIO


MAX_CAPTURE_CHARACTERS = 32_768


class ShellCaptureError(RuntimeError):
    """Raised when shell integration supplies unusable command text."""


def read_captured_command(
    stream: TextIO,
    *,
    max_characters: int = MAX_CAPTURE_CHARACTERS,
) -> str:
    """Read one bounded command from stdin without executing or parsing it."""

    command = stream.read(max_characters + 1)
    if len(command) > max_characters:
        raise ShellCaptureError(
            f"Captured command is too long; maximum is {max_characters} characters."
        )

    command = command.rstrip("\r\n")
    if not command.strip():
        raise ShellCaptureError("No previous Git Bash command was received.")
    if "\x00" in command:
        raise ShellCaptureError(
            "Captured command contains an unsupported null character."
        )
    return command

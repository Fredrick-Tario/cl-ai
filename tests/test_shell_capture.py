from io import StringIO

import pytest

from cl_ai.shell import ShellCaptureError, read_captured_command


def test_captured_command_preserves_quotes_and_multiline_text() -> None:
    expected = 'echo "first value"\necho "second value"'

    command = read_captured_command(StringIO(expected + "\n"))

    assert command == expected


def test_empty_capture_is_rejected() -> None:
    with pytest.raises(ShellCaptureError, match="No previous"):
        read_captured_command(StringIO("\n"))


def test_null_character_is_rejected() -> None:
    with pytest.raises(ShellCaptureError, match="null character"):
        read_captured_command(StringIO("echo safe\x00hidden"))


def test_capture_size_is_bounded() -> None:
    with pytest.raises(ShellCaptureError, match="too long"):
        read_captured_command(StringIO("123456"), max_characters=5)

"""Deterministic checks for obvious secrets in command text."""

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class SecretFinding:
    """Describe a secret category without retaining or revealing its value."""

    category: str


_DIRECT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private key material",
        re.compile(r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----", re.IGNORECASE),
    ),
    ("API key", re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "bearer token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    ),
    (
        "credential-bearing URL",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@", re.IGNORECASE),
    ),
)

_SENSITIVE_FLAG = re.compile(
    r"(?ix)"
    r"--(?:api[-_]?key|access[-_]?token|auth[-_]?token|token|password|passwd|"
    r"client[-_]?secret|secret)(?:\s*=\s*|\s+)(?P<value>[^\s]+)"
)

_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?ix)"
    r"(?:^|\s)(?:[A-Z][A-Z0-9_]*_)?(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|TOKEN|"
    r"PASSWORD|PASSWD|CLIENT_SECRET|SECRET)\s*=\s*"
    r"(?P<value>[^\s]+)"
)


def _is_reference_or_placeholder(value: str) -> bool:
    cleaned = value.strip("'\"")
    upper = cleaned.upper()
    return (
        cleaned.startswith("$")
        or (cleaned.startswith("%") and cleaned.endswith("%"))
        or (cleaned.startswith("<") and cleaned.endswith(">"))
        or upper.startswith(("YOUR_", "REPLACE_", "EXAMPLE_"))
        or upper in {"XXX", "REDACTED", "CHANGEME"}
    )


class SecretDetector:
    """Find obvious embedded credentials without returning matched values."""

    def scan(self, command_text: str) -> list[SecretFinding]:
        categories: set[str] = set()

        for category, pattern in _DIRECT_PATTERNS:
            if pattern.search(command_text):
                categories.add(category)

        for category, pattern in (
            ("sensitive command option", _SENSITIVE_FLAG),
            ("sensitive environment assignment", _SENSITIVE_ASSIGNMENT),
        ):
            for match in pattern.finditer(command_text):
                if not _is_reference_or_placeholder(match.group("value")):
                    categories.add(category)

        return [SecretFinding(category) for category in sorted(categories)]


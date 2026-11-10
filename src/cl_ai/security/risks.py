"""Deterministic command-risk checks that supplement AI explanations."""

from dataclasses import dataclass
import re

from cl_ai.ai.schemas import RiskLevel


_RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


@dataclass(frozen=True, slots=True)
class RiskFinding:
    level: RiskLevel
    note: str


_RULES: tuple[tuple[re.Pattern[str], RiskFinding], ...] = (
    (
        re.compile(r"(?:^|\s)terraform\s+destroy(?:\s|$)", re.IGNORECASE),
        RiskFinding(
            RiskLevel.CRITICAL,
            "Deletes Terraform-managed infrastructure.",
        ),
    ),
    (
        re.compile(r"(?:^|\s)rm\s+[^\n]*-(?:[a-z]*r[a-z]*f|[a-z]*f[a-z]*r)", re.IGNORECASE),
        RiskFinding(
            RiskLevel.CRITICAL,
            "Permanently deletes files and directories.",
        ),
    ),
    (
        re.compile(r"(?:^|\s)terraform\s+apply(?:\s|$)", re.IGNORECASE),
        RiskFinding(
            RiskLevel.HIGH,
            "Changes infrastructure and may create costs.",
        ),
    ),
    (
        re.compile(r"(?:^|\s)kubectl\s+delete(?:\s|$)", re.IGNORECASE),
        RiskFinding(
            RiskLevel.HIGH,
            "Deletes Kubernetes resources in the selected context.",
        ),
    ),
    (
        re.compile(r"(?:^|\s)docker\s+system\s+prune(?:\s|$)", re.IGNORECASE),
        RiskFinding(
            RiskLevel.HIGH,
            "Deletes unused local Docker data.",
        ),
    ),
    (
        re.compile(r"(?:^|\s)git\s+reset\s+--hard(?:\s|$)", re.IGNORECASE),
        RiskFinding(
            RiskLevel.HIGH,
            "Discards uncommitted changes.",
        ),
    ),
    (
        re.compile(r"(?:^|\s)terraform\s+plan\b[^\n]*\s-out(?:=|\s)", re.IGNORECASE),
        RiskFinding(
            RiskLevel.MEDIUM,
            "The plan file may contain secrets; do not commit it.",
        ),
    ),
)


class CommandRiskAnalyzer:
    """Return known risks without executing or parsing through a shell."""

    def analyze(self, command_text: str) -> list[RiskFinding]:
        return [finding for pattern, finding in _RULES if pattern.search(command_text)]

    @staticmethod
    def maximum_level(*levels: RiskLevel) -> RiskLevel:
        return max(levels, key=_RISK_ORDER.__getitem__)


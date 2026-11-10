"""Validated structured outputs produced by AI providers."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


TagText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
]
RiskNoteText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CommandComponent(BaseModel):
    """One meaningful command token and its explanation."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1, max_length=160)

    @field_validator("token", "explanation")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class CommandDocumentation(BaseModel):
    """Reviewable documentation generated for one command."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=40)
    subcategory: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=180)
    flag_breakdown: list[CommandComponent] = Field(default_factory=list, max_length=6)
    tags: list[TagText] = Field(min_length=1, max_length=6)
    risk_level: RiskLevel
    risk_notes: list[RiskNoteText] = Field(default_factory=list, max_length=5)

    @field_validator("title", "category", "subcategory", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("tags", "risk_notes")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = value.strip()
            key = item.casefold()
            if item and key not in seen:
                normalized.append(item)
                seen.add(key)
        return normalized


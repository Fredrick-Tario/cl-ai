"""Validated Command Vault records."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cl_ai.ai.schemas import CommandComponent, RiskLevel


class CommandSource(str, Enum):
    PASTED = "pasted"
    CAPTURED = "captured"
    RESEARCHED = "researched"


class VerificationState(str, Enum):
    SAVED = "saved"
    USER_REPORTED_WORKED = "user_reported_worked"
    EXECUTION_VERIFIED = "execution_verified"


class DocumentationSource(str, Enum):
    AI_GENERATED = "ai_generated"
    AI_EDITED = "ai_edited"
    MANUAL = "manual"


class CommandCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    command_text: str
    title: str | None = None
    notes: str | None = None
    category: str | None = None
    subcategory: str | None = None
    description: str | None = None
    flag_breakdown: list[CommandComponent] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    risk_level: RiskLevel | None = None
    risk_notes: list[str] = Field(default_factory=list)
    documentation_source: DocumentationSource | None = None
    ai_model: str | None = None
    documented_at: datetime | None = None
    source: CommandSource = CommandSource.PASTED
    verification_state: VerificationState = VerificationState.SAVED
    working_directory: str | None = None
    shell: str | None = None
    source_urls: list[str] = Field(default_factory=list)

    @field_validator("command_text")
    @classmethod
    def command_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("command must not be blank")
        return value

    @field_validator(
        "title",
        "notes",
        "category",
        "subcategory",
        "description",
        "ai_model",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CommandRecord(CommandCreate):
    id: int
    created_at: datetime
    updated_at: datetime


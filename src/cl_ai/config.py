"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """Raised when CL-AI cannot load a safe, valid configuration."""


class LocalSettings(BaseSettings):
    """Settings required by local-only CL-AI features."""

    clai_data_dir: Path = Field(default_factory=lambda: Path.home() / ".cl-ai")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("clai_data_dir", mode="before")
    @classmethod
    def expand_data_directory(cls, value: str | Path) -> Path:
        return Path(value).expanduser()

    @property
    def database_path(self) -> Path:
        return self.clai_data_dir / "cl_ai.db"


class Settings(BaseSettings):
    """Validated CL-AI settings.

    SecretStr prevents the API key from appearing in normal string output.
    """

    ai_provider: Literal["qwen", "nvidia_nim", "openai_compatible"] = "qwen"
    ai_provider_name: str | None = None
    ai_api_key: SecretStr | None = None
    ai_base_url: AnyHttpUrl | None = None
    ai_model: str | None = None
    qwen_api_key: SecretStr | None = None
    qwen_base_url: AnyHttpUrl | None = None
    qwen_model: str | None = None
    clai_max_ai_requests_per_session: int = Field(default=30, ge=1, le=1000)
    ai_timeout_seconds: float | None = Field(default=None, gt=0, le=300)
    qwen_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    web_timeout_seconds: float = Field(default=15.0, gt=0, le=60)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator(
        "ai_provider_name",
        "ai_api_key",
        "ai_base_url",
        "ai_model",
        "qwen_api_key",
        "qwen_base_url",
        "qwen_model",
        "ai_timeout_seconds",
        mode="before",
    )
    @classmethod
    def blank_optional_values_are_unset(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("ai_model", "qwen_model", "ai_provider_name")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("ai_api_key", "qwen_api_key")
    @classmethod
    def api_key_must_not_be_blank(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        if not value.get_secret_value().strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def require_compatible_endpoint_settings(self) -> "Settings":
        missing: list[str] = []
        if self.api_key is None:
            missing.append("API key")
        if self.base_url is None:
            missing.append("base URL")
        if self.model_name is None:
            missing.append("model")
        if missing:
            raise ValueError("missing " + ", ".join(missing))
        return self

    @property
    def api_key(self) -> SecretStr | None:
        return self.ai_api_key or self.qwen_api_key

    @property
    def base_url(self) -> AnyHttpUrl | None:
        return self.ai_base_url or self.qwen_base_url

    @property
    def model_name(self) -> str | None:
        return self.ai_model or self.qwen_model

    @property
    def timeout_seconds(self) -> float:
        return self.ai_timeout_seconds or self.qwen_timeout_seconds

    @property
    def provider_display_name(self) -> str:
        if self.ai_provider_name:
            return self.ai_provider_name
        return {
            "qwen": "Qwen Cloud",
            "nvidia_nim": "NVIDIA NIM",
            "openai_compatible": "OpenAI-compatible API",
        }[self.ai_provider]


def load_settings(env_file: str | Path = ".env") -> Settings:
    """Load settings without including secret values in error messages."""

    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        fields = sorted(
            {
                str(error["loc"][0]).upper()
                for error in exc.errors()
                if error["loc"]
            }
        )
        if not fields:
            fields = [
                "AI_API_KEY/AI_BASE_URL/AI_MODEL OR "
                "QWEN_API_KEY/QWEN_BASE_URL/QWEN_MODEL"
            ]
        field_list = ", ".join(fields) or "UNKNOWN"
        raise ConfigurationError(
            f"Invalid or missing configuration: {field_list}. "
            "Check your local .env file; never paste API keys into chat or source code."
        ) from None


def load_local_settings(env_file: str | Path = ".env") -> LocalSettings:
    """Load settings for features that do not depend on Qwen Cloud."""

    try:
        return LocalSettings(_env_file=env_file)
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]).upper() for error in exc.errors()})
        field_list = ", ".join(fields) or "UNKNOWN"
        raise ConfigurationError(
            f"Invalid local configuration: {field_list}. Check your local .env file."
        ) from None



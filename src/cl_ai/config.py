"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, ValidationError, field_validator
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

    ai_provider: Literal["qwen"] = "qwen"
    qwen_api_key: SecretStr
    qwen_base_url: AnyHttpUrl
    qwen_model: str
    clai_max_ai_requests_per_session: int = Field(default=30, ge=1, le=1000)
    qwen_timeout_seconds: float = Field(default=30.0, gt=0, le=300)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("qwen_model")
    @classmethod
    def model_name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("qwen_api_key")
    @classmethod
    def api_key_must_not_be_blank(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be blank")
        return value


def load_settings(env_file: str | Path = ".env") -> Settings:
    """Load settings without including secret values in error messages."""

    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]).upper() for error in exc.errors()})
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



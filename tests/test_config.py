from pathlib import Path

import pytest

from cl_ai.config import ConfigurationError, load_local_settings, load_settings


def test_load_settings_masks_secret_and_reads_valid_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=qwen\n"
        "QWEN_API_KEY=super-secret-test-value\n"
        "QWEN_BASE_URL=https://example.invalid/compatible-mode/v1\n"
        "QWEN_MODEL=test-model\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file)

    assert settings.qwen_model == "test-model"
    assert "super-secret-test-value" not in repr(settings)
    assert str(settings.qwen_api_key) == "**********"


def test_missing_api_key_has_safe_error(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QWEN_BASE_URL=https://example.invalid/compatible-mode/v1\n"
        "QWEN_MODEL=test-model\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError) as error:
        load_settings(env_file)

    assert "QWEN_API_KEY" in str(error.value)
    assert "test-model" not in str(error.value)


def test_blank_api_key_has_safe_error(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QWEN_API_KEY=\n"
        "QWEN_BASE_URL=https://example.invalid/compatible-mode/v1\n"
        "QWEN_MODEL=test-model\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError) as error:
        load_settings(env_file)

    assert "QWEN_API_KEY" in str(error.value)
    assert "test-model" not in str(error.value)


def test_local_settings_do_not_require_qwen(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "vault-data"
    monkeypatch.setenv("CLAI_DATA_DIR", str(data_dir))
    for name in ("QWEN_API_KEY", "QWEN_BASE_URL", "QWEN_MODEL"):
        monkeypatch.delenv(name, raising=False)

    settings = load_local_settings(tmp_path / "missing.env")

    assert settings.database_path == data_dir / "cl_ai.db"


def test_nvidia_nim_uses_generic_openai_compatible_settings(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=nvidia_nim\n"
        "AI_API_KEY=private-test-value\n"
        "AI_BASE_URL=https://integrate.api.nvidia.com/v1\n"
        "AI_MODEL=test/nim-model\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file)

    assert settings.provider_display_name == "NVIDIA NIM"
    assert settings.model_name == "test/nim-model"
    assert str(settings.base_url).startswith("https://integrate.api.nvidia.com")
    assert "private-test-value" not in repr(settings)


def test_legacy_nvidia_endpoint_has_correct_name_and_help_timeout(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=qwen\n"
        "QWEN_API_KEY=private-test-value\n"
        "QWEN_BASE_URL=https://integrate.api.nvidia.com/v1\n"
        "QWEN_MODEL=test-model\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file)

    assert settings.provider_display_name == "NVIDIA NIM"
    assert settings.helpme_ai_timeout_seconds == 120.0


def test_blank_generic_values_fall_back_to_legacy_qwen_settings(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AI_PROVIDER=qwen\n"
        "AI_API_KEY=\nAI_BASE_URL=\nAI_MODEL=\n"
        "QWEN_API_KEY=legacy-private-value\n"
        "QWEN_BASE_URL=https://example.invalid/v1\n"
        "QWEN_MODEL=legacy-model\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file)

    assert settings.model_name == "legacy-model"
    assert settings.api_key.get_secret_value() == "legacy-private-value"


from typer.testing import CliRunner

from cl_ai.ai.schemas import CommandComponent, CommandDocumentation, RiskLevel
from cl_ai.cli import app
from cl_ai.vault.documenter import DocumentationGenerationError


runner = CliRunner()


def generated_documentation() -> CommandDocumentation:
    return CommandDocumentation(
        title="Preview Terraform changes",
        category="Terraform",
        subcategory="Planning",
        description="Shows proposed infrastructure changes without applying them.",
        flag_breakdown=[
            CommandComponent(token="plan", explanation="Create a change preview.")
        ],
        tags=["terraform", "plan"],
        risk_level=RiskLevel.LOW,
        risk_notes=["Review the output before applying changes."],
    )


def test_version_does_not_require_configuration() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "CL-AI 0.1.0" in result.stdout


def test_missing_configuration_fails_safely(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("QWEN_API_KEY", "QWEN_BASE_URL", "QWEN_MODEL"):
        monkeypatch.delenv(name, raising=False)

    result = runner.invoke(app)

    assert result.exit_code == 2
    assert "Configuration error" in result.output
    assert "QWEN_API_KEY" in result.output


def test_vault_save_and_list_work_without_qwen(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    environment = {"CLAI_DATA_DIR": str(data_dir)}
    for name in ("QWEN_API_KEY", "QWEN_BASE_URL", "QWEN_MODEL"):
        monkeypatch.delenv(name, raising=False)

    saved = runner.invoke(
        app,
        [
            "save",
            "docker compose ps",
            "--title",
            "Compose status",
            "--yes",
            "--no-ai",
        ],
        env=environment,
    )
    listed = runner.invoke(app, ["list"], env=environment)
    shown = runner.invoke(app, ["show", "1"], env=environment)

    assert saved.exit_code == 0
    assert "Saved command #1" in saved.output
    assert listed.exit_code == 0
    assert "docker compose ps" in listed.output
    assert "saved" in listed.output
    assert shown.exit_code == 0
    assert "Compose status" in shown.output


def test_save_last_reads_captured_command_from_stdin(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}

    saved = runner.invoke(
        app,
        ["save-last", "--from-stdin", "--yes", "--no-ai"],
        input='docker compose ps --format "table {{.Name}}"',
        env=environment,
    )
    shown = runner.invoke(app, ["show", "1"], env=environment)

    assert saved.exit_code == 0
    assert "Source" in saved.output
    assert "captured" in saved.output
    assert shown.exit_code == 0
    assert 'docker compose ps --format "table {{.Name}}"' in shown.output
    assert "captured" in shown.output


def test_save_last_has_manual_paste_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}

    saved = runner.invoke(
        app,
        ["save-last", "--yes", "--no-ai"],
        input="git status --short\n",
        env=environment,
    )

    assert saved.exit_code == 0
    assert "integration is not active" in saved.output
    assert "pasted" in saved.output


def test_empty_captured_stdin_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}

    result = runner.invoke(
        app,
        ["save-last", "--from-stdin", "--yes", "--no-ai"],
        input="",
        env=environment,
    )

    assert result.exit_code == 1
    assert "No previous Git Bash command" in result.output


def test_captured_secret_is_rejected_without_echoing_it(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}
    fake_secret = "captured-sensitive-value"

    result = runner.invoke(
        app,
        ["save-last", "--from-stdin", "--yes", "--no-ai"],
        input=f"deploy --token {fake_secret}",
        env=environment,
    )

    assert result.exit_code == 1
    assert "sensitive data" in result.output
    assert fake_secret not in result.output


def test_shell_init_prints_opt_in_wrapper() -> None:
    result = runner.invoke(app, ["shell-init"])

    assert result.exit_code == 0
    assert "cl-ai()" in result.output
    assert "builtin fc" in result.output
    assert "eval" not in result.output


def test_cancelled_save_writes_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}

    cancelled = runner.invoke(
        app,
        ["save", "git status", "--no-ai"],
        input="n\n",
        env=environment,
    )
    listed = runner.invoke(app, ["list"], env=environment)

    assert cancelled.exit_code == 0
    assert "nothing was written" in cancelled.output
    assert "No commands are saved" in listed.output


def test_cli_rejects_secret_without_echoing_it(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}
    fake_secret = "literal-sensitive-value"

    result = runner.invoke(
        app,
        ["save", f"deploy --token {fake_secret}", "--yes", "--no-ai"],
        env=environment,
    )

    assert result.exit_code == 1
    assert "sensitive data" in result.output
    assert fake_secret not in result.output


def test_cli_edit_and_confirmed_delete_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}
    saved = runner.invoke(
        app,
        ["save", "git status", "--yes", "--no-ai"],
        env=environment,
    )
    assert saved.exit_code == 0

    edited = runner.invoke(
        app,
        ["edit", "1"],
        input="git status --short\nConcise status\nBefore commits\ny\n",
        env=environment,
    )
    assert edited.exit_code == 0
    assert "Updated command #1" in edited.output

    cancelled_delete = runner.invoke(
        app,
        ["delete", "1"],
        input="n\n",
        env=environment,
    )
    assert cancelled_delete.exit_code == 0
    assert "nothing was removed" in cancelled_delete.output

    deleted = runner.invoke(app, ["delete", "1", "--yes"], env=environment)
    missing = runner.invoke(app, ["show", "1"], env=environment)

    assert deleted.exit_code == 0
    assert "does not provide undo" in deleted.output
    assert missing.exit_code == 1
    assert "not found" in missing.output


def test_ai_documentation_is_previewed_and_saved(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}
    monkeypatch.setattr(
        "cl_ai.cli._generate_documentation",
        lambda command: (generated_documentation(), "test-qwen-model"),
    )

    saved = runner.invoke(
        app,
        ["save", "terraform plan", "--yes"],
        env=environment,
    )
    shown = runner.invoke(app, ["show", "1"], env=environment)

    assert saved.exit_code == 0
    assert "AI documentation preview" in saved.output
    assert shown.exit_code == 0
    assert "Preview Terraform changes" in shown.output
    assert "ai_generated" in shown.output
    assert "test-qwen-model" in shown.output


def test_cancelled_ai_preview_writes_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}
    monkeypatch.setattr(
        "cl_ai.cli._generate_documentation",
        lambda command: (generated_documentation(), "test-qwen-model"),
    )

    cancelled = runner.invoke(
        app,
        ["save", "terraform plan"],
        input="c\n",
        env=environment,
    )
    listed = runner.invoke(app, ["list"], env=environment)

    assert cancelled.exit_code == 0
    assert "nothing was written" in cancelled.output
    assert "No commands are saved" in listed.output


def test_documentation_failure_does_not_save(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    environment = {"CLAI_DATA_DIR": str(tmp_path / "data")}

    def fail_documentation(command):
        raise DocumentationGenerationError("malformed documentation; nothing was saved")

    monkeypatch.setattr("cl_ai.cli._generate_documentation", fail_documentation)

    failed = runner.invoke(
        app,
        ["save", "terraform plan", "--yes"],
        env=environment,
    )
    listed = runner.invoke(app, ["list"], env=environment)

    assert failed.exit_code == 1
    assert "nothing was saved" in failed.output
    assert "No commands are saved" in listed.output


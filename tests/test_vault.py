import pytest

from cl_ai.ai.schemas import CommandComponent, CommandDocumentation, RiskLevel
from cl_ai.storage import Database
from cl_ai.vault.models import DocumentationSource
from cl_ai.vault.repository import CommandRepository
from cl_ai.vault.service import (
    CommandNotFoundError,
    CommandVault,
    DuplicateCommandError,
    SensitiveCommandError,
)


def build_vault(database_path) -> CommandVault:
    database = Database(database_path)
    database.initialize()
    return CommandVault(CommandRepository(database))


def test_save_and_reopen_preserves_exact_command(tmp_path) -> None:
    database_path = tmp_path / "cl_ai.db"
    command = 'git commit -m "fix quoted value" && echo "done"'
    first_vault = build_vault(database_path)

    saved = first_vault.save(
        command,
        title="Quoted command",
        working_directory="/example/project",
        shell="bash",
    )
    reopened = build_vault(database_path).get(saved.id)

    assert reopened.command_text == command
    assert reopened.title == "Quoted command"
    assert reopened.working_directory == "/example/project"
    assert reopened.verification_state.value == "saved"


def test_duplicate_requires_explicit_override(tmp_path) -> None:
    vault = build_vault(tmp_path / "cl_ai.db")
    original = vault.save("docker compose ps")

    with pytest.raises(DuplicateCommandError) as error:
        vault.save("docker compose ps")

    assert error.value.existing.id == original.id
    duplicate = vault.save("docker compose ps", allow_duplicate=True)
    assert duplicate.id != original.id


def test_update_and_delete(tmp_path) -> None:
    vault = build_vault(tmp_path / "cl_ai.db")
    saved = vault.save("git status")

    updated = vault.update(
        saved.id,
        command_text="git status --short",
        title="Concise Git status",
        notes="Useful before committing",
    )

    assert updated.command_text == "git status --short"
    assert updated.title == "Concise Git status"
    assert updated.updated_at >= saved.updated_at

    vault.delete(saved.id)
    with pytest.raises(CommandNotFoundError):
        vault.get(saved.id)


def test_sensitive_command_is_never_written(tmp_path) -> None:
    vault = build_vault(tmp_path / "cl_ai.db")

    with pytest.raises(SensitiveCommandError):
        vault.save("deploy --token literal-sensitive-value")

    assert vault.list() == []


def test_ai_documentation_persists_with_provenance(tmp_path) -> None:
    database_path = tmp_path / "cl_ai.db"
    vault = build_vault(database_path)
    documentation = CommandDocumentation(
        title="List Compose services",
        category="Docker",
        subcategory="Compose status",
        description="Lists services in the current Compose project.",
        flag_breakdown=[
            CommandComponent(token="ps", explanation="Show service status.")
        ],
        tags=["docker", "compose"],
        risk_level=RiskLevel.LOW,
        risk_notes=[],
    )

    saved = vault.save(
        "docker compose ps",
        documentation=documentation,
        documentation_source=DocumentationSource.AI_GENERATED,
        ai_model="test-qwen-model",
    )
    reopened = build_vault(database_path).get(saved.id)

    assert reopened.description == documentation.description
    assert reopened.flag_breakdown[0].token == "ps"
    assert reopened.tags == ["docker", "compose"]
    assert reopened.documentation_source is DocumentationSource.AI_GENERATED
    assert reopened.ai_model == "test-qwen-model"
    assert reopened.documented_at is not None


def test_changing_command_text_clears_stale_documentation(tmp_path) -> None:
    vault = build_vault(tmp_path / "cl_ai.db")
    documentation = CommandDocumentation(
        title="Git status",
        category="Git",
        subcategory="Working tree",
        description="Shows working-tree changes.",
        flag_breakdown=[],
        tags=["git"],
        risk_level=RiskLevel.LOW,
        risk_notes=[],
    )
    saved = vault.save("git status", documentation=documentation, ai_model="test-model")

    updated = vault.update(
        saved.id,
        command_text="git log --oneline",
        title="Git log",
        notes=None,
    )

    assert updated.command_text == "git log --oneline"
    assert updated.description is None
    assert updated.tags == []
    assert updated.documentation_source is DocumentationSource.MANUAL
    assert updated.ai_model is None


def test_natural_language_search_uses_saved_fields_and_category(tmp_path) -> None:
    vault = build_vault(tmp_path / "cl_ai.db")
    terraform = CommandDocumentation(
        title="Inspect saved Terraform plan",
        category="Terraform",
        subcategory="Inspection",
        description="Shows a previously created infrastructure plan.",
        flag_breakdown=[],
        tags=["terraform", "plan", "inspect"],
        risk_level=RiskLevel.LOW,
        risk_notes=[],
    )
    docker = CommandDocumentation(
        title="Inspect Compose services",
        category="Docker",
        subcategory="Status",
        description="Shows running Compose services.",
        flag_breakdown=[],
        tags=["docker", "compose"],
        risk_level=RiskLevel.LOW,
        risk_notes=[],
    )
    expected = vault.save("terraform show tfplan", documentation=terraform)
    vault.save("docker compose ps", documentation=docker)

    matches = vault.search(
        "What did I use to inspect my infrastructure plan?",
        category="terraform",
    )

    assert [record.id for record in matches] == [expected.id]
    assert vault.search("a command that was never saved") == []


def test_researched_source_urls_survive_restart(tmp_path) -> None:
    database_path = tmp_path / "cl_ai.db"
    saved = build_vault(database_path).save(
        "terraform import ADDRESS ID",
        source_urls=["https://developer.hashicorp.com/terraform/cli/commands/import"],
    )

    reopened = build_vault(database_path).get(saved.id)

    assert reopened.source_urls == [
        "https://developer.hashicorp.com/terraform/cli/commands/import"
    ]


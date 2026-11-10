"""Command Vault rules independent of the terminal UI."""

from datetime import datetime, timezone
import os
from pathlib import Path

from cl_ai.ai.schemas import CommandDocumentation
from cl_ai.security import SecretDetector
from cl_ai.vault.models import (
    CommandCreate,
    CommandRecord,
    CommandSource,
    DocumentationSource,
)
from cl_ai.vault.repository import CommandRepository


class VaultError(RuntimeError):
    """Base class for safe Command Vault errors."""


class CommandNotFoundError(VaultError):
    def __init__(self, command_id: int) -> None:
        super().__init__(f"Command #{command_id} was not found.")


class DuplicateCommandError(VaultError):
    def __init__(self, existing: CommandRecord) -> None:
        self.existing = existing
        super().__init__(f"This exact command is already saved as #{existing.id}.")


class SensitiveCommandError(VaultError):
    def __init__(self, categories: list[str]) -> None:
        category_list = ", ".join(categories)
        super().__init__(
            "The command was not saved because it may contain sensitive data "
            f"({category_list}). Replace literal credentials with environment-variable "
            "references and try again."
        )


class CommandVault:
    """Enforce safety, duplicate, and record-state rules around persistence."""

    def __init__(
        self,
        repository: CommandRepository,
        detector: SecretDetector | None = None,
    ) -> None:
        self.repository = repository
        self.detector = detector or SecretDetector()

    def ensure_safe(self, command_text: str) -> None:
        findings = self.detector.scan(command_text)
        if findings:
            raise SensitiveCommandError([finding.category for finding in findings])

    def find_duplicate(
        self, command_text: str, *, exclude_id: int | None = None
    ) -> CommandRecord | None:
        for record in self.repository.find_exact(command_text):
            if record.id != exclude_id:
                return record
        return None

    def save(
        self,
        command_text: str,
        *,
        title: str | None = None,
        notes: str | None = None,
        allow_duplicate: bool = False,
        working_directory: str | None = None,
        shell: str | None = None,
        documentation: CommandDocumentation | None = None,
        documentation_source: DocumentationSource | None = None,
        ai_model: str | None = None,
        source: CommandSource = CommandSource.PASTED,
    ) -> CommandRecord:
        self.ensure_safe(command_text)
        duplicate = self.find_duplicate(command_text)
        if duplicate is not None and not allow_duplicate:
            raise DuplicateCommandError(duplicate)

        context_directory = working_directory or str(Path.cwd())
        context_shell = shell or os.environ.get("SHELL") or os.environ.get("COMSPEC")
        if documentation is not None and documentation_source is None:
            documentation_source = DocumentationSource.AI_GENERATED
        normalized_title = title.strip() if title and title.strip() else None
        return self.repository.create(
            CommandCreate(
                command_text=command_text,
                title=normalized_title or (
                    documentation.title if documentation else None
                ),
                notes=notes,
                category=documentation.category if documentation else None,
                subcategory=documentation.subcategory if documentation else None,
                description=documentation.description if documentation else None,
                flag_breakdown=(
                    documentation.flag_breakdown if documentation else []
                ),
                tags=documentation.tags if documentation else [],
                risk_level=documentation.risk_level if documentation else None,
                risk_notes=documentation.risk_notes if documentation else [],
                documentation_source=documentation_source,
                ai_model=ai_model if documentation else None,
                documented_at=(
                    datetime.now(timezone.utc) if documentation else None
                ),
                source=source,
                working_directory=context_directory,
                shell=context_shell,
            )
        )

    def get(self, command_id: int) -> CommandRecord:
        record = self.repository.get(command_id)
        if record is None:
            raise CommandNotFoundError(command_id)
        return record

    def list(self, limit: int = 50) -> list[CommandRecord]:
        return self.repository.list(limit)

    def update(
        self,
        command_id: int,
        *,
        command_text: str,
        title: str | None,
        notes: str | None,
        allow_duplicate: bool = False,
    ) -> CommandRecord:
        current = self.get(command_id)
        self.ensure_safe(command_text)
        duplicate = self.find_duplicate(command_text, exclude_id=current.id)
        if duplicate is not None and not allow_duplicate:
            raise DuplicateCommandError(duplicate)

        updated = self.repository.update(
            command_id,
            command_text=command_text,
            title=title,
            notes=notes,
        )
        if updated is None:
            raise CommandNotFoundError(command_id)
        if command_text != current.command_text:
            self.repository.clear_documentation(command_id)
            updated = self.get(command_id)
        return updated

    def delete(self, command_id: int) -> None:
        if not self.repository.delete(command_id):
            raise CommandNotFoundError(command_id)


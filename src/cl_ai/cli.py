"""Typer entry point for CL-AI chat and Command Vault operations."""

from datetime import timezone
from importlib.resources import files
import sys
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cl_ai import __version__
from cl_ai.ai import create_provider
from cl_ai.ai.provider import ProviderError
from cl_ai.ai.schemas import CommandDocumentation, RiskLevel
from cl_ai.chat import run_chat
from cl_ai.config import (
    ConfigurationError,
    load_local_settings,
    load_settings,
)
from cl_ai.helpme import OnlineHelpError, OnlineHelpService, WebRetriever
from cl_ai.shell import ShellCaptureError, read_captured_command
from cl_ai.storage import Database, DatabaseError
from cl_ai.vault.documenter import CommandDocumenter, DocumentationGenerationError
from cl_ai.vault.models import CommandRecord, CommandSource, DocumentationSource
from cl_ai.vault.repository import CommandRepository
from cl_ai.vault.service import CommandVault, VaultError


app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False,
    help="A terminal-first conversational DevOps and SRE assistant.",
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"CL-AI {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
    helpme_alias: Annotated[
        str | None,
        typer.Option(
            "-helpme",
            help="Research a question using current official online documentation.",
        ),
    ] = None,
) -> None:
    """Start chat with no command, or use a Command Vault subcommand."""

    del version
    if ctx.invoked_subcommand is not None:
        return
    if helpme_alias is not None:
        helpme_command(helpme_alias)
        raise typer.Exit()

    console = Console()
    try:
        settings = load_settings()
        provider = create_provider(settings)
    except (ConfigurationError, ProviderError) as exc:
        error_console = Console(stderr=True)
        error_console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=2) from None

    run_chat(
        provider,
        settings.clai_max_ai_requests_per_session,
        console=console,
        provider_name=settings.provider_display_name,
    )


def _create_vault() -> CommandVault:
    settings = load_local_settings()
    database = Database(settings.database_path)
    database.initialize()
    return CommandVault(CommandRepository(database))


def _exit_with_error(error: Exception) -> NoReturn:
    Console(stderr=True).print(f"[bold red]CL-AI error:[/bold red] {error}")
    raise typer.Exit(code=1)


def _format_timestamp(record_time) -> str:
    return record_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _verification_label(value: str) -> str:
    labels = {
        "saved": "Saved only; not tested",
        "user_reported_worked": "User says it worked",
        "execution_verified": "Execution verified",
    }
    return labels.get(value, value)


def _record_panel(record: CommandRecord) -> Panel:
    details = Table.grid(padding=(0, 1))
    details.add_column(style="cyan", no_wrap=True)
    details.add_column()
    details.add_row("ID", str(record.id))
    details.add_row("Command", Text(record.command_text))
    details.add_row("Title", Text(record.title or "-"))
    details.add_row("Notes", Text(record.notes or "-"))
    if record.category:
        details.add_row("Category", Text(record.category))
    if record.subcategory:
        details.add_row("Subcategory", Text(record.subcategory))
    if record.description:
        details.add_row("Description", Text(record.description))
    if record.flag_breakdown:
        breakdown = "\n".join(
            f"{part.token}: {part.explanation}" for part in record.flag_breakdown
        )
        details.add_row("Command breakdown", Text(breakdown))
    if record.tags:
        details.add_row("Tags", Text(", ".join(record.tags)))
    if record.risk_level:
        details.add_row("Risk level", record.risk_level.value)
    if record.risk_notes:
        details.add_row("Risk notes", Text("\n".join(record.risk_notes)))
    details.add_row("Command source", record.source.value)
    details.add_row(
        "Documentation",
        record.documentation_source.value if record.documentation_source else "manual",
    )
    if record.ai_model:
        details.add_row("AI model", Text(record.ai_model))
    if record.source_urls:
        details.add_row("Source URLs", Text("\n".join(record.source_urls)))
    details.add_row(
        "Verification state",
        _verification_label(record.verification_state.value),
    )
    details.add_row("Directory", Text(record.working_directory or "-"))
    details.add_row("Shell", Text(record.shell or "-"))
    details.add_row("Created", _format_timestamp(record.created_at))
    details.add_row("Updated", _format_timestamp(record.updated_at))
    return Panel(details, title=f"Command #{record.id}", border_style="cyan")


def _draft_panel(
    command: str,
    title: str | None,
    notes: str | None,
    source: CommandSource = CommandSource.PASTED,
) -> Panel:
    details = Table.grid(padding=(0, 1))
    details.add_column(style="cyan", no_wrap=True)
    details.add_column()
    details.add_row("Command", Text(command))
    details.add_row("Title", Text(title or "-"))
    details.add_row("Notes", Text(notes or "-"))
    details.add_row("Source", source.value)
    details.add_row("Verification", "saved (not proof it worked)")
    return Panel(details, title="Save preview", border_style="yellow")


def _documentation_panel(
    command: str,
    documentation: CommandDocumentation,
) -> Panel:
    details = Table.grid(padding=(0, 1))
    details.add_column(style="cyan", no_wrap=True)
    details.add_column()
    details.add_row("Command", Text(command))
    details.add_row("Title", Text(documentation.title))
    details.add_row("Category", Text(documentation.category))
    details.add_row("Subcategory", Text(documentation.subcategory))
    details.add_row("Description", Text(documentation.description))
    if documentation.flag_breakdown:
        breakdown = "\n".join(
            f"{part.token}: {part.explanation}"
            for part in documentation.flag_breakdown
        )
        details.add_row("Command breakdown", Text(breakdown))
    details.add_row("Tags", Text(", ".join(documentation.tags) or "-"))
    details.add_row("Risk level", documentation.risk_level.value)
    details.add_row(
        "Risk notes", Text("\n".join(documentation.risk_notes) or "None identified")
    )
    details.add_row("Verification state", "Saved only; not tested")
    return Panel(details, title="AI documentation preview", border_style="yellow")


def _generate_documentation(command: str) -> tuple[CommandDocumentation, str]:
    settings = load_settings()
    provider = create_provider(settings)
    documentation = CommandDocumenter(provider).generate(command)
    return documentation, settings.model_name


def _edit_documentation(
    documentation: CommandDocumentation,
) -> CommandDocumentation:
    title = typer.prompt("Title", default=documentation.title)
    category = typer.prompt("Category", default=documentation.category)
    subcategory = typer.prompt("Subcategory", default=documentation.subcategory)
    description = typer.prompt("Description", default=documentation.description)
    tags_text = typer.prompt("Tags (comma-separated)", default=", ".join(documentation.tags))
    tags = [item.strip() for item in tags_text.split(",") if item.strip()]

    valid_levels = {level.value for level in RiskLevel}
    risk_level_text = typer.prompt(
        "Risk level [low/medium/high/critical]",
        default=documentation.risk_level.value,
    ).strip().lower()
    while risk_level_text not in valid_levels:
        risk_level_text = typer.prompt(
            "Enter low, medium, high, or critical",
            default=documentation.risk_level.value,
        ).strip().lower()

    risk_notes_text = typer.prompt(
        "Risk notes (separate with |)",
        default=" | ".join(documentation.risk_notes),
        show_default=False,
    )
    risk_notes = [item.strip() for item in risk_notes_text.split("|") if item.strip()]

    return CommandDocumentation.model_validate(
        {
            **documentation.model_dump(),
            "title": title.strip(),
            "category": category.strip(),
            "subcategory": subcategory.strip(),
            "description": description.strip(),
            "tags": tags,
            "risk_level": RiskLevel(risk_level_text),
            "risk_notes": risk_notes,
        }
    )


def _review_choice() -> str:
    while True:
        choice = typer.prompt(
            "Choose [S]ave, [E]dit, or [C]ancel", default="S"
        ).strip().lower()
        if choice in {"s", "save", "e", "edit", "c", "cancel"}:
            return choice[0]
        Console().print("Enter S, E, or C.")


def _save_command_workflow(
    command: str,
    *,
    title: str | None,
    notes: str | None,
    yes: bool,
    no_ai: bool,
    source: CommandSource,
    source_urls: list[str] | None = None,
) -> None:
    """Review and save command text without executing it."""

    console = Console()
    try:
        vault = _create_vault()
        vault.ensure_safe(command)
        duplicate = vault.find_duplicate(command)
        allow_duplicate = False
        if duplicate is not None:
            console.print(
                f"[yellow]This exact command is already saved as #{duplicate.id}.[/yellow]"
            )
            allow_duplicate = typer.confirm(
                "Save another contextual copy?", default=False
            )
            if not allow_duplicate:
                console.print("Save cancelled; the existing record was unchanged.")
                return

        documentation = None
        documentation_source = None
        ai_model = None
        if no_ai:
            console.print(_draft_panel(command, title, notes, source))
            if not yes and not typer.confirm("Save this command?", default=False):
                console.print("Save cancelled; nothing was written.")
                return
        else:
            console.print(
                "[cyan]Sending the secret-checked command to the configured AI provider for "
                "documentation...[/cyan]"
            )
            documentation, ai_model = _generate_documentation(command)
            documentation_source = DocumentationSource.AI_GENERATED
            if title and title.strip():
                documentation = CommandDocumentation.model_validate(
                    {**documentation.model_dump(), "title": title.strip()}
                )
                documentation_source = DocumentationSource.AI_EDITED

            console.print(
                _documentation_panel(
                    command,
                    documentation,
                )
            )
            if not yes:
                choice = _review_choice()
                if choice == "c":
                    console.print("Save cancelled; nothing was written.")
                    return
                if choice == "e":
                    documentation = _edit_documentation(documentation)
                    documentation_source = DocumentationSource.AI_EDITED
                    console.print(
                        _documentation_panel(
                            command,
                            documentation,
                        )
                    )
                    if not typer.confirm(
                        "Save this edited documentation?", default=False
                    ):
                        console.print("Save cancelled; nothing was written.")
                        return

        record = vault.save(
            command,
            title=title,
            notes=notes,
            allow_duplicate=allow_duplicate,
            documentation=documentation,
            documentation_source=documentation_source,
            ai_model=ai_model,
            source=source,
            source_urls=source_urls,
        )
    except (
        ConfigurationError,
        DatabaseError,
        DocumentationGenerationError,
        ProviderError,
        VaultError,
    ) as exc:
        _exit_with_error(exc)

    console.print(f"[green]Saved command #{record.id}.[/green]")


@app.command("save")
def save_command(
    command: Annotated[str, typer.Argument(help="Exact command text to save.")],
    title: Annotated[str | None, typer.Option("--title", help="Optional title.")] = None,
    notes: Annotated[str | None, typer.Option("--notes", help="Optional notes.")] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Save after preview without prompting."),
    ] = False,
    no_ai: Annotated[
        bool,
        typer.Option(
            "--no-ai",
            help="Save manually without sending the command to the AI provider.",
        ),
    ] = False,
) -> None:
    """Review and save a pasted command without executing it."""

    _save_command_workflow(
        command,
        title=title,
        notes=notes,
        yes=yes,
        no_ai=no_ai,
        source=CommandSource.PASTED,
        source_urls=None,
    )


@app.command("save-last")
def save_last_command(
    from_stdin: Annotated[
        bool,
        typer.Option(
            "--from-stdin",
            help="Read command text from the trusted Git Bash wrapper.",
        ),
    ] = False,
    title: Annotated[str | None, typer.Option("--title", help="Optional title.")] = None,
    notes: Annotated[str | None, typer.Option("--notes", help="Optional notes.")] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Save after preview without prompting."),
    ] = False,
    no_ai: Annotated[
        bool,
        typer.Option(
            "--no-ai",
            help="Save manually without sending the command to the AI provider.",
        ),
    ] = False,
) -> None:
    """Save the previous Git Bash command, with a manual-paste fallback."""

    source = CommandSource.CAPTURED
    if from_stdin:
        try:
            command = read_captured_command(sys.stdin)
        except ShellCaptureError as exc:
            _exit_with_error(exc)
    else:
        Console().print(
            "Git Bash integration is not active. Paste the command instead, "
            "or run: source <(cl-ai shell-init)"
        )
        command = typer.prompt("Command to save")
        source = CommandSource.PASTED

    _save_command_workflow(
        command,
        title=title,
        notes=notes,
        yes=yes,
        no_ai=no_ai,
        source=source,
        source_urls=None,
    )


@app.command("shell-init")
def shell_init() -> None:
    """Print the optional Git Bash wrapper for the current shell."""

    integration = (
        files("cl_ai.shell")
        .joinpath("cl_ai.bash")
        .read_text(encoding="utf-8")
    )
    typer.echo(integration, nl=False)


@app.command("list")
def list_commands(
    limit: Annotated[
        int,
        typer.Option("--limit", min=1, max=500, help="Maximum records to show."),
    ] = 50,
    category: Annotated[
        str | None,
        typer.Option("--category", help="Only show this technology category."),
    ] = None,
) -> None:
    """List locally saved commands."""

    console = Console()
    try:
        records = _create_vault().list(limit, category=category)
    except (ConfigurationError, DatabaseError, VaultError) as exc:
        _exit_with_error(exc)

    if not records:
        console.print("No commands are saved yet.")
        return

    table = Table(title="Command Vault")
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title")
    table.add_column("Command")
    table.add_column("State", no_wrap=True)
    table.add_column("Saved", no_wrap=True)
    for record in records:
        table.add_row(
            str(record.id),
            Text(record.title or "-"),
            Text(record.command_text),
            record.verification_state.value,
            _format_timestamp(record.created_at),
        )
    console.print(table)


@app.command("find")
def find_commands(
    query: Annotated[str, typer.Argument(help="Natural-language Vault search.")],
    category: Annotated[
        str | None,
        typer.Option("--category", help="Only search this technology category."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", min=1, max=50, help="Maximum matches to show."),
    ] = 10,
) -> None:
    """Find real saved commands; no model-generated commands are added."""

    console = Console()
    try:
        records = _create_vault().search(query, category=category, limit=limit)
    except (ConfigurationError, DatabaseError, VaultError) as exc:
        _exit_with_error(exc)

    if not records:
        console.print(
            "No saved commands matched. CL-AI did not generate a replacement; "
            "try different terms or use 'cl-ai helpme' for online research."
        )
        return

    console.print(
        f"[bold]Saved Vault matches ({len(records)})[/bold] - these are existing SQLite records."
    )
    for record in records:
        console.print(_record_panel(record))


def _research_help(question: str):
    settings = load_settings()
    provider = create_provider(settings)
    service = OnlineHelpService(
        provider,
        WebRetriever(timeout=settings.web_timeout_seconds),
    )
    return service.research(question)


@app.command("helpme")
def helpme_command(
    question: Annotated[
        str,
        typer.Argument(help="Question or command to research online."),
    ],
    save: Annotated[
        int | None,
        typer.Option(
            "--save",
            min=1,
            help="Review and save the numbered researched command.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Save the selected command after preview."),
    ] = False,
) -> None:
    """Research official online documentation without executing commands."""

    console = Console()
    try:
        research = _research_help(question)
    except (
        ConfigurationError,
        OnlineHelpError,
        ProviderError,
    ) as exc:
        _exit_with_error(exc)

    console.print(Panel(Text(research.explanation), title="Online documentation"))
    if research.prerequisites:
        console.print("[bold]Prerequisites / assumptions[/bold]")
        for item in research.prerequisites:
            console.print(f"- {item}")
    if research.commands:
        console.print("[bold]Useful commands (suggestions only; not executed)[/bold]")
        for index, command in enumerate(research.commands, start=1):
            sources = ", ".join(str(item) for item in command.source_indices)
            console.print(
                f"[cyan]{index}.[/cyan] {command.command}\n"
                f"   {command.explanation}\n"
                f"   Provenance: {command.provenance}; source(s): {sources}; "
                f"risk: {command.risk_level.value}"
            )
            for warning in command.risk_notes:
                console.print(f"   Warning: {warning}")
    if research.warnings:
        console.print("[bold yellow]Warnings[/bold yellow]")
        for warning in research.warnings:
            console.print(f"- {warning}")

    console.print("[bold]Sources (retrieved online)[/bold]")
    for index, document in enumerate(research.documents, start=1):
        console.print(f"{index}. {document.title}\n   {document.url}")

    if save is None:
        if research.commands:
            console.print(
                "To review and save one result with its source URLs, rerun with "
                "--save NUMBER."
            )
        return
    if save > len(research.commands):
        _exit_with_error(
            OnlineHelpError(
                f"Cannot save command {save}; the research returned "
                f"{len(research.commands)} command(s)."
            )
        )

    selected = research.commands[save - 1]
    source_urls = [
        research.documents[index - 1].url for index in selected.source_indices
    ]
    _save_command_workflow(
        selected.command,
        title=f"Researched: {question[:60]}",
        notes=selected.explanation,
        yes=yes,
        no_ai=True,
        source=CommandSource.RESEARCHED,
        source_urls=source_urls,
    )


@app.command("show")
def show_command(
    command_id: Annotated[int, typer.Argument(min=1, help="Command record ID.")],
) -> None:
    """Show a complete saved command record."""

    try:
        record = _create_vault().get(command_id)
    except (ConfigurationError, DatabaseError, VaultError) as exc:
        _exit_with_error(exc)
    Console().print(_record_panel(record))


@app.command("edit")
def edit_command(
    command_id: Annotated[int, typer.Argument(min=1, help="Command record ID.")],
) -> None:
    """Interactively edit a saved command without executing it."""

    console = Console()
    try:
        vault = _create_vault()
        current = vault.get(command_id)
        console.print(_record_panel(current))

        command = typer.prompt("Command", default=current.command_text)
        title = typer.prompt(
            "Title (blank for none)", default=current.title or "", show_default=False
        )
        notes = typer.prompt(
            "Notes (blank for none)", default=current.notes or "", show_default=False
        )
        normalized_title = title.strip() or None
        normalized_notes = notes.strip() or None

        if (
            command == current.command_text
            and normalized_title == current.title
            and normalized_notes == current.notes
        ):
            console.print("No changes detected.")
            return

        vault.ensure_safe(command)
        duplicate = vault.find_duplicate(command, exclude_id=current.id)
        allow_duplicate = False
        if duplicate is not None:
            console.print(
                f"[yellow]The edited command matches existing record #{duplicate.id}.[/yellow]"
            )
            allow_duplicate = typer.confirm("Keep this intentional duplicate?", default=False)
            if not allow_duplicate:
                console.print("Edit cancelled; no changes were written.")
                return

        console.print(
            _draft_panel(
                command,
                normalized_title,
                normalized_notes,
                current.source,
            )
        )
        if not typer.confirm("Apply these changes?", default=False):
            console.print("Edit cancelled; no changes were written.")
            return

        command_changed = command != current.command_text
        updated = vault.update(
            command_id,
            command_text=command,
            title=normalized_title,
            notes=normalized_notes,
            allow_duplicate=allow_duplicate,
        )
    except (ConfigurationError, DatabaseError, VaultError) as exc:
        _exit_with_error(exc)

    console.print(f"[green]Updated command #{updated.id}.[/green]")
    if command_changed and current.documentation_source is not None:
        console.print(
            "[yellow]The command text changed, so its previous AI documentation "
            "was cleared as stale.[/yellow]"
        )


@app.command("delete")
def delete_command(
    command_id: Annotated[int, typer.Argument(min=1, help="Command record ID.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Delete without a confirmation prompt."),
    ] = False,
) -> None:
    """Delete a saved command after explicit confirmation."""

    console = Console()
    try:
        vault = _create_vault()
        record = vault.get(command_id)
        console.print(_record_panel(record))
        if not yes and not typer.confirm(
            "Delete this command permanently?", default=False
        ):
            console.print("Delete cancelled; nothing was removed.")
            return
        vault.delete(command_id)
    except (ConfigurationError, DatabaseError, VaultError) as exc:
        _exit_with_error(exc)

    console.print(
        f"[green]Deleted command #{command_id}.[/green] "
        "This milestone does not provide undo or database backups."
    )


def run() -> None:
    """Console-script wrapper."""

    app()


if __name__ == "__main__":
    run()


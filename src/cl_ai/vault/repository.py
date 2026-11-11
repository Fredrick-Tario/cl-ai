"""Parameterized SQLite operations for Command Vault records."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from cl_ai.storage import Database, DatabaseError
from cl_ai.vault.models import CommandCreate, CommandRecord


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_from_row(row, source_urls: list[str] | None = None) -> CommandRecord:
    data = dict(row)
    try:
        data["flag_breakdown"] = json.loads(data["flag_breakdown"] or "[]")
        data["tags"] = json.loads(data["tags"] or "[]")
        data["risk_notes"] = json.loads(data["risk_notes"] or "[]")
        data["source_urls"] = source_urls or []
        return CommandRecord.model_validate(data)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise DatabaseError(
            "A stored Command Vault record is malformed. Restore a valid backup "
            "or repair the record before continuing."
        ) from exc


class CommandRepository:
    """Persist commands without embedding presentation or AI behavior."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, command: CommandCreate) -> CommandRecord:
        timestamp = _utc_now()
        with self.database.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO commands (
                    command_text, title, notes, category, subcategory, description,
                    flag_breakdown, tags, risk_level, risk_notes,
                    documentation_source, ai_model, documented_at,
                    source, verification_state, working_directory, shell,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    command.command_text,
                    command.title,
                    command.notes,
                    command.category,
                    command.subcategory,
                    command.description,
                    json.dumps(
                        [part.model_dump() for part in command.flag_breakdown],
                        ensure_ascii=False,
                    ),
                    json.dumps(command.tags, ensure_ascii=False),
                    command.risk_level.value if command.risk_level else None,
                    json.dumps(command.risk_notes, ensure_ascii=False),
                    (
                        command.documentation_source.value
                        if command.documentation_source
                        else None
                    ),
                    command.ai_model,
                    (
                        command.documented_at.isoformat()
                        if command.documented_at
                        else None
                    ),
                    command.source.value,
                    command.verification_state.value,
                    command.working_directory,
                    command.shell,
                    timestamp,
                    timestamp,
                ),
            )
            row = connection.execute(
                "SELECT * FROM commands WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            for url in command.source_urls:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO command_sources (
                        command_id, url, created_at
                    ) VALUES (?, ?, ?)
                    """,
                    (cursor.lastrowid, url, timestamp),
                )
        return _record_from_row(row, command.source_urls)

    def _source_urls(self, connection, command_id: int) -> list[str]:
        rows = connection.execute(
            "SELECT url FROM command_sources WHERE command_id = ? ORDER BY id",
            (command_id,),
        ).fetchall()
        return [row["url"] for row in rows]

    def get(self, command_id: int) -> CommandRecord | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM commands WHERE id = ?", (command_id,)
            ).fetchone()
            urls = self._source_urls(connection, command_id) if row is not None else []
        return _record_from_row(row, urls) if row is not None else None

    def list(
        self, limit: int = 50, *, category: str | None = None
    ) -> list[CommandRecord]:
        with self.database.connection() as connection:
            if category:
                rows = connection.execute(
                    """
                    SELECT * FROM commands
                    WHERE category IS NOT NULL AND lower(category) = lower(?)
                    ORDER BY created_at DESC, id DESC LIMIT ?
                    """,
                    (category, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM commands ORDER BY created_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [
                _record_from_row(row, self._source_urls(connection, row["id"]))
                for row in rows
            ]

    def find_exact(self, command_text: str) -> list[CommandRecord]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM commands
                WHERE command_text = ?
                ORDER BY created_at DESC, id DESC
                """,
                (command_text,),
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def search(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 10,
    ) -> list[CommandRecord]:
        """Search only persisted records using bounded, escaped FTS terms."""

        stop_words = {
            "a", "an", "and", "command", "did", "do", "find", "for", "how",
            "i", "me", "my", "of", "the", "to", "use", "used", "what",
        }
        terms = [
            term.casefold()
            for term in re.findall(r"[A-Za-z0-9_.:-]+", query)
            if len(term) > 1 and term.casefold() not in stop_words
        ]
        terms = list(dict.fromkeys(terms))[:12]
        if not terms:
            return []
        match_query = " OR ".join(f'"{term.replace(chr(34), "")}"*' for term in terms)

        sql = """
            SELECT commands.*
            FROM commands_fts
            JOIN commands ON commands.id = commands_fts.rowid
            WHERE commands_fts MATCH ?
        """
        parameters: list[object] = [match_query]
        if category:
            sql += " AND commands.category IS NOT NULL AND lower(commands.category) = lower(?)"
            parameters.append(category)
        sql += " ORDER BY bm25(commands_fts), commands.updated_at DESC LIMIT ?"
        parameters.append(min(limit * 5, 250))

        with self.database.connection() as connection:
            rows = connection.execute(sql, parameters).fetchall()
            minimum_matches = 1 if len(terms) == 1 else 2
            records: list[CommandRecord] = []
            for row in rows:
                searchable = " ".join(
                    str(row[field] or "").casefold()
                    for field in ("command_text", "title", "description", "tags")
                )
                if sum(term in searchable for term in terms) < minimum_matches:
                    continue
                records.append(
                    _record_from_row(
                        row,
                        self._source_urls(connection, row["id"]),
                    )
                )
                if len(records) >= limit:
                    break
            return records

    def update(
        self,
        command_id: int,
        *,
        command_text: str,
        title: str | None,
        notes: str | None,
    ) -> CommandRecord | None:
        timestamp = _utc_now()
        with self.database.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE commands
                SET command_text = ?, title = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (command_text, title, notes, timestamp, command_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM commands WHERE id = ?", (command_id,)
            ).fetchone()
            urls = self._source_urls(connection, command_id)
        return _record_from_row(row, urls)

    def clear_documentation(self, command_id: int) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """
                UPDATE commands
                SET category = NULL,
                    subcategory = NULL,
                    description = NULL,
                    flag_breakdown = '[]',
                    tags = '[]',
                    risk_level = NULL,
                    risk_notes = '[]',
                    documentation_source = 'manual',
                    ai_model = NULL,
                    documented_at = NULL
                WHERE id = ?
                """,
                (command_id,),
            )

    def delete(self, command_id: int) -> bool:
        with self.database.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM commands WHERE id = ?", (command_id,)
            )
        return cursor.rowcount > 0


"""SQLite connection management and schema initialization."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3


SCHEMA_VERSION = 2

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_text TEXT NOT NULL,
    title TEXT,
    notes TEXT,
    category TEXT,
    subcategory TEXT,
    description TEXT,
    flag_breakdown TEXT NOT NULL DEFAULT '[]',
    tags TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    risk_notes TEXT NOT NULL DEFAULT '[]',
    documentation_source TEXT CHECK (
        documentation_source IN ('ai_generated', 'ai_edited', 'manual')
    ),
    ai_model TEXT,
    documented_at TEXT,
    source TEXT NOT NULL CHECK (source IN ('pasted', 'captured', 'researched')),
    verification_state TEXT NOT NULL CHECK (
        verification_state IN ('saved', 'user_reported_worked', 'execution_verified')
    ),
    working_directory TEXT,
    shell TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_commands_exact_text
ON commands(command_text);

CREATE INDEX IF NOT EXISTS idx_commands_created_at
ON commands(created_at DESC);
"""

MIGRATIONS: dict[int, str] = {
    1: """
        ALTER TABLE commands ADD COLUMN category TEXT;
        ALTER TABLE commands ADD COLUMN subcategory TEXT;
        ALTER TABLE commands ADD COLUMN description TEXT;
        ALTER TABLE commands ADD COLUMN flag_breakdown TEXT NOT NULL DEFAULT '[]';
        ALTER TABLE commands ADD COLUMN tags TEXT NOT NULL DEFAULT '[]';
        ALTER TABLE commands ADD COLUMN risk_level TEXT;
        ALTER TABLE commands ADD COLUMN risk_notes TEXT NOT NULL DEFAULT '[]';
        ALTER TABLE commands ADD COLUMN documentation_source TEXT;
        ALTER TABLE commands ADD COLUMN ai_model TEXT;
        ALTER TABLE commands ADD COLUMN documented_at TEXT;
    """,
}


class DatabaseError(RuntimeError):
    """Raised when local database work cannot be completed safely."""


class Database:
    """Own SQLite setup and transaction boundaries."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(
                f"Cannot create the CL-AI data directory: {self.path.parent}"
            ) from exc

        with self.connection() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise DatabaseError(
                    "The database was created by a newer CL-AI version. "
                    "Upgrade CL-AI before opening it."
                )
            if version == 0:
                connection.executescript(SCHEMA_SQL)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                return

            while version < SCHEMA_VERSION:
                migration = MIGRATIONS.get(version)
                if migration is None:
                    raise DatabaseError(
                        f"No migration is available for database schema version {version}."
                    )
                connection.executescript(migration)
                version += 1
                connection.execute(f"PRAGMA user_version = {version}")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            if connection is not None:
                connection.rollback()
            raise DatabaseError(
                "The local CL-AI database operation failed. "
                "Check the data-directory permissions and available disk space."
            ) from exc
        except Exception:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()


import sqlite3

import pytest

from cl_ai.storage import Database, DatabaseError
from cl_ai.storage.database import SCHEMA_VERSION


def test_database_initialization_creates_versioned_schema(tmp_path) -> None:
    path = tmp_path / "nested" / "cl_ai.db"

    Database(path).initialize()

    with sqlite3.connect(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'commands'"
        ).fetchone()
    assert version == SCHEMA_VERSION
    assert table == ("commands",)


def test_newer_database_schema_is_rejected(tmp_path) -> None:
    path = tmp_path / "cl_ai.db"
    with sqlite3.connect(path) as connection:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")

    with pytest.raises(DatabaseError, match="newer CL-AI version"):
        Database(path).initialize()


def test_version_one_database_is_migrated_without_losing_commands(tmp_path) -> None:
    path = tmp_path / "cl_ai.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_text TEXT NOT NULL,
                title TEXT,
                notes TEXT,
                source TEXT NOT NULL,
                verification_state TEXT NOT NULL,
                working_directory TEXT,
                shell TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO commands (
                command_text, title, source, verification_state, created_at, updated_at
            ) VALUES (
                'git status', 'Git status', 'pasted', 'saved',
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'
            );
            PRAGMA user_version = 1;
            """
        )

    Database(path).initialize()

    with sqlite3.connect(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        row = connection.execute(
            "SELECT command_text, flag_breakdown, tags FROM commands WHERE id = 1"
        ).fetchone()
    assert version == SCHEMA_VERSION
    assert row == ("git status", "[]", "[]")


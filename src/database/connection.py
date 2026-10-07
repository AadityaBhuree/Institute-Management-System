"""Database connection manager and session context for SQLite.
Enforces WAL mode, foreign keys, and dictionary row mapping.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import src.core.config as config  # pyright: ignore[reportMissingImports] # type: ignore


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Create and configure a robust SQLite connection."""
    target_path = Path(db_path) if db_path else config.DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(target_path),
        check_same_thread=False,
        timeout=10.0,
        isolation_level=None,  # autocommit mode / explicit transaction management
    )
    conn.row_factory = sqlite3.Row

    # Enforce SQLite enterprise pragmas
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA busy_timeout = 5000;")
    cursor.close()

    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for atomic transaction block with automatic rollback on error."""
    cursor = conn.cursor()
    cursor.execute("BEGIN IMMEDIATE;")
    try:
        yield cursor
        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise
    finally:
        cursor.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for obtaining a request-scoped database connection."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

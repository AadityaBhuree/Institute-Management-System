"""Database Schema Migration and Version Tracking Manager.
Discovers, tracks, and atomically executes numerical SQL schema migrations in sequence.
"""

import hashlib
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

from src.database.connection import transaction

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class MigrationManager:
    """Manages database schema versioning, integrity hashes, and forward migrations."""

    @staticmethod
    def init_migration_table(conn: sqlite3.Connection) -> None:
        """Ensure schema_migrations metadata table exists."""
        with transaction(conn) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT,
                    execution_ms REAL DEFAULT 0.0
                );
                """
            )

    @staticmethod
    def get_applied_migrations(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Retrieve ordered list of previously executed migrations."""
        MigrationManager.init_migration_table(conn)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT version, name, applied_at, checksum, execution_ms
            FROM schema_migrations
            ORDER BY version ASC;
            """
        )
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_pending_migrations(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Identify available migration files that have not yet been applied."""
        applied = {m["version"] for m in MigrationManager.get_applied_migrations(conn)}
        MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

        pending = []
        for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            # Expect filename format: 001_name.sql
            parts = file.stem.split("_", 1)
            if len(parts) == 2 and parts[0].isdigit():
                version = int(parts[0])
                name = parts[1]
                if version not in applied:
                    pending.append(
                        {
                            "version": version,
                            "name": name,
                            "filename": file.name,
                            "filepath": file,
                        }
                    )
        return pending

    @staticmethod
    def apply_migration(
        conn: sqlite3.Connection, version: int, name: str, filepath: Path
    ) -> Dict[str, Any]:
        """Atomically execute a single SQL migration file and record its metadata."""
        content = filepath.read_text(encoding="utf-8")
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        t0 = time.perf_counter()
        with transaction(conn) as cur:
            cur.executescript(content)
            execution_ms = round((time.perf_counter() - t0) * 1000, 2)
            cur.execute(
                """
                INSERT INTO schema_migrations (version, name, checksum, execution_ms)
                VALUES (?, ?, ?, ?);
                """,
                (version, name, checksum, execution_ms),
            )

        logging.getLogger("ims").info(
            "Applied migration %03d_%s in %.2f ms", version, name, execution_ms
        )
        return {
            "version": version,
            "name": name,
            "checksum": checksum,
            "execution_ms": execution_ms,
            "status": "APPLIED",
        }

    @staticmethod
    def run_pending_migrations(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Run all pending schema migrations in numerical order."""
        MigrationManager.init_migration_table(conn)
        pending = MigrationManager.get_pending_migrations(conn)
        results = []
        for item in pending:
            res = MigrationManager.apply_migration(
                conn, item["version"], item["name"], item["filepath"]
            )
            results.append(res)
        return results

    @staticmethod
    def get_status(conn: sqlite3.Connection) -> Dict[str, Any]:
        """Return diagnostic status of applied and pending schema migrations."""
        applied = MigrationManager.get_applied_migrations(conn)
        pending = MigrationManager.get_pending_migrations(conn)
        current_version = max([m["version"] for m in applied], default=0)

        return {
            "current_version": current_version,
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_migrations": applied,
            "pending_migrations": [
                {"version": p["version"], "name": p["name"], "filename": p["filename"]}
                for p in pending
            ],
        }

"""System telemetry, diagnostics, and database backup service."""

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Dict, List

from src.core.config import APP_NAME, APP_VERSION, DATA_DIR, DB_PATH

BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


class SystemService:
    @staticmethod
    def get_system_telemetry(conn: sqlite3.Connection) -> Dict[str, Any]:
        """Collect database size, WAL mode, table counts, and integrity status."""
        cursor = conn.cursor()

        # Database File Size
        db_size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        db_size_kb = round(db_size_bytes / 1024, 2)
        db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

        # Integrity Check
        cursor.execute("PRAGMA integrity_check;")
        integrity_row = cursor.fetchone()
        integrity_status = integrity_row[0] if integrity_row else "unknown"

        # Journal Mode
        cursor.execute("PRAGMA journal_mode;")
        journal_row = cursor.fetchone()
        journal_mode = journal_row[0].upper() if journal_row else "unknown"

        # Tables and Record Counts
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        tables = [r["name"] for r in cursor.fetchall()]

        table_stats: Dict[str, int] = {}
        for tbl in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) AS total FROM {tbl};")
                table_stats[tbl] = cursor.fetchone()["total"]
            except Exception:
                table_stats[tbl] = 0

        cursor.close()

        backups = SystemService.list_backups()

        return {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "db_path": str(DB_PATH),
            "db_size_bytes": db_size_bytes,
            "db_size_kb": db_size_kb,
            "db_size_mb": db_size_mb,
            "integrity_status": integrity_status,
            "journal_mode": journal_mode,
            "total_tables": len(tables),
            "table_stats": table_stats,
            "backups_count": len(backups),
            "recent_backups": backups[:10],
        }

    @staticmethod
    def create_backup(conn: sqlite3.Connection) -> Dict[str, Any]:
        """Perform a hot live backup of the active SQLite database using native backup API."""
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"ims_backup_{timestamp}.db"
        backup_filepath = BACKUPS_DIR / backup_filename

        # Create destination database and execute atomic online backup
        dest_conn = sqlite3.connect(str(backup_filepath))
        with dest_conn:
            conn.backup(dest_conn)
        dest_conn.close()

        file_size_bytes = backup_filepath.stat().st_size
        file_size_kb = round(file_size_bytes / 1024, 2)

        return {
            "filename": backup_filename,
            "filepath": str(backup_filepath),
            "size_bytes": file_size_bytes,
            "size_kb": file_size_kb,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "SUCCESS",
        }

    @staticmethod
    def list_backups() -> List[Dict[str, Any]]:
        """List all available database snapshots in data/backups/."""
        if not BACKUPS_DIR.exists():
            return []

        backups: List[Dict[str, Any]] = []
        for p in BACKUPS_DIR.glob("*.db"):
            stat = p.stat()
            backups.append(
                {
                    "filename": p.name,
                    "filepath": str(p),
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )

        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
